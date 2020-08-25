import os
import signal

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpResponse
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import View
from django.views.generic.edit import CreateView
from django.views.decorators.cache import never_cache
from django.utils import timezone

from utilities.views import ObjectListView, GetReturnURLMixin
from .forms import ChangeInformationForm
from .models import ChangeInformation, ChangeSet, AlreadyExistsError, ProvisionSet, ProvisionFailed
from . import tables


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
        context['obj'] = ChangeInformation()
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
        try:
            provision_set.run_prepare()
        except ProvisionFailed as e:
            provision_set.delete()
            messages.error(request, f"Provision can not be started: {e}")
            return redirect('change:deploy')

        return redirect('change:provision_set', pk=provision_set.pk)


class SecondStageView(PermissionRequiredMixin, View):
    permission_required = 'change.change_provisionset'

    def post(self, request, pk=None):

        provision_set = ProvisionSet.objects.get(pk=pk)

        try:
            provision_set.run_commit()
        except ProvisionFailed as e:
            messages.error(request, f"Provision failed: {e}")

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

        provision_set.terminate()

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
