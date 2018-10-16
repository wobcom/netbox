import yaml

from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

DRAFT = 1
IN_REVIEW = 2
ACCEPTED = 3
IMPLEMENTED = 4


class ChangeSet(models.Model):
    ticket_id = models.PositiveIntegerField(null=True)

    status = models.SmallIntegerField(
        default=DRAFT,
        choices=(
            (DRAFT, 'Draft'),
            (IN_REVIEW, 'Under Review'),
            (ACCEPTED, 'Accepted'),
            (IMPLEMENTED, 'Implemented'),
        )
    )

    def to_yaml(self):
        changes = []
        for change in self.changedfield_set.all():
            changed_object = {}

            for field in change.changed_object._meta.fields:
                if field.__class__ == models.ForeignKey:
                    continue

                fname = field.name
                changed_object[fname] = getattr(change.changed_object, fname)


            changes.append({
                "field": change.field,
                "old_value": change.old_value,
                "new_value": change.new_value,
                "type": str(change.changed_object_type),
                "changed_object": changed_object
            })

        return yaml.dump(changes,explicit_start=True, default_flow_style=False)


class ChangedField(models.Model):
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
        return "Field {} of {} was changed from '{}' to '{}'".format(self.field,
                    self.changed_object_type, self.old_value, self.new_value)

    def revert(self):
        setattr(self.changed_object, self.field, self.old_value)
        self.changed_object.save()
