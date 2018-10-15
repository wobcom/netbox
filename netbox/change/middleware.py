from django.contrib.sessions.models import Session
from django.db.models.signals import pre_save, post_save

from extras.models import ObjectChange

from .models import ChangedField

blacklist = [
    ChangedField,
    ObjectChange,
    Session
]


def before_save(request):
    worked_on = False

    def before_save_internal(sender, instance, **kwargs):
        # TODO: urgh!
        nonlocal worked_on
        if sender in blacklist:
            return
        try:
            old_instance = sender.objects.get(id=instance.id)
        except sender.DoesNotExist:
            return
        for field in sender._meta.fields:
            old_value = getattr(old_instance, field.name)
            new_value = getattr(instance, field.name)

            if new_value == old_value:
                continue

            ChangedField(
                changed_object=instance,
                field=field.name,
                old_value=getattr(old_instance, field.name),
                new_value=getattr(instance, field.name),
                user=request.user,
            ).save()
        worked_on = True

    def after_save_internal(sender, instance, **kwargs):
        if sender in blacklist or worked_on:
            return
        for field in sender._meta.fields:
            ChangedField(
                changed_object=instance,
                field=field.name,
                old_value=None,
                new_value=getattr(instance, field.name),
                user=request.user,
            ).save()

    pre_save.connect(before_save_internal, weak=False, dispatch_uid="chgfield")
    post_save.connect(after_save_internal, weak=False, dispatch_uid="chgfield")


class FieldChangeMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.session.get("in_change", False):
            before_save(request)

        return self.get_response(request)
