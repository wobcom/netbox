import io
import pickle
import yaml
import graphviz
from datetime import timedelta
from collections import defaultdict

from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import JSONField
from django.db import models, transaction
from django.shortcuts import redirect
from django.utils import timezone

from netbox import configuration
from dcim.models import Device, Interface
from dcim.constants import *
from ipam.models import IPADDRESS_ROLE_LOOPBACK
from ipam.constants import IPADDRESS_ROLE_ANYCAST
from virtualization.models import VirtualMachine

from change.utilities import Markdownify
from dcim.constants import *
from configuration.models import RouteMap, BGPCommunity, BGPCommunityList

DEVICE_ROLE_TOPOLOGY_WHITELIST = ['leaf', 'spine', 'superspine']
NO_CHANGE = 0
OWN_CHANGE = 1
FOREIGN_CHANGE = 2


class ChangeInformation(models.Model):
    """Meta information about a change."""
    name = models.CharField(max_length=256, verbose_name="Change Title")
    is_emergency = models.BooleanField(verbose_name="Is an emergency change")
    is_extensive = models.BooleanField(verbose_name="Is an extensive change")
    affects_customer = models.BooleanField(verbose_name="Customers are affected")
    change_implications = models.TextField()
    ignore_implications = models.TextField()
    change_type = models.SmallIntegerField(choices=[
        (1, 'Standard Change (vorabgenehmigt)')], default=1)
    category = models.SmallIntegerField(choices=[(1, 'Netzwerk')], default=1)
    subcategory = models.SmallIntegerField(choices=[
        (0, '------------'),
        (1, 'Routing/Switching'),
        (2, 'Firewall'),
        (3, 'CPE'),
        (4, 'Access Netz'),
        (5, 'Extern')
    ], default=0)

    depends_on = models.ManyToManyField(
        'ChangeSet',
        related_name='dependants',
        blank=True,
    )

    def executive_summary(self, no_markdown=True):
        md = Markdownify(no_markdown=no_markdown)
        res = io.StringIO()
        if self.is_emergency:
            res.write(md.bold('This change is an emergency change.'))
            res.write('\n\n')

        res.write(md.bold('Implications if this change is accepted:'))
        res.write('\n{}\n\n'.format(self.change_implications))
        res.write(md.bold('Implications if this change is rejected:'))
        res.write('\n{}\n\n'.format(self.ignore_implications))

        if self.affects_customer:
            res.write(md.h3('This change affects customers'))
            res.write('\nThe following customers are affected:\n')
            for change in self.affectedcustomer_set.all():
                res.write('- {}'.format(change.name))
                if change.is_business:
                    res.write(md.bold(' (Business Customer)'))
                res.write(": {}\n".format(change.products_affected))

        if self.depends_on.exists():
            res.write(md.h3('This change depends on the following changes\n'))
            for depends in self.depends_on.all():
                res.write('- {}\n'.format(depends))

        return res.getvalue()


class AffectedCustomer(models.Model):
    """Customers affected by a change"""
    information = models.ForeignKey(
        to=ChangeInformation,
        on_delete=models.CASCADE,
    )

    name = models.CharField(max_length=128, verbose_name="Customer Name")
    is_business = models.BooleanField(verbose_name="Is a business customer")
    products_affected = models.CharField(max_length=128,
                                         verbose_name="Affected Products")


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

    def __str__(self):
        return '#{}: {}'.format(self.id, self.change_information.name if self.change_information else '')


RUNNING = 1
FINISHED = 2
FAILED = 3
ABORTED = 4


class ProvisionSet(models.Model):
    user = models.ForeignKey(
        to=User,
        on_delete=models.SET_NULL,
        related_name='+',
        blank=True,
        null=True,
    )

    output_log = models.CharField(max_length=512, blank=True, null=True)
    error_log = models.CharField(max_length=512, blank=True, null=True)
    pid = models.PositiveIntegerField(blank=True, null=True)
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
