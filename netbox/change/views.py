from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views.generic import View

@method_decorator(login_required, name='dispatch')
class ToggleView(View):
    def get(self, request):
        request.session["in_change"] = not request.session.get("in_change", False)
        return redirect(request.META.get("HTTP_REFERER", "/"))
