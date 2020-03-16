import os
import signal
import json

from copy import deepcopy

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpResponse
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import View
from django.views.generic.edit import CreateView
from django.views.decorators.cache import never_cache
from django.utils import timezone
from django.db import IntegrityError
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from diplomacy import Diplomat

from netbox import configuration
from utilities.views import ObjectListView, GetReturnURLMixin
from .forms import ChangeInformationForm
from .models import ChangeInformation, ChangeSet, AlreadyExistsError, ProvisionSet, PID
from . import tables


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


def prepare_provisioning_stage(stage_configuration, provision_set):

    parsed_stage_config = []

    for job in stage_configuration:
        parsed_job = deepcopy(job)
        parsed_job['command'] = [e.format(provision_set=provision_set) for e in job['command']]
        parsed_stage_config.append(parsed_job)

    return parsed_stage_config


def run_provisioning_stage(stage_configuration, finished_callback=lambda status: status):
    """
    runs a given provisioning stage

    the finished callback must be a function with an status argument, status is set to one out of:
        FINISHED, ABORTED, FAILED

    :param stage_configuration: tuple of tuples with the command specification
    :param finished_callback: callback function an end of the run func(status)
    :return: temp log file path
    """
    def write_cmd(job):
        # we stylize the input to be bold and underlined in ansi
        job.output_file().write(
            "\n\n\033[1m$ {}\033[0m\n".format(" ".join(job.cmd))
        )

    def callback(job):
        PID.set(None)
        if job.has_succeeded():
            finished_callback(status=ProvisionSet.FINISHED)
        else:
            # find out whether it was aborted
            ret = job.process().returncode
            if ret < 0 and signal.SIGABRT == abs(ret):
                finished_callback(status=ProvisionSet.ABORTED)
            else:
                finished_callback(status=ProvisionSet.FAILED)

    def job_exit_callback_creator(jobs):
        if len(jobs) == 0:
            return callback

        def job_exit_callback(job):
            if not job.has_succeeded():
                callback(job)
                return
            new_job = Diplomat(
                *jobs[0]['command'],
                out=job.output_file_name(),
                single_file=True,
                env=jobs[0].get('environment', {}),
                pre_start=write_cmd,
                on_exit=job_exit_callback_creator(jobs[1:]),
            )
            PID.set(new_job.process().pid)

        return job_exit_callback

    if len(stage_configuration) == 0:
        raise ValueError('Empty stage configuration')

    initial_job = Diplomat(*stage_configuration[0]['command'],
                           single_file=True,
                           env=stage_configuration[0].get('environment', {}),
                           pre_start=write_cmd,
                           on_exit=job_exit_callback_creator(stage_configuration[1:]))
    PID.set(initial_job.process().pid)

    return initial_job.output_file_name()


class ChangeFormView(GetReturnURLMixin, PermissionRequiredMixin, CreateView):
    """
    This view is for displaying the change form and
    open a new change.
    """
    model = ChangeInformation
    form_class = ChangeInformationForm
    success_url = '/'
    permission_required = 'change.add_changeset'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['return_url'] = self.get_return_url(self.request)
        return context

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
        request.my_change.status = ChangeSet.ACCEPTED
        request.my_change.save()

        return redirect('home')


class DeployView(PermissionRequiredMixin, View):
    """
    This view is for displaying provisioning details
    and start provisioning.
    """
    permission_required = 'change.add_provisionset'

    def __init__(self, *args, **kwargs):
        super(DeployView, self).__init__(*args, **kwargs)
        self.undeployed_changesets = ChangeSet.objects.exclude(status=ChangeSet.IMPLEMENTED)\
                                                      .exclude(status=ChangeSet.IN_REVIEW)\
                                                      .order_by('id')

    def get(self, request):

        return render(request, 'change/deploy.html', context={
            'undeployed_changesets_table': tables.ProvisioningChangesTable(data=self.undeployed_changesets),
            'undeployed_changesets': self.undeployed_changesets.count(),
            'unaccepted_changesets': self.undeployed_changesets.exclude(status=ChangeSet.ACCEPTED).count(),
        })

    def post(self, request):
        try:
            provision_set = ProvisionSet(user=request.user)
        except AlreadyExistsError:
            messages.error(
                request,
                'Provisioning can not be started, another provisioning is already running.'
            )
            return redirect('change:deploy')

        provision_set.save()

        send_provision_status(provision_set, status=True)

        self.undeployed_changesets.update(provision_set=provision_set)

        def provisioning_finished(status):
            send_provision_status(provision_set, status=False)

            if status == ProvisionSet.FINISHED:
                provision_set.status = ProvisionSet.REVIEWING
                self.undeployed_changesets.update(status=ChangeSet.IN_REVIEW)
            else:
                provision_set.status = status

            provision_set.persist_output_log()
            provision_set.save()

        log_file_path = run_provisioning_stage(
            prepare_provisioning_stage(configuration.PROVISIONING_STAGE_1, provision_set),
            provisioning_finished)
        provision_set.output_log_file = log_file_path
        provision_set.status = ProvisionSet.RUNNING
        provision_set.save()

        return redirect('change:provision_set', pk=provision_set.pk)


class SecondStageView(PermissionRequiredMixin, View):
    permission_required = 'change.change_provisionset'

    def post(self, request, pk=None):

        provision_set = ProvisionSet.objects.get(pk=pk)

        send_provision_status(provision_set, status=True)

        def provisioning_finished(status):
            provision_set.status = status
            send_provision_status(provision_set, status=False)

            if status == ProvisionSet.FINISHED:
                provision_set.changesets.update(status=ChangeSet.IMPLEMENTED)
            else:
                provision_set.changesets.update(status=ChangeSet.ACCEPTED)

            provision_set.persist_output_log(append=True)
            provision_set.save()

        log_file_path = run_provisioning_stage(
            prepare_provisioning_stage(configuration.PROVISIONING_STAGE_2, provision_set),
            provisioning_finished)

        provision_set.status = ProvisionSet.RUNNING
        provision_set.output_log_file = log_file_path
        provision_set.save()

        return redirect('change:provision_set', pk=provision_set.pk)


class TerminateView(PermissionRequiredMixin, View):
    """
    This view is for terminating Ansible deployments preemptively.
    """
    permission_required = 'change.deploy_changeset'

    def post(self, request, pk=None):
        """
        This view terminates the provision set.
        """
        provision_set = get_object_or_404(ProvisionSet, pk=pk)

        if provision_set.status != ProvisionSet.RUNNING:
            provision_set.changesets.update(status=ChangeSet.ACCEPTED)
            provision_set.status = ProvisionSet.ABORTED
            provision_set.save()
            return redirect('change:provision_set', pk=provision_set.pk)

        pid = PID.get()

        if not pid:
            return HttpResponse('Provision was not started!', status=409)

        try:
            os.kill(pid, signal.SIGABRT)
        except ProcessLookupError:
            return HttpResponse('Provision process was not found!', status=400)

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
    permission_required = 'change.view_provisionset'
    queryset = ProvisionSet.objects.order_by('-created')
    table = tables.ProvisionTable
    template_name = 'change/provision_list.html'


class ProvisionSetView(PermissionRequiredMixin, View):
    permission_required = 'change.view_provisionset'

    @never_cache
    def get(self, request, pk):
        provision_set = get_object_or_404(ProvisionSet, pk=pk)

        changes_table = tables.ProvisioningChangesTable(data=provision_set.changesets.all())

        return render(request, 'change/provision.html', context={
            'provision_set': provision_set,
            'changes_table': changes_table,
            'current_time': timezone.now(),
        })
