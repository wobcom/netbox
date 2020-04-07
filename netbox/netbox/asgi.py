import os

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "netbox.settings")
django.setup()

from channels.auth import AuthMiddlewareStack               # noqa
from channels.routing import ProtocolTypeRouter, URLRouter  # noqa

import change.urls                                          # noqa


application = ProtocolTypeRouter({
    'websocket': AuthMiddlewareStack(
        URLRouter(change.urls.websocket_urlpatterns)
    )
})
