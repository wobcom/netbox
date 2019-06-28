"""
The changes middleware checks whether we are in a change by checking the user
cookies. If we are, it adds signal handlers that fire before and after saving
a model to make sure we insert appropriate changes for them.

Some models are blacklisted to avoid recursion. This should probably be changed
to be a whitelist instead, since right now all Django models are captured as
well (TODO).
"""
import pickle

from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.sessions.models import Session
from django.db import models
from django.db.models.signals import pre_save, post_save, m2m_changed
from django.shortcuts import redirect
from django.utils import timezone

from extras.models import ObjectChange

from .models import ChangedField, ChangedObject, ChangeSet, AffectedCustomer, \
    ChangeInformation
from .utilities import redirect_to_referer

CHANGE_BLACKLIST = [
    AffectedCustomer,
    ChangedField,
    ChangedObject,
    ChangeInformation,
    ChangeSet,
    ObjectChange,
    Session,
    User,
    ContentType,
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
    handled = []
    try:
        changeset = ChangeSet.objects.get(pk=request.session['change_id'])
    except ChangeSet.DoesNotExist:
        return handled

    def before_save_internal(sender, instance, **kwargs):
        """
        This function only triggers when the instance already exists. Otherwise
        it will bail. It records all field changes individually.
        """
        if sender in CHANGE_BLACKLIST:
            return

        # see whether the object already exists; if not, bail
        try:
            old_instance = sender.objects.get(pk=instance.pk)
        except sender.DoesNotExist:
            return

        # create a new DB row for each updated field
        for field in sender._meta.fields:
            old_value = getattr(old_instance, field.name)
            new_value = getattr(instance, field.name)

            # field was not changed; this also blocks changes from None to
            # empty string and the like (as per request by @cdieckhoff)
            if new_value == old_value or not new_value and not old_value:
                continue

            cf = ChangedField(
                changed_object=instance,
                field=field.name,
                old_value=pickle.dumps(getattr(old_instance, field.name)),
                new_value=pickle.dumps(getattr(instance, field.name)),
                user=request.user,
            )
            cf.save()
            changeset.changedfield_set.add(cf)
        changeset.updated = timezone.now()
        changeset.save()
        handled.append(instance)


    def after_save_internal(sender, instance, **kwargs):
        """
        This function only triggers when the instance is new; it will save the
        whole thing.
        """
        if sender in CHANGE_BLACKLIST or instance in handled:
            return
        co = ChangedObject(
            changed_object=instance,
            changed_object_data=pickle.dumps(instance),
            user=request.user,
        )
        co.save()
        changeset.changedobject_set.add(co)
        changeset.updated = timezone.now()
        changeset.save()
        handled.append(instance)

    def m2m_changed_internal(sender, instance, action, model=None, pk_set=None, **kwargs):
        if not pk_set:
            pk_set = {}
        if action not in ['post_add', 'pre_remove']:
            return
        if sender in CHANGE_BLACKLIST:
            return

        if action == 'post_add':
            for pk in pk_set:
                through = sender.objects.get(**{
                    '{}_id'.format(instance._meta.model.__name__.lower()): instance.pk,
                    '{}_id'.format(model.__name__.lower()): pk
                })
                co = ChangedObject(
                    changed_object=through,
                    changed_object_data=pickle.dumps(through),
                    user=request.user,
                )
                co.save()
                changeset.changedobject_set.add(co)
                changeset.updated = timezone.now()
                changeset.save()



    # we need to install them strongly, because they are closures;
    # otherwise django will throw away the weak references at the end of this
    # function (we need it to be there until the end of this request)
    pre_save.connect(before_save_internal, weak=False, dispatch_uid='chgfield')
    post_save.connect(after_save_internal, weak=False, dispatch_uid='chgfield')
    m2m_changed.connect(m2m_changed_internal, weak=False, dispatch_uid='chgfield')
    return [{'handler': before_save_internal, 'signal': pre_save},
            {'handler': after_save_internal, 'signal': post_save},
            {'handler': m2m_changed_internal, 'signal': m2m_changed}]


SITE_BLACKLIST = ["add/", "edit/", "delete/", "import/", "change/toggle/"]


class FieldChangeMiddleware(object):
    """
    This  middleware checks whether we or someone else is in change and wires
    up the world accordingly. Its in-depth documentation can be found in the
    docs/ directory, because it's pretty gnarly.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # fast track for admin stuff
        if request.path.startswith('/admin'):
            return self.get_response(request)

        in_change = request.session.get('in_change', False)
        to_uninstall = []
        if in_change:
            c = None
            try:
                c = ChangeSet.objects.get(pk=request.session['change_id'])
            except ChangeSet.DoesNotExist:
                messages.warning(request, "Your change session was deleted.")
                request.session['in_change'] = False

            if c and c.in_use():
                # we do not install the hooks if we're currently toggling,
                # because otherwise our reverts would be recorded
                if request.path != '/change/toggle/':
                    to_uninstall = install_save_hooks(request)
                wrong_url = request.path not in ['/change/form/',
                                                 '/change/toggle/']
                if not request.session.get('change_information') and wrong_url:
                    return redirect('/change/form')
            elif c:
                messages.warning(request, "Your change session timed out.")
                request.session['in_change'] = False
        else:
            # this is the simplest solution, albeit incredibly dirty
            cs = ChangeSet.objects.filter(active=True)
            request.session['foreign_change'] = cs.exists()
            if cs.exists() and cs.first().id != request.session.get('change_id'):
                c = cs.first()
                # this costs a lot for every request
                if c.in_use():
                    message = "User {} is currently making a change."
                    messages.warning(request, message.format(c.user.username))
                    if any(request.path.endswith(s) for s in SITE_BLACKLIST):
                        return redirect_to_referer(request)
                else:
                    c.active = False
                    c.revert()
                    c.save()

        response = self.get_response(request)
        for handler in to_uninstall:
            handler['signal'].disconnect(handler['handler'],
                                         dispatch_uid='chgfield')
        return response
