from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.safestring import mark_safe
from django.views.generic import View
from django.views.generic.edit import CreateView
from diplomacy import Diplomat

from netbox import configuration
from dcim.models import Device
from .forms import ChangeInformationForm
from .models import (ChangeInformation, ChangeSet, ProvisionSet, ACCEPTED,
    IMPLEMENTED, RUNNING, FINISHED, FAILED)


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

        db = configuration.DATABASE
        # postgresql is a given in the context of netbox
        # TODO: is there a better way to obtain a connection string?
        odin = Diplomat("odin", 'postgresql://{}:{}@{}/{}'.format(
            db['USER'], db['PASSWORD'], db['HOST'], db['NAME']
        ))

        odin.wait()

        if not odin.has_succeeded():
            messages.warning(
             request,
             "Odin has failed! Error message: {}".format(diplo.error_output())
            )
            provision_set.deployment_status = FAILED
            provision_set.save()
            return redirect('home')

        ansible = Diplomat(
            "ansible-playbook", "-K", "-i", "_build/inventory.ini",
            "_build/deploy.yml", "--check", "--diff", # the last two are for testing
            out=odin.output_file_name(),
            err=odin.output_file_name()
        )

        def callback():
            # TODO: what do we set here?
            if ansible.has_succeeded():
                provision_set.status = FINISHED
            else:
                provision_set.deployment_status = FAILED
            provision_set.save()

        ansible.register_exit_fn(callback)

        provision_set.output_log = ansible.output_file_name()
        provision_set.error_log = ansible.error_file_name()
        provision_set.deployment_status = RUNNING
        provision_set.save()

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
