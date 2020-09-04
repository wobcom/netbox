from abc import abstractmethod
import json
import os
import time
from threading import Thread

from channels.generic.websocket import WebsocketConsumer
from channels.exceptions import DenyConnection

from asgiref.sync import async_to_sync

from extras.signals import purge_changelog
from .models import ProvisionSet, ProvStateMachine


EOF_LENGTH = 8


class OdinConsumer(WebsocketConsumer):
    @abstractmethod
    def state_running(self):
        pass

    @abstractmethod
    def state_finished(self):
        pass

    @abstractmethod
    def persist_hook(self):
        pass

    def __init__(self, *args, **kwargs):
        super(OdinConsumer, self).__init__(*args, **kwargs)
        self.buffer_file = None
        self.provision_set = None

    def ensure_objectcache_ready(self):
        # this has to happen since we need to ensure that the objectchange
        # cache is initialized
        purge_changelog.send(self)

    def connect(self):
        self.ensure_objectcache_ready()
        try:
            pset_id = self.scope['url_route']['kwargs']['pk']
            self.provision_set = ProvisionSet.objects.get(pk=pset_id)
            self.handle_connection()
        except ProvisionSet.DoesNotExist:
            raise DenyConnection('ProvisionSet does not exist.')

    def handle_connection(self):
        with ProvStateMachine(self.provision_set) as state:
            self.prepare_buffer()
            s = self.state_running()
            state.assert_state(s)
            self.accept()

    def prepare_buffer(self):
        out = self.provision_set.output_log_file
        self.buffer_file = open(out, 'ab', buffering=0)

    def receive(self, text_data=None, bytes_data=None):
        if bytes_data is not None:
            self.buffer_file.write(bytes_data)

    def disconnect(self, code):
        self.ensure_objectcache_ready()
        with ProvStateMachine(self.provision_set) as state:
            # By convention we consider 4201 a successful ansible execution.
            if code == 4201:
                state.transition(ProvisionSet.REVIEWING)
            else:
                n = self.state_finished()
                state.transition(n)
            self.finalize_buffer()

    def finalize_buffer(self):
        """
        Write NULL-byte to indicate end of file, persist it to database and delete the file.
        """
        self.buffer_file.write(b'\x00')
        self.buffer_file.close()
        self.persist_hook()

        buffer_file_path = os.path.realpath(self.buffer_file.name)
        if os.path.isfile(buffer_file_path):
            os.unlink(buffer_file_path)


class OdinPrepareConsumer(OdinConsumer):
    def state_running(self):
        return ProvisionSet.PREPARE

    def state_finished(self):
        return ProvisionSet.REVIEWING

    def persist_hook(self):
        self.provision_set.persist_prepare_log()


class OdinCommitConsumer(OdinConsumer):
    def state_running(self):
        return ProvisionSet.COMMIT

    def state_finished(self):
        return ProvisionSet.FINISHED

    def persist_hook(self):
        self.provision_set.persist_commit_log()


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
            while True:
                data = buffer_file.read()
                if not self.connected:
                    break
                if len(data) > 0:
                    # Because producer writes the file in chunks,
                    # buffer_file.read() will only produce the data present so far.
                    # The EOF is not enough to know whether the producer is done.
                    # By convention the producer will finish with
                    # a NUL byte to communicate it will not send further data.
                    # This code reads chunks until the magic NUL byte is detected.
                    if data[-1] == 0x00:
                        break
                    self.send(bytes_data=data)
                time.sleep(0.05)


class ProvisionStatusConsumer(WebsocketConsumer):

    def connect(self):
        self.accept()

        message = {
            'provisioning_set_pk': None,
            'provision_status': '0'
        }

        running_provision_set = ProvisionSet.objects.filter(state__in=(ProvisionSet.RUNNING,
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
