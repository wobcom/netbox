import pickle
from datetime import timedelta
from topdesk import Topdesk

from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils import timezone

from netbox import configuration
from dcim.models import Device, Interface
from dcim.constants import *
from virtualization.models import VirtualMachine

from dcim.constants import *
from configuration.models import RouteMap, BGPCommunity, BGPCommunityList

DEVICE_ROLE_TOPOLOGY_WHITELIST = ['leaf', 'spine', 'superspine']
NO_CHANGE = 0
OWN_CHANGE = 1
FOREIGN_CHANGE = 2


class ChangeInformation(models.Model):
    """Meta information about a change."""
    name = models.CharField(max_length=256, verbose_name="Change Title")
    topdesk_change_number = models.CharField(max_length=50, null=True)

    def executive_summary(self, no_markdown=True):
        return self.name

    def topdesk_change(self):
        if not configuration.TOPDESK_URL:
            return
        t = Topdesk(configuration.TOPDESK_URL,
                    verify=configuration.TOPDESK_SSL_VERIFICATION,
                    app_creds=(configuration.TOPDESK_USER, configuration.TOPDESK_TOKEN))
        return t.operator_change(id_=self.topdesk_change_number)

    def topdesk_url(self):
        if not configuration.TOPDESK_URL:
            return

        base_url = "{}/tas/secure/contained/newchange?action=show&unid={}"

        return base_url.format(configuration.TOPDESK_URL, self.topdesk_change()['id'])


class ChangeSetManager(models.Manager):
    def get_queryset(self):
        return super(ChangeSetManager, self).get_queryset()\
            .select_related('change_information', 'user')


# These are the states that a change set can be in
DRAFT = 1
IN_REVIEW = 2
ACCEPTED = 3
IMPLEMENTED = 4
REJECTED = 5
FAILED = 6


class ChangeSet(models.Model):
    """
    A change set always refers to a ticket, has a set of changes, and can be
    serialized to YAML.
    """
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
    provision_log = JSONField(
        blank=True,
        null=True
    )
    mr_location = models.CharField(
        max_length=256,
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
            (REJECTED, 'Rejected'),
            (FAILED, 'Failed'),
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
        try:
            c = ChangeSet.objects.get(active=True, user=user)
            return OWN_CHANGE
        except ChangeSet.DoesNotExist:
            return NO_CHANGE

    def executive_summary(self, no_markdown=False):
        return self.change_information.executive_summary(no_markdown=no_markdown)

    def in_use(self):
        threshold = timedelta(minutes=configuration.CHANGE_SESSION_TIMEOUT)
        before = timezone.now() - threshold

        return self.updated > before

    def topdesk_url(self):
        return self.change_information.topdesk_url()

    def __str__(self):
        return '#{}: {}'.format(self.id, self.change_information.name if self.change_information else '')


RUNNING = 1
FINISHED = 2
FAILED = 3
ABORTED = 4


class ProvisionSet(models.Model):
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

    output_log = models.CharField(max_length=512, blank=True, null=True)
    error_log = models.CharField(max_length=512, blank=True, null=True)
    status = models.SmallIntegerField(
        default=DRAFT,
        choices=[
            (RUNNING, "Running"),
            (FINISHED, "Finished"),
            (FAILED, "Failed"),
            (ABORTED, "Aborted"),
        ]
    )


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
