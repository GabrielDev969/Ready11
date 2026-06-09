"""
ASGI config for Ready11 project.

Routes HTTP to Django and WebSocket to Channels (real-time notifications).
"""

import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Ready11.settings')

from django.conf import settings
from django.core.asgi import get_asgi_application

# Initialize Django's ASGI app first so the app registry is ready before we
# import consumers (which touch models).
django_asgi_app = get_asgi_application()

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator

from apps.notifications.routing import websocket_urlpatterns

# AllowedHostsOriginValidator rejects WebSocket handshakes whose Origin isn't in
# ALLOWED_HOSTS — prevents Cross-Site WebSocket Hijacking (a malicious page opening
# a socket with the victim's session cookie).
application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AllowedHostsOriginValidator(
        AuthMiddlewareStack(URLRouter(websocket_urlpatterns))
    ),
})

# Wrap with Sentry ASGI middleware so WebSocket errors are captured too.
# Only activates when SENTRY_DSN is configured.
if getattr(settings, 'SENTRY_DSN', ''):
    from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
    application = SentryAsgiMiddleware(application)
