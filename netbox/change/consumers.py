import time
import json

from threading import Thread

from channels.generic.websocket import WebsocketConsumer
from channels.exceptions import DenyConnection

from asgiref.sync import async_to_sync

from .models import ProvisionSet
from.globals import active_provisioning


class LogfileConsumer(WebsocketConsumer):

    def __init__(self, *args, **kwargs):
        super(LogfileConsumer, self).__init__(*args, **kwargs)

        self.provision_set = None
        self.connected = False

    def connect(self):
        self.accept()

        try:
            self.provision_set = ProvisionSet.objects.get(pk=self.scope['url_route']['kwargs']['pk'])
        except ProvisionSet.DoesNotExist:
            self.send('Not found')
            raise DenyConnection('Provision set not found')

        self.connected = True

        if self.provision_set.output_log_file is not None:
            Thread(target=self.send_file, args=(self.provision_set.output_log_file,)).start()
        else:
            self.send(json.dumps({'scope': 'default', 'line': self.provision_set.output_log}))

    def disconnect(self, code):
        self.connected = False

    def send_file(self, path, scope=None):
        file = open(path, 'r')

        for line in self.read_file_continuously(file):
            self.send(json.dumps({'scope': scope if scope else 'default', 'line': line}))

    def read_file_continuously(self, file):
        while self.connected:
            line = file.readline()
            if not line:
                time.sleep(1)
                continue
            yield line


class ProvisionStatusConsumer(WebsocketConsumer):

    def connect(self):
        self.accept()

        self.send(active_provisioning.locked())

        async_to_sync(self.channel_layer.group_add)("provision_status", self.channel_name)

    def disconnect(self, code):
        async_to_sync(self.channel_layer.group_discard)("provision_status", self.channel_name)
