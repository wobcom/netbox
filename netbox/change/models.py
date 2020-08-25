import pickle
import json
from datetime import timedelta, datetime
from topdesk import Topdesk
from requests import post, delete
from tempfile import NamedTemporaryFile
from os.path import realpath

from django.conf import settings
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
from configuration.models import RouteMap, BGPCommunity, BGPCommunityList

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
        on_delete=models.PROTECT,
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
            c = ChangeSet.objects.get(active=True, user=user)
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
    pass


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
        NOT_STARTED: (PREPARE, ABORTED),
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
    prepare_log = models.TextField(blank=True, null=True)
    state = models.CharField(
        max_length=20,
        default=NOT_STARTED,
        choices=state_labels.items()
    )

    def __init__(self, *args, **kwargs):
        super(ProvisionSet, self).__init__(*args, **kwargs)
        if self.active_exists() and not self.pk:
            print(self.active_exists())
            raise AlreadyExistsError('An unfinished provision already exists.')

    def transition(self, to):
        from_ = self.status
        valid = self.valid_transitions[from_]
        if to not in valid:
            raise BadTransition("Bad transition request from {} to {}, valid next states: {}".format(from_, to, valid))
        if self.status in (self.PREPARE, self.FINISHED, self.FAILED, self.ABORTED):
            async_to_sync(get_channel_layer().group_send)('provision_status', {
                'type': 'provision_status_message',
                'text': json.dumps({
                    'provision_set_pk': self.pk,
                    'provision_status': str(int(self.status == self.PREPARE))
                })
            })
        self.status = to

    def transition_(self, to):
        self.transition(to)
        self.save()

    def run_prepare(self):
        self.transition_(self.PREPARE)
        r = post(
            url=f"{settings.ODIN_WORKER_URL}/provision/{self.pk}",
            json={
                "odinArgs": settings.ODIN_ADDITIONAL_ARGS,
                "callbackPath": f"/change/provisions/{self.pk}/worker/{self.PREPARE}/",
            },
        )
        if r.status_code != 200:
            self.transition_(self.FAILED)
            raise ProvisionFailed(r.text)
        with NamedTemporaryFile(delete=False) as file:
            self.output_log_file = realpath(file.name)
            self.save()

    def run_commit(self):
        self.transition_(self.COMMIT)
        r = post(
            url=f"{settings.ODIN_WORKER_URL}/provision/{self.pk}/commit",
            json=f"/change/provisions/{self.pk}/worker/{self.COMMIT}/",
        )
        if r.status_code != 200:
            self.transition_(self.FAILED)
            raise ProvisionFailed(r.text)

    def finish(self):
        self.transition(self.FINISHED)
        self.changesets.update(status=ChangeSet.ACCEPTED)
        self.save()

    def terminate(self):
        self.transition(self.ABORTED)
        delete(
            url=f"{settings.ODIN_WORKER_URL}/provision/{self.pk}"
        )
        self.save()

    def persist_output_log(self, append=False):
        with open(self.output_log_file, 'r') as buffer_file:
            if self.prepare_log is None:
                self.prepare_log = buffer_file.read()
            else:
                self.prepare_log += '\n'
                self.prepare_log += buffer_file.read()
        self.output_log_file = None

    @property
    def timeout(self):
        if settings.PROVISIONING_TIMEOUT is None:
            return None
        return self.updated + timedelta(seconds=settings.PROVISIONING_TIMEOUT)

    @property
    def timed_out(self):
        if self.timeout is None:
            return False
        return timezone.now() > self.timeout

    @classmethod
    def active_exists(cls):
        return cls.objects.filter(status__in=(cls.RUNNING, cls.PREPARE, cls.COMMIT, cls.REVIEWING)).exists()


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
