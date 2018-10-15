from datetime import datetime
import yaml

from django.contrib.auth.decorators import login_required
from django.db import models
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.views.generic import View

from .models import ChangedField

@method_decorator(login_required, name='dispatch')
class ToggleView(View):
    def get(self, request):
        request.session["in_change"] = not request.session.get("in_change", False)
        # we started the change and are done
        if request.session["in_change"]:
            request.session["change_started"] = str(datetime.now())
            return redirect(request.META.get("HTTP_REFERER", "/"))

        # we finished our change. now we need to gather the changes

        # the standard deserialization from datetime
        change_time = datetime.strptime(request.session["change_started"],
                                        "%Y-%m-%d %H:%M:%S.%f")
        change_objs = ChangedField.objects.filter(user=request.user,
                                                  time__gt=change_time)

        changes = []

        for change in change_objs:
            changed_object = {}

            for field in change.changed_object._meta.fields:
                if field.__class__ == models.ForeignKey:
                    continue

                fname = field.name
                changed_object[fname] = getattr(change.changed_object, fname)


            changes.append({
                "field": change.field,
                "old_value": change.old_value,
                "new_value": change.new_value,
                "type": str(change.changed_object_type),
                "changed_object": changed_object
            })

        # for now just render the result
        return render(request, 'change/list.html', {
            'changes': yaml.dump(changes,explicit_start=True,
                                 default_flow_style=False),
        })
