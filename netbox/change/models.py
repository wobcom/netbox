import yaml
from datetime import timedelta

from django.contrib.auth.models import User
from django.contrib.postgres import fields
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.shortcuts import redirect
from django.utils import timezone

from netbox import configuration

from change.utilities import Markdownify


class ChangeInformation(models.Model):
    """Meta information about a change."""
    is_emergency = models.BooleanField(verbose_name="Is an emergency change")
    affects_customer = models.BooleanField(verbose_name="Customers are affected")
    change_implications = models.TextField()
    ignore_implications = models.TextField()

    # TODO: should this be a StringIO object instead?
    def executive_summary(self, no_markdown=True):
        md = Markdownify(no_markdown=no_markdown)
        res = ''
        if self.is_emergency:
            res += md.bold('This change is an emergency change.')
            res += '\n\n'

        res += md.h3('Implications if this change is accepted:')
        res += '\n{}\n\n'.format(self.change_implications)
        res += md.h3('Implications if this change is rejected:')
        res += '\n{}\n\n'.format(self.ignore_implications)

        if self.affects_customer:
            res += md.h3('This change affects customers')
            res += '\nThe following customers are affected:\n'
            for change in self.affectedcustomer_set.all():
                res += '- {}'.format(change.name)
                if change.is_business:
                    res += md.bold(' (Business Customer)')
                res += ": {}\n".format(change.products_affected)
        return res


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


# These are the states that a change set can be in
DRAFT = 1
IN_REVIEW = 2
ACCEPTED = 3
IMPLEMENTED = 4
REJECTED = 5


class ChangeSet(models.Model):
    """
    A change set always refers to a ticket, has a set of changes, and can be
    serialized to YAML.
    """
    ticket_id = models.UUIDField(null=True)
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

    user = models.ForeignKey(
        to=User,
        on_delete=models.SET_NULL,
        related_name='+',
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
        )
    )

    def to_yaml(self):
        """
        This function serializes the changeset to yaml. It will serialize all
        changed fields and object and gather some metadata to dump.
        """
        changes = []
        # we go through all our changed fields to append them to the serialized
        # list
        for change in self.changedfield_set.all():
            changed_object = {}

            for field in change.changed_object._meta.fields:
                # we do not go deeply into the object relations. if we find a
                # foreign key, we ignore it
                if field.__class__ == models.ForeignKey:
                    continue

                fname = field.name
                changed_object[fname] = getattr(change.changed_object, fname)

            # we add a dict containing the field name, new and old values,
            # type of the changed object, set "updated" as the action, and
            # record what the object looks like
            changes.append({
                "field": change.field,
                "old_value": change.old_value,
                "new_value": change.new_value,
                "type": str(change.changed_object_type),
                "changed_object": changed_object,
                "action": "updated",
            })

        # we go through all our changed objects to append them to the serialized
        # list; it's mostly the same as above.
        for change in self.changedobject_set.all():
            # less info, because we do not need to record the previous value;
            # everything has changed!
            changes.append({
                "type": str(change.changed_object_type),
                "changed_object": change.changed_object_data,
                "action": "added",
            })

        return yaml.dump(changes, explicit_start=True, default_flow_style=False)

    def executive_summary(self, no_markdown=False):
        return self.change_information.executive_summary(no_markdown=no_markdown)

    def in_use(self):
        # TODO: change session duration. where should this be saved?
        # TODO: this is very costly
        threshold = timedelta(minutes=configuration.CHANGE_SESSION_TIMEOUT)
        before = timezone.now() - threshold

        return bool(self.started > before or
                    self.changedobject_set.filter(time__gte=before).count() or
                    self.changedfield_set.filter(time__gte=before).count())


class ChangedField(models.Model):
    """
    A changed field refers to a field of any model that has changed. It records
    the old and new values, refers to a changeset, has a time, and a generic
    foreign key relation to the model it refers to. These are kind of clunky,
    but sadly necessary.

    It can be reverted by calling revert(), which will check whether the values
    are as we expect them (otherwise something terrible happened), and reverts
    it to the old value.
    """
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
    old_value = models.CharField(max_length=150, null=True)
    new_value = models.CharField(max_length=150, null=True)
    user = models.ForeignKey(
        to=User,
        on_delete=models.SET_NULL,
        related_name='+',
        blank=True,
        null=True
    )

    def __str__(self):
        tpl = "Field {} of {} was changed from '{}' to '{}'."
        return tpl.format(self.field, self.changed_object_type, self.old_value,
                          self.new_value)

    def revert(self):
        # TODO: what happens otherwise?
        if getattr(self.changed_object, self.field) == self.new_value:
            setattr(self.changed_object, self.field, self.old_value)
            self.changed_object.save()


class ChangedObject(models.Model):
    """
    A changed object is similar to a changed field, but it refers to the whole
    object. This is necessary if there was no object before (i.e. it was newly
    created).

    It can be reverted by calling revert(), which will simply delete the object.
    """
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
    changed_object_data = fields.JSONField()
    user = models.ForeignKey(
        to=User,
        on_delete=models.SET_NULL,
        related_name='+',
        blank=True,
        null=True
    )

    def __str__(self):
        return "{} #{} was added.".format(self.changed_object_type,
                                          self.changed_object_id)

    def revert(self):
        self.changed_object.delete()
