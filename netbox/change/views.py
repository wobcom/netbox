import io
import json

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

from netbox import configuration
from utilities.views import ObjectListView
from . import tables
from .forms import AffectedCustomerInlineFormSet
from .models import ChangeInformation, ChangeSet, \
    DRAFT, IN_REVIEW, ACCEPTED, REJECTED, IMPLEMENTED, FAILED
from .utilities import redirect_to_referer



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
    SESSION_VARS = ['change_information', 'in_change', 'foreign_change']

    def get_changeset(self, request):
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

        changeset.revert()

        return changeset

    def clear_session(request):
        for session_var in self.SESSION_VARS:
            if session_var in request.session:
                del request.session[session_var]

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
        changeset = self.treat_changeset(request)

        res = render(request, 'change/list.html', {
            'changeset': changeset
        })

        if 'change_information' not in request.session:
            request.session['in_change'] = False
            return redirect('/')

        self.clear_session(request)

        return res


MR_TXT = """Change #{} was created in Netbox by {}.

## Executive Summary

{}
"""


def check_actions(project, actions, branch):
    treated = set()
    new_actions = []
    for f in project.repository_tree(path='host_vars', all=True, recursive=True):
        # we only care for files
        if f['type'] != 'blob':
            continue
        f = f['path']
        if f in actions:
            treated.add(f)
            new_actions.append({
                'action': 'update',
                'file_path': f,
                'content': actions[f],
            })
        else:
            new_actions.append({
                'action': 'delete',
                'file_path': f,
            })
    for action in actions:
        if action in treated:
            continue
        new_actions.append({
            'action': 'create',
            'file_path': action,
            'content': actions[action],
        })
    return new_actions


def check_branch_exists(project, branch_name):
    try:
        b = project.branches.get(branch_name)
        if b:
            return True
    except gitlab.exceptions.GitlabError:
        pass
    return False


def open_gitlab_mr(o, delete_branch=False):
    gl = gitlab.Gitlab(configuration.GITLAB_URL, configuration.GITLAB_TOKEN)
    info = o.change_information
    project = gl.projects.get(configuration.GITLAB_PROJECT_ID)
    actions = o.to_actions()
    mr_txt = MR_TXT.format(o.id, o.user, o.executive_summary())
    emergency_label = ['emergency'] if info.is_emergency else []
    branch_name = 'change_{}'.format(o.id)
    req_approvals = 1 if o.change_information.is_emergency or not o.change_information.is_extensive else 2
    commit_msg = 'Autocommit from Netbox (Change #{}: {})'.format(
        o.id, info.name
    )
    req_approvals = 1 if info.is_emergency or not info.is_extensive else 2

    if delete_branch and check_branch_exists(project, branch_name):
        project.branches.delete(branch_name)

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
        'commit_message': commit_msg,
        'author_name': 'Netbox',
        'actions': actions,
    })
    mr = project.mergerequests.create({
        'title': 'Change #{}: {}'.format(o.id, info.name),
        'description': mr_txt,
        'source_branch': branch_name,
        'target_branch': 'master',
        'approvals_before_merge': req_approvals,
        'labels': ['netbox', 'unreviewed'] + emergency_label
    })

    # set project approvals so the surveyor can do its funk if the approver is
    # set
    if configuration.GITLAB_APPROVER_ID:
        mr_mras = mr.approvals.get()
        mr_mras.approvals_before_merge = 1
        mr_mras.save()

        mr.approvals.set_approvers(
            approver_ids=[configuration.GITLAB_APPROVER_ID]
        )

    msg = "You can review your merge request at {}/{}/merge_requests/{}!"
    return msg.format(configuration.GITLAB_URL, project.path_with_namespace,
                      mr.iid)


@method_decorator(login_required, name='dispatch')
class MRView(View):
    model = ChangeSet

    def get(self, request, pk=None):
        """
        This view is triggered when the operator clicks on "Recreate Merge
        Request" in the change list view.
        A merge request is created in Gitlab, and the status of the object is
        changed to Accepted.
        """
        obj = get_object_or_404(self.model, pk=pk)

        messages.info(request, open_gitlab_mr(obj, delete_branch=True))
        obj.status = ACCEPTED
        obj.save()

        return redirect('/change/list')


@method_decorator(login_required, name='dispatch')
class AcceptView(View):
    model = ChangeSet

    def get(self, request, pk=None):
        """
        This view is triggered when the change was accepted by the operator.
        The changes are propagated into Gitlab, and the status of the object is
        changed to in review.
        """
        obj = get_object_or_404(self.model, pk=pk)

        if obj.status != DRAFT:
            return HttpResponseForbidden('Change was already accepted!')

        try:
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
    def update(self, request, pk=None):
        """
        This view is triggered when the change was provisioned by Gitlab.
        The status of the changeset is updated and the changes are re-applied.
        """
        obj = get_object_or_404(self.model, pk=pk)

        if obj.status == IMPLEMENTED:
            return HttpResponseForbidden('Change was already provisioned!')

        obj.status = IMPLEMENTED
        obj.provision_log = json.loads(request.body.decode('utf-8'))
        obj.apply()
        obj.save()

        # no content
        return HttpResponse(status=204)


class FailedView(ViewSet):
    model = ChangeSet
    queryset = ChangeSet.objects
    def update(self, request, pk=None):
        """
        This view is triggered when the change was provisioned by Gitlab and
        errored. The status of the changeset is updated and the changes are
        re-applied.
        """
        obj = get_object_or_404(self.model, pk=pk)

        obj.status = FAILED
        obj.provision_log = json.loads(request.body.decode('utf-8'))
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

        open_gitlab_mr(obj)

        obj.status = ACCEPTED
        obj.save()

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
