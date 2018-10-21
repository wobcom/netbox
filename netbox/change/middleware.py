from django.contrib.sessions.models import Session
from django.db.models.signals import pre_save, post_save

from extras.models import ObjectChange

from .models import ChangedField, ChangeSet

CHANGE_BLACKLIST = [
    ChangedField,
    ObjectChange,
    ChangeSet,
    Session
]


def before_save(request):
    old_instance = None
    def before_save_internal(sender, instance, **kwargs):
        if sender in CHANGE_BLACKLIST:
            return
        try:
            nonlocal old_instance
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

        # we don't have to call save hooks anymore, since we already treated it
        post_save.disconnect(after_save_internal,
                             dispatch_uid="chgfield")



    def after_save_internal(sender, instance, **kwargs):
        if sender in CHANGE_BLACKLIST:
            return
        for field in sender._meta.fields:
            ChangedField(
                changed_object=instance,
                field=field.name,
                old_value=None,
                new_value=getattr(instance, field.name),
                user=request.user,
            ).save()

    def after_save_rollback(sender, instance, **kwargs):
        if sender in CHANGE_BLACKLIST:
            return
        post_save.disconnect(after_save_rollback,
                             dispatch_uid="chgfield_rollback")
        if old_instance:
            instance = sender.objects.get(id=old_instance.id)

            for field in sender._meta.fields:
                field = field.name
                setattr(instance, field, getattr(old_instance, field))

            instance.save()

    pre_save.connect(before_save_internal, weak=False, dispatch_uid="chgfield")
    post_save.connect(after_save_internal, weak=False, dispatch_uid="chgfield")
    post_save.connect(after_save_rollback, weak=False,
                      dispatch_uid="chgfield_rollback")


class FieldChangeMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.session.get("in_change", False):
            before_save(request)

        return self.get_response(request)
