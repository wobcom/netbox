from django.db import models
from django.contrib.contenttypes.models import ContentType

from .constants import SLACK_MESSAGE_MODELS


class SlackChannel(models.Model):
    name = models.CharField(
        max_length=80,
    )

    messages = models.ManyToManyField(
        to='SlackMessage',
        related_name='slack_channels',
    )

    class Meta:
        verbose_name = 'Channel'

    def __str__(self):
        return self.name


class SlackMessage(models.Model):
    name = models.CharField(
        max_length=127,
    )
    object_types = models.ManyToManyField(
        to=ContentType,
        related_name='slack_messages',
        verbose_name='Object types',
        limit_choices_to={
            'model__in': [model.split('.')[1] for model in SLACK_MESSAGE_MODELS],
        },
        help_text="The object(s) to which this message applies",
    )
    on_create = models.BooleanField(
        default=False,
        help_text="Send this message when a matching object is created."
    )
    on_update = models.BooleanField(
        default=False,
        help_text="Send this message when a matching object is updated."
    )
    on_delete = models.BooleanField(
        default=False,
        help_text="Send this message when a matching object is deleted."
    )
    template = models.TextField(
        help_text="Message template in django template syntax.\n"
                  "If the template results to an empty string the message will not be sent.\n"
                  "The corresponding object is available in the template as \"object\"."
    )

    class Meta:
        verbose_name = 'Message'

    def __str__(self):
        return self.name
