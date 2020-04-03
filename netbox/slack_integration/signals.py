from django.db.models.signals import post_save, m2m_changed, pre_delete

from django_rq import get_queue

from .models import SlackMessage


def install_message_model_receivers():
    """
    Register three receivers to the SlackMessage model,
    to keep the message receivers for slack message handling up to date.

        post_save:   To recognize changes to the model attributes.
                     In case of a new SlackMessage this signal is useless,
                     because the called 'update_message receivers' function
                     needs the ManyToMany fields available, which does not exists
                     at the time of this signal. But for updates of an existing
                     SlackMessage this receiver is needed to handle updates, if no
                     ManyToMany relation was changed,

        m2m_changed: To recognize ManyToMany changes of SlackMessage.object_types,
                     because the ManyToMany models does not exist at time of the
                     post_save signal.

        pre_delete:  To recognise SlackMessage deletions.

    In case of an update of SlackMessage.object_types and another SlackMessage
    attribute the two signals post_save and m2m_changed are received, this is
    a little bit dirty but not a real problem, because the use of dispatch_uid
    in update_message_receiver's receiver registration.
    """

    def callback(**kwargs):
        update_message_receivers(messages=(kwargs['instance'],))

    def m2m_callback(**kwargs):
        if kwargs.get('action', '') == 'post_add':
            callback(**kwargs)
        if kwargs.get('action', '') == 'pre_remove':
            update_message_receivers(messages=(kwargs['instance'],), deleted_object_types=kwargs['pk_set'])

    def delete_callback(**kwargs):
        kwargs['instance'].on_create = False
        kwargs['instance'].on_update = False
        kwargs['instance'].on_delete = False
        callback(**kwargs)

    post_save.connect(
        receiver=callback,
        sender=SlackMessage,
        weak=False,
        dispatch_uid='SlackMessageSaveReceiver',
    )

    m2m_changed.connect(
        receiver=m2m_callback,
        sender=SlackMessage.object_types.through,
        weak=False,
        dispatch_uid='SlackMessageM2mChangedReceiver',
    )

    pre_delete.connect(
        receiver=delete_callback,
        sender=SlackMessage,
        weak=False,
        dispatch_uid='SackMessageDeleteReceiver',
    )


def message_callback_creator(message, on_save=False):
    """
    Creates receiver callback for SlackMessage
    :type message: SlackMessage
    :type on_save: bool
    :param message: slack message to create callback for.
    :param on_save: is the callback for an save signal or not.
    :return:
    """

    def message_base_callback(**kwargs):
        queue = get_queue('default')
        queue.enqueue(
            'slack_integration.worker.handle_slack_message',
            message,
            kwargs.get('instance', None),
        )

    def message_save_callback(**kwargs):
        if kwargs.get('created', False) and message.on_create:
            message_base_callback(**kwargs)
        if message.on_update and not kwargs.get('created', False):
            message_base_callback(**kwargs)

    if on_save:
        return message_save_callback
    else:
        return message_base_callback


def update_message_receivers(messages=None, deleted_object_types=[]):
    """
    Install signal receivers

    installed signals dispatch_uid has the following form:

        message_<message.pk>_<object_type.app_label>_<object_type.model>_<save|delete>

    :param deleted_object_types: iterable of primary_keys from SlackMessage.object_types.through,
                                 to clean remove signal receivers.
    :type messages: SlackMessage[]
    :param messages: messages to proceed, if not given all existing messages are loaded from database.
    """

    if messages is None:
        messages = SlackMessage.objects.all()

    for message in messages:
        message_uid = "message_{}".format(message.pk)

        for object_type in message.object_types.all():
            object_type_uid = "{}_{}.{}".format(message_uid, object_type.app_label, object_type.model)

            save_uid = '{}_save'.format(object_type_uid)
            if (message.on_update or message.on_create) and object_type.pk not in deleted_object_types:
                post_save.connect(
                    receiver=message_callback_creator(message, on_save=True),
                    sender=object_type.model_class(),
                    weak=False,
                    dispatch_uid=save_uid,
                )
            else:
                post_save.disconnect(
                    sender=object_type.model_class(),
                    dispatch_uid=save_uid,
                )

            delete_uid = '{}_delete'.format(object_type_uid)
            if message.on_delete and object_type.pk not in deleted_object_types:
                pre_delete.connect(
                    receiver=message_callback_creator(message),
                    sender=object_type.model_class(),
                    weak=False,
                    dispatch_uid=delete_uid,
                )
            else:
                pre_delete.disconnect(
                    sender=object_type.model_class(),
                    dispatch_uid=delete_uid,
                )
