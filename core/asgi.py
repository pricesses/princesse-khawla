"""
ASGI config for core project.
Utilise python manage.py runserver uniquement.
"""

import os
import logging
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

django_asgi_app = get_asgi_application()

logger = logging.getLogger(__name__)

try:
    from channels.routing import ProtocolTypeRouter, URLRouter
    from channels.auth import AuthMiddlewareStack
    from django.urls import path

    try:
        from guard.routing import websocket_urlpatterns as dashboard_ws
    except ImportError:
        dashboard_ws = []
        logger.warning("⚠️ guard.routing not found")

    application = ProtocolTypeRouter({
        'http': django_asgi_app,
        'websocket': AuthMiddlewareStack(
            URLRouter(dashboard_ws)
        ),
    })
    logger.info("✅ Channels WebSocket configured")

except Exception as e:
    logger.warning(f"⚠️ Channels not available: {e}")
    application = django_asgi_app