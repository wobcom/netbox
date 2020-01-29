from channels.generic.websocket import WebsocketConsumer


class LogfileConsumer(WebsocketConsumer):

    def connect(self):
        self.accept()

    def disconnect(self, code):
        pass
