from django.apps import AppConfig


class ChangeConfig(AppConfig):
    name = "change"

    def ready(self):
        from .signals import register_websocket_handlers
        register_websocket_handlers()
