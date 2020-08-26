import json
import os
import time
from tempfile import NamedTemporaryFile
from threading import Thread

from channels.generic.websocket import WebsocketConsumer
from channels.exceptions import DenyConnection

from asgiref.sync import async_to_sync

from .models import ProvisionSet, BadTransition


EOF_LENGTH = 8


class ProvisionWorkerConsumer(WebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super(ProvisionWorkerConsumer, self).__init__(*args, **kwargs)
        self.buffer_file = None
        self.provision_set = None

    def connect(self):
        new_state = self.scope['url_route']['kwargs']['state']
        try:
            self.provision_set = ProvisionSet.objects.get(pk=self.scope['url_route']['kwargs']['pk'])
            self.provision_set.transition(new_state)
            if self.provision_set.output_log_file is None:
                self.buffer_file = NamedTemporaryFile(mode='wb', buffering=0, delete=False)
                self.provision_set.output_log_file = os.path.realpath(self.buffer_file.name)
            else:
                self.buffer_file = open(self.provision_set.output_log_file, 'ab', buffering=0)
            self.provision_set.save()
            self.accept()
        except ProvisionSet.DoesNotExist:
            raise DenyConnection('ProvisionSet does not exist.')
        except BadTransition:
            raise DenyConnection('Invalid state.')

    def receive(self, text_data=None, bytes_data=None):
        if bytes_data is not None:
            self.buffer_file.write(bytes_data)

    def disconnect(self, code):
        self.provision_set.persist_output_log()
        if code == 4201:
            if self.provision_set.state == ProvisionSet.PREPARE:
                self.provision_set.transition(ProvisionSet.REVIEWING)
            else:
                self.provision_set.finish()
        else:
            self.provision_set.transition(ProvisionSet.FAILED)
        self.provision_set.save()
        buffer_file_path = os.path.realpath(self.buffer_file.name)
        self.buffer_file.write(b'\x00' * EOF_LENGTH)
        self.buffer_file.close()
        if os.path.isfile(buffer_file_path):
            os.unlink(buffer_file_path)


class LogfileConsumer(WebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super(LogfileConsumer, self).__init__(*args, **kwargs)
        self.connected = False

    def accept(self, *args, **kwargs):
        super(LogfileConsumer, self).accept(*args, **kwargs)
        self.connected = True

    def connect(self):
        try:
            provision_set = ProvisionSet.objects.get(pk=self.scope['url_route']['kwargs']['pk'])
            self.accept()
            if provision_set.output_log_file is not None:
                Thread(
                    target=self.send_file_continuously,
                    args=(provision_set.output_log_file,)
                ).start()
            else:
                self.send(text_data='File already closed.')
        except ProvisionSet.DoesNotExist:
            raise DenyConnection('ProvisionSet does not exist.')

    def disconnect(self, code):
        self.connected = False

    def send_file_continuously(self, path):
        with open(path, 'rb') as buffer_file:
            eof_counter = 0
            while True:
                data = buffer_file.read()
                if not self.connected:
                    break
                if len(data) > 0:
                    eof_counter_old = eof_counter
                    # Count 0x00s from the back.
                    # In case there is another char as 0x00 in data chunk,
                    # subtract old counter state.
                    for i in reversed(data):
                        if i != 0x00:
                            eof_counter -= eof_counter_old
                            break
                        eof_counter += 1
                    self.send(bytes_data=data)
                    if eof_counter >= EOF_LENGTH:
                        break
                time.sleep(0.05)


class ProvisionStatusConsumer(WebsocketConsumer):

    def connect(self):
        self.accept()

        message = {
            'provisioning_set_pk': None,
            'provision_status': '0'
        }

        running_provision_set = ProvisionSet.objects.filter(status__in=(ProvisionSet.RUNNING,
                                                                        ProvisionSet.REVIEWING))

        if running_provision_set.exists():
            message = {
                'provisioning_set_pk': running_provision_set.first().pk,
                'provision_status': '1',
            }

        self.send(json.dumps(message))

        async_to_sync(self.channel_layer.group_add)("provision_status", self.channel_name)

    def disconnect(self, code):
        async_to_sync(self.channel_layer.group_discard)("provision_status", self.channel_name)

    def provision_status_message(self, event):
        self.send(event['text'])
