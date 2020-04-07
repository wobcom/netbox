import os

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "netbox.settings")
django.setup()

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter

import change.urls


application = ProtocolTypeRouter({
    'websocket': AuthMiddlewareStack(
        URLRouter(change.urls.websocket_urlpatterns)
    )
})
