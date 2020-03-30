from django.db.models import Q
from django.db.models.signals import post_save, post_delete
from django.template import Template, Context

from django_rq import get_queue


from .models import SlackMessage


def install_receivers():
    """
    Install signal receivers
    """

    queue = get_queue('default')

    for message in SlackMessage.objects.filter(
            Q(slack_channels__isnull=False)
    ):
            message_uid = "message_{}".format(message.pk)

            def message_base_callback(**kwargs):
                queue.enqueue(
                    'slack_integration.worker.handle_slack_message',
                    message,
                    kwargs.get('instance', None),
                )

            def message_save_callback(**kwargs):
                if kwargs.get('created', False) and message.on_create:
                    message_base_callback(**kwargs)
                elif message.on_update:
                    message_base_callback()

            for object_type in message.object_types.all():
                object_type_uid = "{}_object_{}.{}".format(message_uid, object_type.app_label, object_type.model)

                if message.on_update or message.on_create:
                    post_save.connect(
                        receiver=message_save_callback,
                        sender=object_type.model_class(),
                        weak=False,
                        dispatch_uid='{}_save'.format(object_type_uid),
                    )

                if message.on_delete:
                    post_delete.connect(
                        receiver=message_base_callback,
                        sender=object_type.model_class(),
                        weak=False,
                        dispatch_uid='{}_delete'.format(object_type_uid),
                    )




def uninstall_receivers():
    """
    Uninstall signal receivers
    """
