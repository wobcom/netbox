import io

from django.contrib.auth.decorators import login_required
from django.db import models
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import dateparse, timezone
from django.utils.decorators import method_decorator
from django.views.generic import View
from django.views.generic.edit import CreateView
import gitlab
import topdesk

from netbox import configuration
from .models import ChangeInformation, ChangedField, ChangedObject, ChangeSet, \
    DRAFT, IN_REVIEW, REJECTED, Change
from .forms import AffectedCustomerInlineFormSet


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
        return ctx


@method_decorator(login_required, name='dispatch')
class ToggleView(View):
    def get(self, request):
        """
        This view is triggered when we begin or end a change.
        If we begin the change, we simply toggle the cookie. If we end it, we
        finalize the change and present it to the user.
        """
        request.session['in_change'] = not request.session.get('in_change', False)
        # we started the change and need to get info
        if request.session['in_change']:
            request.session['change_started'] = str(timezone.now())
            Change(user=request.user).save()
            return redirect('/change/form')
        Change.objects.filter(user=request.user).delete()

        # we finished our change. we generate the changeset now
        changeset = ChangeSet()
        changeset.user = request.user
        info_id = request.session.get('change_information')
        change_information = None
        if info_id:
            # TODO: why are there stale information IDs?
            change_information = ChangeInformation.objects.get(pk=info_id)
            changeset.change_information = change_information

        # now we need to gather the changes for our set

        # the standard deserialization from timezone
        started_str = request.session['change_started']
        change_time = dateparse.parse_datetime(started_str)
        change_objs = ChangedObject.objects.filter(user=request.user,
                                                   time__gt=change_time)
        change_fields = ChangedField.objects.filter(user=request.user,
                                                    time__gt=change_time)

        if not change_fields.count() and not change_objs.count():
            if change_information:
                del request.session['change_information']
                del request.session['change_started']
                change_information.delete()
            return render(request, 'change/list.html', {
                'changeset': None
            })

        changeset.save()
        changeset.changedfield_set.add(*change_fields)
        changeset.changedobject_set.add(*change_objs)
        changeset.save()

        # for now just render the result
        res = render(request, 'change/list.html', {
            'changeset': changeset
        })

        for change in changeset.changedfield_set.all():
            change.revert()
        for change in changeset.changedobject_set.all():
            change.revert()

        if 'change_information' not in request.session:
            return HttpResponseForbidden('You need to fill out the change form!')

        del request.session['change_information']
        del request.session['change_started']

        return res


def trigger_topdesk_change(obj):
    # TODO: verify=False is debug!
    tp = topdesk.Topdesk(configuration.TOPDESK_URL, verify=False,
                         app_creds=(configuration.TOPDESK_USERNAME,
                                    configuration.TOPDESK_PASSWORD))

    request_txt = 'Change #{} was created in Netbox by {}.\n\nSummary:\n{}'
    request_txt = request_txt.format(obj.id, obj.user,
                                     obj.executive_summary(no_markdown=True))
    data = {
        'requester': {
            'id': configuration.TOPDESK_REQ_ID,
            'name': configuration.TOPDESK_REQ_NAME,
        },
        'briefDescription': 'Change #{} was created in Netbox'.format(obj.id),
        'changeType': 'simple',
        'request': request_txt,
    }
    # TODO: incidents work, check
    res = tp.create_operator_change(data)
    res_id = res['id']
    obj.ticket_id = res_id
    obj.save()
    return res_id


ISSUE_TXT = """Change #{} was created in Netbox by {} (TOPdesk ticket {}).

## Executive Summary

{}

## YAML Summary:
```yaml
{}
```
"""


def open_gitlab_issue(o):
    gl = gitlab.Gitlab(configuration.GITLAB_URL, configuration.GITLAB_TOKEN)
    project = gl.projects.get(configuration.GITLAB_PROJECT_ID)
    yaml = o.to_yaml()
    issue_txt = ISSUE_TXT.format(o.id, o.user, o.ticket_id,
                                 o.executive_summary(), yaml)
    emergency_label = ['emergency'] if o.change_information.is_emergency else []
    branch_name = 'change_{}'.format(o.id)
    project.branches.create({
        'branch': branch_name,
        'ref': 'master'
    })
    project.commits.create({
        'id': project.id,
        'branch': branch_name,
        'commit_message': 'Autocommit from Netbox (Change #{})'.format(o.id),
        'author_name': 'Netbox',
        'actions': [{
            'action': 'create',
            'file_path': 'files/change_{}.yaml'.format(o.id),
            'content': yaml
        }]
    })
    project.mergerequests.create({
        'title': 'Change #{} was created in Netbox'.format(o.id),
        'description': issue_txt,
        'source_branch': branch_name,
        'target_branch': 'master',
        'labels': ['netbox', 'unreviewed'] + emergency_label
    })


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

        res_id = trigger_topdesk_change(obj)
        obj.ticket_id = res_id
        obj.save()
        open_gitlab_issue(obj)

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
