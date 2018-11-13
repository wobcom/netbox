import io
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import models
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views.generic import View
from django.views.generic.edit import CreateView
import topdesk

from netbox import configuration
from .models import ChangeInformation, ChangedField, ChangedObject, ChangeSet, \
                    DRAFT, IN_REVIEW


@method_decorator(login_required, name='dispatch')
class ChangeFormView(CreateView):
    model = ChangeInformation
    fields = '__all__'
    success_url = '/'


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
            request.session['change_started'] = str(datetime.now())
            return redirect('/change/form')

        # we finished our change. we generate the changeset now
        changeset = ChangeSet()
        changeset.user = request.user

        #now we need to gather the changes for our set

        # the standard deserialization from datetime
        change_time = datetime.strptime(request.session['change_started'],
                                        '%Y-%m-%d %H:%M:%S.%f')
        change_objs = ChangedObject.objects.filter(user=request.user,
                                                   time__gt=change_time)
        change_fields = ChangedField.objects.filter(user=request.user,
                                                    time__gt=change_time)

        if not change_fields.count() and not change_objs.count():
            return render(request, 'change/list.html', {
                'changeset': None
            })

        changeset.save()
        changeset.changedfield_set.add(*change_fields)
        changeset.changedobject_set.add(*change_objs)
        changeset.save()

        # for now just render the result
        return render(request, 'change/list.html', {
            'changeset': changeset
        })

def trigger_netbox_change(obj):
    # TODO: verify=False is debug!
    tp = topdesk.Topdesk(configuration.TOPDESK_URL, verify=False)

    tp.login_operator(configuration.TOPDESK_USERNAME,
                      configuration.TOPDESK_PASSWORD)

    request_txt = 'Change #{} was created in Netbox by {}.\n\nChanges:\n{}'
    request_txt = request_txt.format(obj.id, obj.user, obj.to_yaml())
    data = {
        'requester': {
            'id': configuration.TOPDESK_REQ_ID,
            'name': configuration.TOPDESK_REQ_NAME,
        },
        'briefDescription': 'Change #{} was created in Netbox'.format(obj.id),
        'changeType': 'extensive'
    }
    res = tp.create_operator_change(data)
    res_id = res['id']
    obj.ticket_id = res_id
    obj.save()
    tp.create_operator_change_attachment(res_id, io.StringIO(request_txt))
    return res_id

@method_decorator(login_required, name='dispatch')
class AcceptView(View):
    model = ChangeSet

    def get(self, request, pk=None):
        """
        This view is triggered when the change was accepted by the operator.
        The changes are reverted, and the status of the object is changed to in
        review.
        TODO: sync with TOPdesk
        """
        obj = get_object_or_404(self.model, pk=pk)

        if obj.status != DRAFT:
            return HttpResponseForbidden('Change was already accepted!')

        for change in obj.changedfield_set.all():
            change.revert()
        for change in obj.changedobject_set.all():
            change.revert()

        obj.status = IN_REVIEW
        obj.save()

        res_id = trigger_netbox_change(obj)

        return redirect('/')
