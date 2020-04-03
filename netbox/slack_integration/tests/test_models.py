from django.test import TestCase
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save, pre_delete

from slack_integration.models import SlackMessage


class SlackMessageTestCase(TestCase):

    def build_dispatch_uid(self, message, object_type, signal):
        if signal not in ('save', 'delete'):
            raise ValueError("signal must be 'save' or 'delete'")
        return "message_{}_{}.{}_{}".format(
            message.pk,
            object_type.app_label,
            object_type.model,
            signal
        )

    def is_in_signal_receivers(self, signal, dispatch_uid):
        for receiver in signal.receivers:
            if receiver[0][0] == dispatch_uid:
                return True
        return False

    def assertSignals(self, message, object_type, save=False, delete=False):
        save_installed = self.is_in_signal_receivers(
            signal=post_save,
            dispatch_uid=self.build_dispatch_uid(
                message=message,
                object_type=object_type,
                signal='save'
            ),
        )
        delete_installed = self.is_in_signal_receivers(
            signal=pre_delete,
            dispatch_uid=self.build_dispatch_uid(
                message=message,
                object_type=object_type,
                signal='delete'
            ),
        )

        self.assertEqual(save, save_installed, "Wrong state of the post_save receiver installation.")
        self.assertEqual(delete, delete_installed, "Wrong state of the pre_Delete receiver installation.")

    def setUp(self):
        self.device_content_type = ContentType.objects.get(app_label='dcim', model='device')
        self.interface_content_type = ContentType.objects.get(app_label='dcim', model='interface')

    def test__message(self):

        # on_create

        message = SlackMessage(name='Test Message', on_create=True, template='{{ object }} created')
        message.save()
        message.object_types.add(self.device_content_type)

        self.assertSignals(
            message=message,
            object_type=self.device_content_type,
            save=True,
            delete=False,
        )

        # on_update

        message.on_create = False
        message.on_update = True
        message.save()

        self.assertSignals(
            message=message,
            object_type=self.device_content_type,
            save=True,
            delete=False,
        )

        # on_delete

        message.on_update = False
        message.on_delete = True
        message.save()

        self.assertSignals(
            message=message,
            object_type=self.device_content_type,
            save=False,
            delete=True,
        )

        # on_create, on_update

        message.on_create = True
        message.on_update = True
        message.on_delete = False
        message.save()

        self.assertSignals(
            message=message,
            object_type=self.device_content_type,
            save=True,
            delete=False,
        )

        # on_update, on_delete

        message.on_create = False
        message.on_delete = True
        message.save()

        self.assertSignals(
            message=message,
            object_type=self.device_content_type,
            save=True,
            delete=True
        )

        # on_create, on_delete

        message.on_create = True
        message.on_update = False
        message.save()

        self.assertSignals(
            message=message,
            object_type=self.device_content_type,
            save=True,
            delete=True,
        )

        # on_create, on_update, on_delete

        message.on_update = True
        message.save()

        self.assertSignals(
            message=message,
            object_type=self.device_content_type,
            save=True,
            delete=True,
        )

        # remove object_type

        message.object_types.remove(self.device_content_type)

        self.assertSignals(
            message=message,
            object_type=self.device_content_type,
            save=False,
            delete=False,
        )

        message.object_types.add(self.device_content_type)

        # change object_type and other settings

        message.on_delete = False
        message.save()
        message.object_types.add(self.interface_content_type)

        self.assertSignals(
            message=message,
            object_type=self.interface_content_type,
            save=True,
            delete=False,
        )
        self.assertSignals(
            message=message,
            object_type=self.device_content_type,
            save=True,
            delete=False,
        )
