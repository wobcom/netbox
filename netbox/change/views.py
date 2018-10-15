from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import models
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.views.generic import View

from .models import ChangedField, ChangeSet

@method_decorator(login_required, name='dispatch')
class ToggleView(View):
    def get(self, request):
        request.session["in_change"] = not request.session.get("in_change", False)
        # we started the change and are done
        if request.session["in_change"]:
            request.session["change_started"] = str(datetime.now())
            return redirect(request.META.get("HTTP_REFERER", "/"))

        # we finished our change. we generate the changeset now
        changeset = ChangeSet()
        changeset.save()

        #now we need to gather the changes for our set

        # the standard deserialization from datetime
        change_time = datetime.strptime(request.session["change_started"],
                                        "%Y-%m-%d %H:%M:%S.%f")
        change_objs = ChangedField.objects.filter(user=request.user,
                                                  time__gt=change_time)

        changeset.changedfield_set.add(*change_objs)

        # for now just render the result
        return render(request, 'change/list.html', {
            'changes': changeset.to_yaml()
        })
