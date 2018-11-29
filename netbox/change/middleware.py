"""
The changes middleware checks whether we are in a change by checking the user
cookies. If we are, it adds signal handlers that fire before and after saving
a model to make sure we insert appropriate changes for them.

Some models are blacklisted to avoid recursion. This should probably be changed
to be a whitelist instead, since right now all Django models are captured as
well (TODO).
"""
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.db import models
from django.db.models.signals import pre_save, post_save
from django.shortcuts import redirect

from extras.models import ObjectChange

from .models import ChangedField, ChangedObject, ChangeSet, AffectedCustomer, \
    ChangeInformation

CHANGE_BLACKLIST = [
    AffectedCustomer,
    ChangedField,
    ChangedObject,
    ChangeInformation,
    ChangeSet,
    ObjectChange,
    Session,
    User,
]


def _model_to_dict(obj):
    """Our version of model_to_dict that doesnt add foreign key relations"""
    res = {}
    for field in obj._meta.fields:
        # we do not go deeply into the object relations. if we find a
        # foreign key, we only get the ID
        if field.__class__ == models.ForeignKey:
            fname = '{}_id'.format(field.name)
        else:
            fname = field.name
        res[fname] = str(getattr(obj, fname))
    return res


def install_save_hooks(request):
    """
    This function installs the change hooks, on pre- and one post-save.
    The pre-save hook captures all updated models, the post-save hooks captures
    all newly-created models.
    """
    changeset = ChangeSet.objects.get(pk=request.session['change_id'])

    def before_save_internal(sender, instance, **kwargs):
        """
        This function only triggers when the instance already exists. Otherwise
        it will bail. It records all field changes individually.
        """
        if sender in CHANGE_BLACKLIST:
            return

        # see whether the object already exists; if not, bail
        try:
            old_instance = sender.objects.get(id=instance.id)
        except sender.DoesNotExist:
            return

        # create a new DB row for each updated field
        for field in sender._meta.fields:
            old_value = getattr(old_instance, field.name)
            new_value = getattr(instance, field.name)

            # field was not changed
            if new_value == old_value:
                continue

            cf = ChangedField(
                changed_object=instance,
                field=field.name,
                old_value=getattr(old_instance, field.name),
                new_value=getattr(instance, field.name),
                user=request.user,
            )
            cf.save()
            changeset.changedfield_set.add(cf)

        # we don't have to call save hooks anymore, since we already treated it
        post_save.disconnect(after_save_internal,
                             dispatch_uid='chgfield')

    def after_save_internal(sender, instance, **kwargs):
        """
        This function only triggers when the instance is new; it will save the
        whole thing.
        """
        if sender in CHANGE_BLACKLIST:
            return
        co = ChangedObject(
            changed_object=instance,
            changed_object_data=_model_to_dict(instance),
            user=request.user,
        )
        co.save()
        changeset.changedobject_set.add(co)

    # we need to install them strongly, because they are closures;
    # otherwise django will throw away the weak references at the end of this
    # function (we need it to be there until the end of this request)
    pre_save.connect(before_save_internal, weak=False, dispatch_uid='chgfield')
    post_save.connect(after_save_internal, weak=False, dispatch_uid='chgfield')
    return [{'handler': before_save_internal, 'signal': pre_save},
            {'handler': after_save_internal, 'signal': post_save}]


class FieldChangeMiddleware(object):
    """
    This very simple middleware checks the `in_change` cookie. If the cookie is
    set, it installs the save hooks.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        in_change = request.session.get('in_change', False)
        to_uninstall = []
        if in_change:
            to_uninstall = install_save_hooks(request)
            wrong_url = request.path not in ['/change/form/', '/change/toggle/']
            if not request.session.get('change_information') and wrong_url:
                return redirect('/change/form')
        else:
            # TODO: this is the simplest solution, albeit incredibly dirty;
            # needs to be discussed
            cs = ChangeSet.objects.filter(active=True)
            if cs.count():
                if (request.path.endswith("edit/") or
                   request.path.endswith("delete/") or
                   request.path.endswith("change/toggle/")):
                    return redirect(request.META.get("HTTP_REFERER", "/"))
                message = "User {} is currently making a change."
                uname = cs.first().user.username
                messages.warning(request, message.format(uname))
                request.session['foreign_change'] = True
            else:
                request.session['foreign_change'] = False

        response = self.get_response(request)
        for handler in to_uninstall:
            handler['signal'].disconnect(handler['handler'],
                                         dispatch_uid='chgfield')
        return response
