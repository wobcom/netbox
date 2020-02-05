import os
import signal
import json

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpResponse
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import View
from django.views.generic.edit import CreateView
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from diplomacy import Diplomat

from netbox import configuration
from utilities.views import ObjectListView
from .forms import ChangeInformationForm
from .models import (ChangeInformation, ChangeSet, ProvisionSet, ACCEPTED,
    IMPLEMENTED, RUNNING, FINISHED, FAILED, ABORTED)
from . import tables, globals


def send_provision_status(provision_set, status):
    """
    Sends provision status to channels group 'provision_status'.
    :param provision_set:
    :param status: True if started, False if stopped
    """
    async_to_sync(get_channel_layer().group_send)('provision_status', {
        'type': 'provision_status_message',
        'text': json.dumps({'provision_set_pk': provision_set.pk, 'provision_status': str(int(status))})
    })


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
            'undeployed_changesets_table': tables.ProvisioningChangesTable(data=self.undeployed_changesets),
            'undeployed_changesets': self.undeployed_changesets.count(),
            'unaccepted_changesets': self.undeployed_changesets.exclude(status=ACCEPTED).count(),
            'ACCEPTED': ACCEPTED
        })

    def post(self, request):
        acquired = globals.active_provisioning.acquire(blocking=False)
        if not acquired:
            messages.error(
                request,
                'Provisioning can not be started, another provisioning is already running.'
            )
            return redirect('change:deploy')

        provision_set = ProvisionSet(user=request.user)
        provision_set.save()

        send_provision_status(provision_set, status=True)

        self.undeployed_changesets.update(provision_set=provision_set)

        db = configuration.DATABASE
        # postgresql is a given in the context of netbox
        # TODO: is there a better way to obtain a connection string?
        odin = Diplomat(
            configuration.ODIN_EXECUTABLE,
            'postgresql://{}:{}@{}/{}'.format(
                db['USER'], db['PASSWORD'], db['HOST'], db['NAME']
            ),
            single_file=True
        )

        provision_set.output_log_file = odin.output_file_name()
        provision_set.status = RUNNING
        provision_set.save()

        odin.wait()

        if not odin.has_succeeded():
            provision_set.status = FAILED
            provision_set.persist_output_log()
            provision_set.save()
            return redirect('change:provision_set', pk=provision_set.pk)

        ansible = Diplomat(
            "ansible-playbook", "-K", "-i", "_build/inventory.ini",
            "_build/deploy.yml", "--check", "--diff", # the last two are for testing
            out=odin.output_file_name(),
            single_file=True,
        )

        globals.provisioning_pid = ansible._process.pid

        def callback():
            # TODO: what do we set here?
            globals.provisioning_pid = None
            globals.active_provisioning.release()
            send_provision_status(provision_set, status=False)
            if ansible.has_succeeded():
                provision_set.status = FINISHED
                self.undeployed_changesets.update(status=IMPLEMENTED)
            else:
                # find out whether it was aborted
                ret = ansible.process().returncode
                if ret < 0 and signal.SIGABRT == abs(ret):
                    provision_set.status = ABORTED
                else:
                    provision_set.status = FAILED
            provision_set.persist_output_log()
            provision_set.save()

        ansible.register_exit_fn(callback)

        return redirect('change:provision_set', pk=provision_set.pk)


class TerminateView(PermissionRequiredMixin, View):
    """
    This view is for terminating Ansible deployments preemptively.
    """
    permission_required = 'change.deploy_changeset'

    def get(self, request, pk=None):
        """
        This view terminates the provision set.
        """
        provision_set = get_object_or_404(ProvisionSet, pk=pk)

        if provision_set.status != RUNNING:
            return HttpResponse('Not running Provisioning can not be terminated!', status=409)

        if not globals.provisioning_pid:
            return HttpResponse('Provision was not started!', status=409)

        try:
            os.kill(globals.provisioning_pid, signal.SIGABRT)
        except ProcessLookupError:
            return HttpResponse('Provision process was not found!', status=400)

        # TODO: where should we redirect?
        return redirect('change:provision_set', pk=provision_set.pk)


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


# Provisions
class ProvisionsView(PermissionRequiredMixin, ObjectListView):
    permission_required = 'change:view_provisionset'
    queryset = ProvisionSet.objects.order_by('-created')
    table = tables.ProvisionTable
    template_name = 'change/provision_list.html'


class ProvisionSetView(PermissionRequiredMixin, View):
    permission_required = 'change:view_provisionset'

    def get(self, request, pk):
        provision_set = get_object_or_404(ProvisionSet, pk=pk)

        changes_table = tables.ProvisioningChangesTable(data=provision_set.changesets.all())

        return render(request, 'change/provision.html', context={
            'provision_set': provision_set,
            'changes_table': changes_table,
        })
