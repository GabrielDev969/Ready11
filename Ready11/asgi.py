"""
ASGI config for Ready11 project.

Routes HTTP to Django and WebSocket to Channels (real-time notifications).
"""

import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Ready11.settings')

from django.core.asgi import get_asgi_application

# Initialize Django's ASGI app first so the app registry is ready before we
# import consumers (which touch models).
django_asgi_app = get_asgi_application()

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter

from notifications.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
})
