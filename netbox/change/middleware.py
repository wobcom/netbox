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
from django.db.models.signals import pre_save, post_save, m2m_changed, pre_delete
from django.shortcuts import redirect
from django.utils import timezone

from extras.models import ObjectChange
from netbox import settings

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
                through = model.objects.get(**{
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

    def before_delete_internal(sender, instance, **kwargs):
        if sender in CHANGE_BLACKLIST or instance in handled:
            return
        co = ChangedObject(
            changed_object=instance,
            changed_object_data=pickle.dumps(instance),
            deleted=True,
            user=request.user,
        )
        co.save()
        changeset.changedobject_set.add(co)
        changeset.updated = timezone.now()
        changeset.save()
        handled.append(instance)

    # we need to install them strongly, because they are closures;
    # otherwise django will throw away the weak references at the end of this
    # function (we need it to be there until the end of this request)
    pre_save.connect(before_save_internal, weak=False, dispatch_uid='chgfield')
    post_save.connect(after_save_internal, weak=False, dispatch_uid='chgfield')
    pre_delete.connect(before_delete_internal, weak=False, dispatch_uid='chgfield')
    m2m_changed.connect(m2m_changed_internal, weak=False, dispatch_uid='chgfield')
    return [{'handler': before_save_internal, 'signal': pre_save},
            {'handler': after_save_internal, 'signal': post_save},
            {'handler': before_delete_internal, 'signal': pre_delete},
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
        # The change middleware is responsible for a couple of things related
        # to changes. Let’s start with a TL;DR bullet point overview:
        #
        # - If we are in a change we check whether it’s still active and
        #   install the hooks that record the changes.
        # - If someone else is in a change, we give the user a message and
        #   disable all buttons that change something.
        # - Otherwise we don’t do anything.
        #
        # Either of the first points is fairly complex on its own and deals
        # with a couple of different things at once. Let’s go through the
        # source code of the function together, and find out what exactly!
        #
        # We’re starting out by checking whether our user does admin-y things.
        # If they do, we put them on the fast track and ignore them.
        #
        # We also need to set up a list of hooks we need to uninstall (called
        # `to_uninstall` here). It’s initially empty, but depending on where we
        # will go during our little voyage, it might get filled with hooks that
        # need to be uninstalled.
        if request.path.startswith('/admin'):
            return self.get_response(request)

        in_change = request.session.get('in_change', False)
        to_uninstall = []

        # Chapter I: We are in a change
        #
        # If we find ourselves inside a change, we should first get the change set we are
        # working with. We have to take some precautions, because someone might have
        # deleted the change set while it’s still active.
        if in_change:
            c = None
            try:
                c = ChangeSet.objects.get(pk=request.session['change_id'])
            except ChangeSet.DoesNotExist:
                messages.warning(request, "Your change session was deleted.")
                request.session['in_change'] = False

            if c and c.in_use():
                # So, what should we do if the change is still in use? As it turns out, a
                # couple of things. First we install the save hooks that will record the
                # changes made during this request. There is one exception to that rule,
                # however: if we are currently trying to end this change during this
                # request, we will not install these hooks, because we would otherwise
                # record the rollback as well, and we do not want that.
                if request.path != '/change/toggle/':
                    to_uninstall = install_save_hooks(request)

                # Alright, then are we done here? Not quite. We will also have to check
                # whether we have filled out the form that starts off a change yet! If
                # the user hasn’t we will redirect them to the form. One exception to
                # that rule is if the change ends, which means that they effectively
                # cancelled the change.
                wrong_url = request.path not in ['/change/form/',
                                                 '/change/toggle/']
                if not request.session.get('change_information') and wrong_url:
                    return redirect('/change/form')

            # Now we are done, and can take care of the other alternative, which is that
            # our change timed out.
            elif c:
                # If it timed out, we will simply unset the cookie that tells us that the
                # user is currently in a change, and give the user a visible message that
                # tells them that their session has timed out.
                messages.warning(request, "Your change session timed out.")
                request.session['in_change'] = False

        # That is all we need to do if we are in a change.
        #
        # Chapter II: We are not in a change, but someone else might be
        #
        else:
            # We are not in a change, so what do we have to do?
            #
            # First, we see if there are any active changes.
            cs = ChangeSet.objects.filter(active=True)

            # Now, let’s check whether there is someone making a change.
            if cs.exists() and cs.first().id != request.session.get('change_id'):
                # First, we get the change that is active.
                c = cs.first()

                # Secondly, we need to check whether that change is actually still
                # active—the user might have left without finalizing their change after
                # all.
                if c.in_use():
                    # If the change really is currently active, we will leave the user
                    # with a message and, if they attempted to do an edit of some sort,
                    # redirect them to where they came from instead. We’ll also set a
                    # cookie so that we can disable editing!
                    request.session['foreign_change'] = True
                    message = "User {} is currently making a change."
                    messages.warning(request, message.format(c.user.username))
                    if any(request.path.endswith(s) for s in SITE_BLACKLIST):
                        return redirect_to_referer(request)
                # What, however, if the changeset is not active anymore?
                else:
                    # Well, helpful citizens as we are, we should mark this change as not
                    # active, revert it, save that result to the database, and unset the
                    # cookie we might have set before.
                    request.session['foreign_change'] = False
                    c.active = False
                    c.revert()
                    c.save()
            # if we’re not in a change, then we’ll also unset the cookie, just for safety.
            else:
                request.session['foreign_change'] = False

            # If we are not in a change, we’ll have to do another thing: we’ll have to
            # check whether we are allowed to edit anything outside a change. If not,
            # we’ll have to disallow doing that. To that end, we look for the setting
            # `NEED_CHANGE_FOR_WRITE`, and if this is set, we’ll redirect the person who
            # tries to edit anything.
            if settings.NEED_CHANGE_FOR_WRITE:
                # dont check for change/toggle
                if any(request.path.endswith(s) for s in SITE_BLACKLIST[:-1]):
                    return redirect_to_referer(request)

        # Epilogue
        #
        # Once we are done handling the change, we can now finally process the request.
        # As this is a middleware, we are not concerned with how the actual handler works,
        # and we simple demand to get a response.
        response = self.get_response(request)

        # But there is one more thing left for us to do: uninstall the signal handlers.
        # So let’s take care of that really quick:
        for handler in to_uninstall:
            handler['signal'].disconnect(handler['handler'],
                                         dispatch_uid='chgfield')

        # And now, after this tumultuous, arduous ride, we are finally able to return the
        # response:

        return response
