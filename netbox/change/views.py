from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import models
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views.generic import View

from .models import ChangedField, ChangeSet, IN_REVIEW

@method_decorator(login_required, name='dispatch')
class ToggleView(View):
    def get(self, request):
        request.session["in_change"] = not request.session.get("in_change", False)
        # we started the change and are done
        if request.session["in_change"]:
            request.session["change_started"] = str(datetime.now())
            to_redirect = request.META.get("HTTP_REFERER", "/")
            if to_redirect.endswith('/change/begin/'):
                to_redirect = '/'
            return redirect(to_redirect)

        # we finished our change. we generate the changeset now
        changeset = ChangeSet()

        #now we need to gather the changes for our set

        # the standard deserialization from datetime
        change_time = datetime.strptime(request.session["change_started"],
                                        "%Y-%m-%d %H:%M:%S.%f")
        change_objs = ChangedField.objects.filter(user=request.user,
                                                  time__gt=change_time)

        if not change_objs.count():
            return render(request, 'change/list.html', {
                'changeset': None
            })

        changeset.save()
        changeset.changedfield_set.add(*change_objs)

        # for now just render the result
        return render(request, 'change/list.html', {
            'changeset': changeset
        })

@method_decorator(login_required, name='dispatch')
class AcceptView(View):
    model = ChangeSet

    def get(self, request, pk=None):
        obj = get_object_or_404(self.model, pk=pk)
        for change in obj.changedfield_set.all():
            change.revert()

        obj.status = IN_REVIEW
        obj.save()

        return redirect('/')
