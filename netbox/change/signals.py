import json

from django.dispatch import Signal
from django.db.models.signals import post_save

from .models import ProvisionSet, ChangeSet
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

channel_layer = get_channel_layer()

provision_finished = Signal(providing_args=['provision_set'])


def register_websocket_handlers():
    post_save.connect(
        receiver=provision_status_handler,
        sender=ProvisionSet,
        weak=False,
    )

    post_save.connect(
        receiver=users_in_change_handler,
        sender=ChangeSet,
        weak=False,
    )


def provision_status_handler(instance, **kwargs):
    async_to_sync(channel_layer.group_send)(
        "provision_status",
        {
            "type": "provision.status",
            "provision_set_pk": instance.pk,
            "message": provision_status_message(instance),
        }
    )


def provision_status_message(instance):
    return {
        'status': {
            'id': instance.state,
            'str': instance.state_labels[instance.state],
        }
    }


def users_in_change_handler(**kwargs):
    async_to_sync(channel_layer.group_send)(
        "users_in_change",
        {
            "type": "users.list",
            "message": users_in_change_message()
        }
    )


def users_in_change_message():
    users = list()
    for change in ChangeSet.objects.filter(status=ChangeSet.DRAFT).prefetch_related('user'):
        users.append(change.user.username)
    return users
