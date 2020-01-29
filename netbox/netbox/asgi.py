from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter

import change.urls

application = ProtocolTypeRouter({
    'websocket': AuthMiddlewareStack(
        URLRouter(change.urls.websocket_urlpatterns)
    )
})
