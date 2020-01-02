import io
import json
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import models
from django.http import HttpResponse, HttpResponseForbidden, \
    HttpResponseServerError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import dateparse, timezone
from django.utils.decorators import method_decorator
from django.utils.safestring import mark_safe
from django.views.generic import View
from django.views.generic.edit import CreateView
from rest_framework.decorators import action
from rest_framework.viewsets import ViewSet
import gitlab

from netbox import configuration
from dcim.models import Device
from utilities.views import ObjectListView
from . import tables
from .forms import AffectedCustomerInlineFormSet, ChangeInformationForm
from .models import ChangeInformation, ChangeSet, \
    DRAFT, IN_REVIEW, ACCEPTED, REJECTED, IMPLEMENTED, FAILED
from .utilities import redirect_to_referer


def treat_changeset(request):
    if 'change_id' not in request.session:
        return HttpResponseForbidden('Invalid session!'), None

    changeset = ChangeSet.objects.get(pk=request.session['change_id'])
    if not changeset.active:
        return HttpResponseForbidden('Change timed out!'), None

    changeset.active = False
    changeset.save()

    changeset.revert()

    change_information = changeset.change_information
    if change_information:
        for depends in change_information.depends_on.all():
            depends.revert()

    return None, changeset


SESSION_VARS = ['change_information', 'in_change', 'foreign_change']

def clear_session(request):
    for session_var in SESSION_VARS:
        if session_var in request.session:
            del request.session[session_var]


class ChangeFormView(PermissionRequiredMixin, CreateView):
    model = ChangeInformation
    form_class = ChangeInformationForm
    success_url = '/'
    permission_required = 'change.add_changeset'

    def get(self, request, *args, **kwargs):
        if not request.session.get('in_change'):
            return redirect('home')
        return super(ChangeFormView, self).get(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        change_id = self.request.session['change_id']
        return {
            **kwargs,
            'change_id': change_id
        }

    def form_valid(self, form):
        result = super(ChangeFormView, self).form_valid(form)

        customers_formset = AffectedCustomerInlineFormSet(
            form.data,
            instance=self.object,
            prefix='affected_customers'
        )
        if customers_formset.is_valid():
            customers_formset.save()

        for depends in self.object.depends_on.all():
            depends.apply()

        c = ChangeSet.objects.get(pk=self.request.session['change_id'])
        c.change_information = self.object
        c.save()

        return result

    def get_context_data(self, **kwargs):
        ctx = super(ChangeFormView, self).get_context_data(**kwargs)
        ctx['affected_customers'] = AffectedCustomerInlineFormSet(prefix='affected_customers')
        ctx['return_url'] = '/change/toggle'
        ctx['obj_type'] = 'Change Request'

        # TODO: add possible parent changes
        #ctx['change_parents'] = TP.operator_change("")

        return ctx


class ToggleView(PermissionRequiredMixin, View):

    def get(self, request):
        """
        This view is triggered when we begin or end a change.
        If we begin the change, we simply toggle the cookie. If we end it, we
        finalize the change and present it to the user.
        """
        if request.session['foreign_change']:
            return redirect_to_referer(request)

        # we started the change and need to get info
        if not request.session['in_change']:
            request.session['in_change'] = True

            c = ChangeSet(user=request.user, active=True)
            c.save()
            request.session['change_id'] = c.id
            return redirect('change:form')

        # we finished our change. we generate the changeset now
        changeset = ChangeSet.objects.get(pk=request.session['change_id'])
        if not changeset.active:
            return HttpResponseForbidden('Change timed out!')

        res = render(request, 'change/list.html', {
            'changeset': changeset
        })

        if not changeset.change_information:
            request.session['in_change'] = False
            return redirect('home')

        return res


MR_TXT = """Change #{} was created in Netbox by {}.

## Executive Summary

{}
"""


def check_actions(project, actions, branch):
    treated = set()
    new_actions = []
    # if not git exists:
    #    git clone configurations.GITLAB_CLONE_URL
    # git pull
    # ls host_vars/**/*
    for f in project.repository_tree(path='host_vars', all=True, recursive=True, per_page=100):
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
    devices = Device.objects.prefetch_related(
             'interfaces__untagged_vlan',
             'interfaces__tagged_vlans',
             'interfaces__overlay_network',
             'device_type').filter(primary_ip4__isnull=False)
    gl = gitlab.Gitlab(configuration.GITLAB_URL, configuration.GITLAB_TOKEN)
    info = o.change_information
    project = gl.projects.get(configuration.GITLAB_PROJECT_ID)
    actions = o.to_actions(devices)
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
    actions.append(o.create_inventory(devices))
    actions.append(o.create_topology_graph(devices))
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

    o.mr_location = "{}/{}/merge_requests/{}".format(
        configuration.GITLAB_URL, project.path_with_namespace, mr.iid
    )

    return 'You can review your merge request <a href="{}">here</a>!'.format(o.mr_location)


@method_decorator(login_required, name='dispatch')
class AcceptView(View):
    model = ChangeSet

    def get(self, request, pk=None):
        """
        This view is triggered when the operator clicks on "Recreate Merge
        Request" in the change list view.
        A merge request is created in Gitlab, and the status of the object is
        changed to Accepted.
        """
        recreate = request.GET.get('recreate')

        err, obj = treat_changeset(request)

        if err:
            return err

        request.session['in_change'] = False

        if obj.status != DRAFT and not recreate:

            return HttpResponseForbidden('Change was already accepted!')

        try:
            safe = mark_safe(open_gitlab_mr(obj, delete_branch=recreate))
            messages.info(request, safe)
            obj.status = IN_REVIEW
            obj.save()
        except gitlab.exceptions.GitlabError as e:
            obj.revert()
            messages.warning(request,
                "Unable to connect to GitLab at the moment! Error message: {}".format(e)
            )

        return redirect('home')


@method_decorator(login_required, name='dispatch')
class RejectView(View):

    def get(self, request, pk=None):
        """
        This view is triggered when the change was rejected by the operator.
        The status of the object is changed to rejected.
        """
        err, obj = treat_changeset(request)

        if err:
            return err

        request.session['in_change'] = False

        if obj.status != DRAFT:
            return HttpResponseForbidden('Change was already accepted!')

        obj.status = REJECTED
        obj.save()

        return redirect('home')


@method_decorator(login_required, name='dispatch')
class ReactivateView(View):
    model = ChangeSet

    def get(self, request, pk=None):
        """
        This view is triggered when the change is reactivated by the operator.
        The object is marked as active, updated, and assigned to the operator.
        """
        obj = get_object_or_404(self.model, pk=pk)

        if obj.status != DRAFT:
            return HttpResponseForbidden('Change cannot be reactivated!')

        obj.active = True
        obj.updated = datetime.now()
        obj.save()

        obj.apply()

        request.session['in_change'] = True

        return redirect('home')


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
