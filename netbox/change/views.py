from datetime import datetime

from django.contrib.auth.decorators import login_required
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
        changes = ChangedField.objects.filter(user=request.user,
                                              time__gt=change_time)

        # for now just render the result
        return render(request, 'change/list.html', {
            'changes': changes,
        })
