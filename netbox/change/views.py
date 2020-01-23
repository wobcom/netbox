from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.safestring import mark_safe
from django.views.generic import View
from django.views.generic.edit import CreateView
import gitlab

from netbox import configuration
from dcim.models import Device
from .forms import ChangeInformationForm
from .models import ChangeInformation, ChangeSet, ProvisionSet, ACCEPTED, IMPLEMENTED


class ChangeFormView(PermissionRequiredMixin, CreateView):
    """
    This view is for displaying the change form and
    open a new change.
    """
    model = ChangeInformation
    form_class = ChangeInformationForm
    success_url = '/'
    permission_required = 'change.add_changeset'

    def post(self, request, *args, **kwargs):
        self.request = request
        return super(ChangeFormView, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        result = super(ChangeFormView, self).form_valid(form)

        c = ChangeSet(user=self.request.user, active=True)
        c.change_information = self.object
        c.save()

        return result

    def get_context_data(self, **kwargs):
        ctx = super(ChangeFormView, self).get_context_data(**kwargs)
        #ctx['affected_customers'] = AffectedCustomerInlineFormSet(prefix='affected_customers')
        ctx['return_url'] = '/change/toggle'
        ctx['obj_type'] = 'Change Request'

        # TODO: add possible parent changes
        #ctx['change_parents'] = TP.operator_change("")

        return ctx


class EndChangeView(PermissionRequiredMixin, View):
    """
    This view is for displaying change overview and closes a change.
    """
    permission_required = 'change.add_changeset'

    def get(self, request):
        if request.my_change is None:
            return HttpResponse('Not in Change!', status=409)

        return render(request, 'change/list.html', {
            'changeset': request.my_change
        })

    def post(self, request):
        """
        This view is triggered when the operator clicks on "Recreate Merge
        Request" in the change list view.
        A merge request is created in Gitlab, and the status of the object is
        changed to Accepted.
        """

        if request.my_change is None:
            return HttpResponse("You're currently not in a change", status=409), None

        request.my_change.active = False
        request.my_change.status = ACCEPTED
        request.my_change.save()

        return redirect('home')


MR_TXT = """## Multiple Changes
Provisioning started in Netbox by {}.
"""

CHANGE_TXT = """

### Change #{}: {}
Created in Netbox by {}.

#### Executive Summary

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
    project = gl.projects.get(configuration.GITLAB_PROJECT_ID)
    actions = o.to_actions(devices)
    mr_txt = MR_TXT.format(o.user.username)
    changes_txt = ""
    for change_set in o.changesets.all():
        mr_txt += "* {}\n".format(change_set.change_information.name)
        changes_txt += CHANGE_TXT.format(
            change_set.id,
            change_set.change_information.name,
            change_set.user.username,
            change_set.executive_summary().replace('\n', '\\\n'),
        )
    mr_txt += changes_txt
    branch_name = 'provisioning_{}'.format(o.id)
    commit_msg = 'Autocommit from Netbox (Provisioning #{})'.format(o.id)

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
        'title': 'Deployment #{}: {} Changes'.format(o.id, o.changesets.count()),
        'description': mr_txt,
        'source_branch': branch_name,
        'target_branch': 'master',
        'approvals_before_merge': 1,
        'labels': ['netbox', 'unreviewed']
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


class DeployView(PermissionRequiredMixin, View):
    """
    This view is for displaying provisioning details
    and start provisioning.
    """
    permission_required = 'change.deploy_changeset'

    def __init__(self, *args, **kwargs):
        super(DeployView, self).__init__(*args, **kwargs)
        self.undeployed_changesets = ChangeSet.objects.exclude(status=IMPLEMENTED).order_by('id')

    def get(self, request):

        return render(request, 'change/deploy.html', context={
            'undeployed_changesets': self.undeployed_changesets,
            'unaccepted_changes': self.undeployed_changesets.exclude(status=ACCEPTED).count(),
            'ACCEPTED': ACCEPTED
        })

    def post(self, request):

        provision_set = ProvisionSet(user=request.user)
        provision_set.save()

        for change_set in self.undeployed_changesets:
            change_set.provision_set = provision_set
            change_set.save()

        try:
            safe = mark_safe(open_gitlab_mr(provision_set))
            messages.info(request, safe)

        except gitlab.exceptions.GitlabError as e:
            messages.warning(request,
                             "Unable to connect to GitLab at the moment! Error message: {}".format(e)
                             )
        self.undeployed_changesets.update(status=IMPLEMENTED)

        return redirect('home')


class DetailView(PermissionRequiredMixin, View):
    """
    This view is for displaying change details.
    """
    permission_required = 'change.view_changeset'

    def get(self, request, pk=None):
        """
        This view renders the details of a change.
        """
        changeset = get_object_or_404(ChangeSet, pk=pk)
        return render(request, 'change/detail.html', {'changeset': changeset})
