import io

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models
from django.http import HttpResponse, HttpResponseForbidden, \
    HttpResponseServerError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import dateparse, timezone
from django.utils.decorators import method_decorator
from django.views.generic import View
from django.views.generic.edit import CreateView
from rest_framework.decorators import action
from rest_framework.viewsets import ViewSet
import gitlab
import requests
import topdesk

from netbox import configuration
from utilities.views import ObjectListView
from . import tables
from .forms import AffectedCustomerInlineFormSet
from .models import ChangeInformation, ChangedField, ChangedObject, ChangeSet, \
    DRAFT, IN_REVIEW, ACCEPTED, REJECTED, IMPLEMENTED
from .utilities import redirect_to_referer



TP = topdesk.Topdesk(configuration.TOPDESK_URL,
                     verify=configuration.TOPDESK_VERIFY_HTTPS,
                     app_creds=(configuration.TOPDESK_USERNAME,
                                configuration.TOPDESK_PASSWORD))



@method_decorator(login_required, name='dispatch')
class ChangeFormView(CreateView):
    model = ChangeInformation
    fields = '__all__'
    success_url = '/'

    def get(self, request, *args, **kwargs):
        if not request.session.get('in_change'):
            return redirect('/')
        return super(CreateView, self).get(request, *args, **kwargs)

    def form_valid(self, form):
        result = super(ChangeFormView, self).form_valid(form)

        customers_formset = AffectedCustomerInlineFormSet(
            form.data,
            instance=self.object,
            prefix='affected_customers'
        )
        if customers_formset.is_valid():
            customers = customers_formset.save()

        self.request.session['change_information'] = self.object.id

        return result

    def get_context_data(self, **kwargs):
        ctx = super(ChangeFormView, self).get_context_data(**kwargs)
        ctx['affected_customers'] = AffectedCustomerInlineFormSet(prefix='affected_customers')
        ctx['return_url'] = '/change/toggle'
        ctx['obj_type'] = 'Change Request'

        # TODO: add possible parent changes
        #ctx['change_parents'] = TP.operator_change("")

        return ctx


@method_decorator(login_required, name='dispatch')
class ToggleView(View):
    def get(self, request):
        """
        This view is triggered when we begin or end a change.
        If we begin the change, we simply toggle the cookie. If we end it, we
        finalize the change and present it to the user.
        """
        if request.session['foreign_change']:
            return redirect_to_referer(request)
        request.session['in_change'] = not request.session.get('in_change', False)
        # we started the change and need to get info
        if request.session['in_change']:
            c = ChangeSet(user=request.user, active=True)
            c.save()
            request.session['change_id'] = c.id
            return redirect('/change/form')

        # we finished our change. we generate the changeset now
        if 'change_id' not in request.session:
            return HttpResponseForbidden('Invalid session!')

        changeset = ChangeSet.objects.get(pk=request.session['change_id'])
        if not changeset.active:
            return HttpResponseForbidden('Change timed out!')

        info_id = request.session.get('change_information')
        change_information = None
        if info_id:
            change_information = ChangeInformation.objects.get(pk=info_id)
            changeset.change_information = change_information

        changeset.active = False
        changeset.save()

        if (not changeset.changedfield_set.count() and
           not changeset.changedobject_set.count()):
            if change_information:
                del request.session['change_information']
                change_information.delete()
            return render(request, 'change/list.html', {
                'changeset': None
            })

        res = render(request, 'change/list.html', {
            'changeset': changeset
        })

        changeset.revert()

        if 'change_information' not in request.session:
            return HttpResponseForbidden('You need to fill out the change form!')

        del request.session['change_information']

        return res


def trigger_topdesk_change(obj):
    type_ = 'extensive' if obj.change_information.is_extensive else 'simple'
    request_txt = 'Change #{} was created in Netbox by {}.\n\nSummary:\n{}'
    request_txt = request_txt.format(obj.id, obj.user,
                                     obj.executive_summary(no_markdown=True))
    data = {
        'requester': {
            'id': configuration.TOPDESK_REQ_ID,
            'name': configuration.TOPDESK_REQ_NAME,
        },
        'briefDescription': 'Change #{} was created in Netbox'.format(obj.id),
        'changeType': type_,
        'request': request_txt,
    }
    res = TP.create_operator_change(data)
    res_id = res['id']
    obj.ticket_id = res_id
    obj.save()
    return res_id


MR_TXT = """Change #{} was created in Netbox by {} (TOPdesk ticket {}).

## Executive Summary

{}
"""


def check_actions(project, actions, branch):
    new_actions = []
    for action in actions:
        try:
            project.files.get(action['file_path'], ref=branch)
            action['action'] = 'update'
        except Exception as e:
            action['action'] = 'create'
        new_actions.append(action)
    return new_actions


def open_gitlab_mr(o):
    gl = gitlab.Gitlab(configuration.GITLAB_URL, configuration.GITLAB_TOKEN)
    project = gl.projects.get(configuration.GITLAB_PROJECT_ID)
    actions = o.to_actions()
    mr_txt = mr_TXT.format(o.id, o.user, o.ticket_id,
                                 o.executive_summary())
    emergency_label = ['emergency'] if o.change_information.is_emergency else []
    branch_name = 'change_{}'.format(o.id)
    commit_msg = 'Autocommit from Netbox (Change #{})'.format(o.id)
    project.branches.create({
        'branch': branch_name,
        'ref': 'master'
    })
    actions = check_actions(project, actions, branch_name)
    actions.append(o.create_inventory())
    actions.append(o.create_topology_graph())
    project.commits.create({
        'id': project.id,
        'branch': branch_name,
        'commit_message': 'Autocommit from Netbox (Change #{})'.format(o.id),
        'author_name': 'Netbox',
        'actions': actions,
    })
    mr = project.mergerequests.create({
        'title': 'Change #{} was created in Netbox'.format(o.id),
        'description': mr_txt,
        'source_branch': branch_name,
        'target_branch': 'master',
        'labels': ['netbox', 'unreviewed'] + emergency_label
    })
    msg = "You can review your merge request at {}/{}/merge_requests/{}!"
    return msg.format(configuration.GITLAB_URL, project.path_with_namespace,
                      mr.iid)


@method_decorator(login_required, name='dispatch')
class AcceptView(View):
    model = ChangeSet

    def get(self, request, pk=None):
        """
        This view is triggered when the change was accepted by the operator.
        The changes are propagated into TOPdesk and Gitlab, and the status of
        the object is changed to in review.
        """
        obj = get_object_or_404(self.model, pk=pk)

        if obj.status != DRAFT:
            return HttpResponseForbidden('Change was already accepted!')

        try:
            if configuration.TOPDESK_URL:
                res_id = trigger_topdesk_change(obj)
                obj.ticket_id = res_id
                obj.save()

            # register in surveyor if its configured
            # if there is no topdesk surveyor url, we create an MR right away.
            # otherwise we first create the ticket and defer creating the MR
            if configuration.TOPDESK_URL and configuration.TOPDESK_SURVEYOR_URL:
                requests.post('{}/{}/{}'.format(
                    configuration.TOPDESK_SURVEYOR_URL,
                    obj.id,
                    res_id)
                )
            else:
                messages.info(request, open_gitlab_mr(obj))
        except ConnectionError as e:
            return HttpResponseServerError(str(e))

        obj.status = IN_REVIEW
        obj.save()

        return redirect('/')


@method_decorator(login_required, name='dispatch')
class RejectView(View):
    model = ChangeSet

    def get(self, request, pk=None):
        """
        This view is triggered when the change was rejected by the operator.
        The status of the object is changed to rejected.
        """
        obj = get_object_or_404(self.model, pk=pk)

        if obj.status != DRAFT:
            return HttpResponseForbidden('Change was already accepted!')

        obj.status = REJECTED
        obj.save()

        return redirect('/')


# needs to be a rest_framework viewset for nextbox... urgh
# TODO: combine to generic workflow endpoint with ReviewedView and RejectedView?
class ProvisionedView(ViewSet):
    model = ChangeSet
    queryset = ChangeSet.objects
    def retrieve(self, request, pk=None):
        """
        This view is triggered when the change was provisioned by Gitlab.
        The status of the changeset is updated and the changes are re-applied.
        """
        obj = get_object_or_404(self.model, pk=pk)

        if obj.status == IMPLEMENTED:
            return HttpResponseForbidden('Change was already provisioned!')

        obj.status = IMPLEMENTED
        obj.apply()
        obj.save()

        # no content
        return HttpResponse(status=204)


class ReviewedView(ViewSet):
    model = ChangeSet
    queryset = ChangeSet.objects
    def retrieve(self, request, pk=None):
        """
        This view is triggered when the change was reviewed in TOPdesk.
        The status of the changeset is updated.
        """
        obj = get_object_or_404(self.model, pk=pk)

        if obj.status != IN_REVIEW:
            return HttpResponseForbidden('Change is not in review!')

        obj.status = ACCEPTED
        obj.save()

        open_gitlab_mr(obj)

        # no content
        return HttpResponse(status=204)


class RejectedView(ViewSet):
    model = ChangeSet
    queryset = ChangeSet.objects
    def retrieve(self, request, pk=None):
        """
        This view is triggered when the change was rejected in TOPdesk.
        The status of the changeset is updated.
        """
        obj = get_object_or_404(self.model, pk=pk)

        if obj.status != IN_REVIEW:
            return HttpResponseForbidden('Change is not in review!')

        obj.status = REJECTED
        obj.save()

        # no content
        return HttpResponse(status=204)


@method_decorator(login_required, name='dispatch')
class DetailView(View):
    def get(self, request, pk=None):
        """
        This view renders the details of a change.
        """
        changeset = get_object_or_404(ChangeSet, pk=pk)
        return render(request, 'change/detail.html', {'changeset': changeset})


@method_decorator(login_required, name='dispatch')
class ListView(ObjectListView):
    queryset = ChangeSet.objects.annotate(
        changedfield_count=models.Count('changedfield', distinct=True),
        changedobject_count=models.Count('changedobject', distinct=True)
    )
    table = tables.ChangeTable
    template_name = 'change/change_list.html'
