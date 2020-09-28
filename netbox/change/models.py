import pickle
import json
import logging
from datetime import timedelta
from topdesk import Topdesk
from tempfile import NamedTemporaryFile
from os.path import realpath

from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone

from dcim.models import Device, Interface
from dcim.constants import *
from virtualization.models import VirtualMachine

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from dcim.constants import *
from .odin import *

logger = logging.getLogger(__name__)

DEVICE_ROLE_TOPOLOGY_WHITELIST = ['leaf', 'spine', 'superspine']
NO_CHANGE = 0
OWN_CHANGE = 1
FOREIGN_CHANGE = 2


class ChangeInformation(models.Model):
    """Meta information about a change."""
    name = models.CharField(max_length=256, verbose_name="Change Title")
    topdesk_change_number = models.CharField(max_length=50, null=True, blank=True)
    is_emergency = models.BooleanField(default=False)

    def executive_summary(self, no_markdown=True):
        return self.name

    def topdesk_change(self):
        if not settings.TOPDESK_URL or self.is_emergency:
            return
        t = Topdesk(settings.TOPDESK_URL,
                    verify=settings.TOPDESK_SSL_VERIFICATION,
                    app_creds=(settings.TOPDESK_USER, settings.TOPDESK_TOKEN))
        return t.operator_change(id_=self.topdesk_change_number)

    def topdesk_url(self):
        if not settings.TOPDESK_URL or self.is_emergency:
            return

        base_url = "{}/tas/secure/contained/newchange?action=show&unid={}"

        return base_url.format(settings.TOPDESK_URL, self.topdesk_change()['id'])


class ChangeSetManager(models.Manager):
    def get_queryset(self):
        return super(ChangeSetManager, self).get_queryset()\
            .select_related('change_information', 'user')


class ChangeSet(models.Model):
    """
    A change set always refers to a ticket.
    """
    DRAFT = 1
    IN_REVIEW = 2
    ACCEPTED = 3
    IMPLEMENTED = 4

    objects = ChangeSetManager()
    active = models.BooleanField(default=False)
    change_information = models.ForeignKey(
        to=ChangeInformation,
        on_delete=models.CASCADE,
        related_name='information',
        null=True
    )
    started = models.DateTimeField(
        auto_now_add=True,
        editable=False
    )
    updated = models.DateTimeField(
        auto_now_add=True,
        editable=False
    )
    user = models.ForeignKey(
        to=User,
        on_delete=models.SET_NULL,
        related_name='changesets',
        blank=True,
        null=True
    )

    status = models.SmallIntegerField(
        default=DRAFT,
        choices=(
            (DRAFT, 'Draft'),
            (IN_REVIEW, 'Under Review'),
            (ACCEPTED, 'Accepted'),
            (IMPLEMENTED, 'Implemented'),
        )
    )

    provision_set = models.ForeignKey(
        to='ProvisionSet',
        on_delete=models.SET_NULL,
        related_name='changesets',
        blank=True,
        null=True,
    )

    def __init__(self, *args, **kwargs):
        super(ChangeSet, self).__init__(*args, **kwargs)

    class Meta:
        permissions = [
            ('deploy_changeset', 'Can deploy Changesets')
        ]

    @staticmethod
    def change_state(user=None):
        """
        Get actual change state
        :param user: user for which the state should be checked, maybe None
        :return: integer value corresponding to *_CHANGE constants
        """
        if user.is_anonymous:
            return NO_CHANGE
        try:
            ChangeSet.objects.get(active=True, user=user)
            return OWN_CHANGE
        except ChangeSet.DoesNotExist:
            return NO_CHANGE

    def executive_summary(self, no_markdown=False):
        return self.change_information.executive_summary(no_markdown=no_markdown)

    def in_use(self):
        threshold = timedelta(minutes=settings.CHANGE_SESSION_TIMEOUT)
        before = timezone.now() - threshold

        return self.updated > before

    def topdesk_url(self):
        return self.change_information.topdesk_url()

    def __str__(self):
        return '#{}: {}'.format(self.id, self.change_information.name if self.change_information else '')


class BadTransition(Exception):
    pass


class ProvisionFailed(Exception):
    pass


class AlreadyExistsError(Exception):
    def __init__(self, *args, active=None):
        super(AlreadyExistsError, self).__init__(*args)
        self.active = active


class UnexpectedState(Exception):
    pass


class ProvStateMachine:
    """
    State machine helper for provision sets.

    The following invariants will be guaranteed:

    - We only do valid transitions.
    - In the __exit__ block we transition into FAILED if any exception is leaked.
    - We save the provision set in the exit block as well as every time transition_ is called
      Keep this in mind if you maintain a reference to the same prov_set.
    """
    def __init__(self, prov_set):
        self.prov_set = prov_set

    def __enter__(self):
        pass

    def __exit__(self, exty, exva, extr):
        if exty or exva or extr:
            logger.error("Exception caught during state transition block. Moving into failed state")
            self.prov_set.fail()


class ProvisionSet(models.Model):
    NOT_STARTED = "not_started"
    RUNNING = "running"
    PREPARE = "prepare"
    COMMIT = "commit"
    FINISHED = "finished"
    FAILED = "failed"
    ABORTED = "aborted"
    REVIEWING = "reviewing"

    state_labels = {
        NOT_STARTED: "Not started",
        RUNNING: "Running",
        PREPARE: "Prepare",
        COMMIT: "Commit",
        FINISHED: "Finished",
        FAILED: "Failed",
        ABORTED: "Aborted",
        REVIEWING: "Reviewing",
    }

    valid_transitions = {
        NOT_STARTED: (PREPARE, ABORTED, FAILED),
        PREPARE: (PREPARE, REVIEWING, FAILED, ABORTED),
        REVIEWING: (COMMIT, ABORTED),
        COMMIT: (COMMIT, FINISHED, FAILED, ABORTED),
        ABORTED: (),
        FAILED: (),
        FINISHED: (),
    }

    created = models.DateTimeField(
        auto_now_add=True,
        editable=False,
        null=True,
    )
    updated = models.DateTimeField(
        auto_now=True,
        null=True,
    )
    user = models.ForeignKey(
        to=User,
        on_delete=models.SET_NULL,
        related_name='+',
        blank=True,
        null=True,
    )

    output_log_file = models.CharField(max_length=512, blank=True, null=True)
    odin_output = models.TextField(blank=True, null=True)
    prepare_log = models.TextField(blank=True, null=True)
    commit_log = models.TextField(blank=True, null=True)
    state = models.CharField(
        max_length=20,
        default=NOT_STARTED,
        choices=state_labels.items()
    )

    def __init__(self, *args, **kwargs):
        super(ProvisionSet, self).__init__(*args, **kwargs)
        active = self.active_exists()
        if active and not self.pk:
            raise AlreadyExistsError('An unfinished provision already exists.', active=active[0])

    def __unsafe_transition(self, state):
        """
        Forces a transition into a state without checking the validity.
        Users of this class should use transition instead.
        This is an internal primitive for transition as well the __exit__ function.
        """
        self.state = state
        self.__save_state()
        self.__notify_state()
        if self.state == self.FINISHED:
            self.changesets.update(status=ChangeSet.IMPLEMENTED)

    def __notify_state(self):
        async_to_sync(get_channel_layer().group_send)('provision_status', {
            'type': 'provision_status_message',
            'text': json.dumps({
                'provision_set_pk': self.pk,
                'provision_status': self.state,
            })
        })

    def transition(self, to):
        """
        Transition into a new provision set state. Will throw a BadTransition exception if the transition request
        is not a valid transition in the current state.
        """
        from_ = self.state
        valid = self.valid_transitions[from_]
        if to not in valid:
            raise BadTransition("Bad transition request from {} to {}, valid next states: {}".format(from_, to, valid))

        self.__unsafe_transition(to)

    def __save_state(self):
        """
        Saves the state of the provision set to the database.
        Will not save other fields.
        """
        self.save(update_fields=['state'])

    def fail(self):
        """
        Move the state into FAILED.
        """
        self.__unsafe_transition(ProvisionSet.FAILED)

    def abort(self):
        """
        Move the state into ABORTED.
        """
        self.__unsafe_transition(ProvisionSet.ABORTED)

    def assert_state(self, expected):
        actual = self.state
        if actual != expected:
            raise UnexpectedState("Expected state {}, actual state {}".format(expected, actual))

    def run_odin(self):
        self.assert_state(self.NOT_STARTED)
        with ProvStateMachine(self):
            self.transition(self.PREPARE)
            r = odin_prepare(self.pk)

            if r.has_errors:
                logger.info("Odin failed with errors")
                self.fail()

            self.odin_output = r.output
            self.save(update_fields=['odin_output'])

    def run_ansible_diff(self):
        self.assert_state(self.PREPARE)
        self.__init_new_output()

        odin_diff(self.pk)

    def run_ansible_commit(self):
        self.assert_state(self.REVIEWING)
        self.transition(self.COMMIT)
        self.__init_new_output()

        odin_commit(self.pk)

    def terminate(self):
        self.abort()
        odin_delete(self.pk)

    def __init_new_output(self):
        with NamedTemporaryFile(delete=False) as file:
            self.output_log_file = realpath(file.name)
            self.save(update_fields=['output_log_file'])

    def persist_prepare_log(self):
        with open(self.output_log_file, 'r') as buffer_file:
            # Please have a look at consumers.py:OdinConsumer.finalize_buffer()
            # to understand why the last byte is ignored
            buf = buffer_file.read()[:-1]
            self.prepare_log = buf
            self.output_log_file = None
            self.save(update_fields=['output_log_file', 'prepare_log'])

    def persist_commit_log(self):
        with open(self.output_log_file, 'r') as buffer_file:
            # Please have a look at consumers.py:OdinConsumer.finalize_buffer()
            # to understand why the last byte is ignored
            buf = buffer_file.read()[:-1]
            self.commit_log = buf
            self.output_log_file = None
            self.save(update_fields=['output_log_file', 'commit_log'])

    def is_final_state(self):
        return len(self.valid_transitions.get(self.state, ())) == 0

    @classmethod
    def active_exists(cls):
        return cls.objects.filter(
            state__in=(cls.RUNNING, cls.PREPARE, cls.COMMIT, cls.REVIEWING)
        ).values_list('pk', flat=True)


class ChangedObjectManager(models.Manager):
    def get_queryset(self):
        return super(ChangedObjectManager, self).get_queryset()\
            .select_related('changed_object_type', 'user')\
            .prefetch_related('changed_object')


class ChangedField(models.Model):
    """
    A changed field refers to a field of any model that has changed. It records
    the old and new values, refers to a changeset, has a time, and a generic
    foreign key relation to the model it refers to. These are kind of clunky,
    but sadly necessary.
    """
    objects = ChangedObjectManager()

    changeset = models.ForeignKey(
        ChangeSet,
        null=True,
        on_delete=models.SET_NULL
    )
    time = models.DateTimeField(
        auto_now_add=True,
        editable=False
    )
    changed_object_type = models.ForeignKey(
        to=ContentType,
        on_delete=models.PROTECT,
        related_name='+'
    )
    changed_object_id = models.PositiveIntegerField()
    changed_object = GenericForeignKey(
        ct_field='changed_object_type',
        fk_field='changed_object_id'
    )
    field = models.CharField(
        max_length=40
    )
    old_value = models.BinaryField(null=True)
    new_value = models.BinaryField(null=True)
    user = models.ForeignKey(
        to=User,
        on_delete=models.SET_NULL,
        related_name='+',
        blank=True,
        null=True
    )

    def __str__(self):
        old = pickle.loads(self.old_value)
        new = pickle.loads(self.new_value)
        tpl = "Field {} of {} was changed from '{}' to '{}'."
        return tpl.format(self.field, self.changed_object_type, old, new)


class ChangedObject(models.Model):
    """
    A changed object is similar to a changed field, but it refers to the whole
    object. This is necessary if there was no object before (i.e. it was newly
    created).
    """
    objects = ChangedObjectManager()

    deleted = models.BooleanField(default=False)
    changeset = models.ForeignKey(
        ChangeSet,
        null=True,
        on_delete=models.SET_NULL
    )
    time = models.DateTimeField(
        auto_now_add=True,
        editable=False
    )
    changed_object_type = models.ForeignKey(
        to=ContentType,
        on_delete=models.PROTECT,
        related_name='+'
    )
    changed_object_id = models.PositiveIntegerField()
    changed_object = GenericForeignKey(
        ct_field='changed_object_type',
        fk_field='changed_object_id'
    )
    changed_object_data = models.BinaryField()
    user = models.ForeignKey(
        to=User,
        on_delete=models.SET_NULL,
        related_name='+',
        blank=True,
        null=True
    )

    def __str__(self):
        return "{} #{} was {}.".format(self.changed_object_type,
                                       self.changed_object_id,
                                       'deleted' if self.deleted else 'added')
