import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter

import change.urls

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "netbox.settings")
application = ProtocolTypeRouter({
    'websocket': AuthMiddlewareStack(
        URLRouter(change.urls.websocket_urlpatterns)
    )
})
