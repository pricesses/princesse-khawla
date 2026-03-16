"""
ASGI config for core project - avec support WebSocket pour le dashboard + GraphQL Subscriptions.
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.layers import get_channel_layer
from django.urls import path
import logging

logger = logging.getLogger(__name__)

try:
    from guard.routing import websocket_urlpatterns as dashboard_ws
except ImportError:
    dashboard_ws = []
    logger.warning("⚠️ guard.routing not found — dashboard WebSocket disabled")

try:
    from strawberry.channels import GraphqlWsConsumer
    from api.schema import schema

    graphql_ws_patterns = [
        path("graphql/", GraphqlWsConsumer.as_asgi(schema=schema)),
    ]
    logger.info("✅ GraphQL WebSocket consumer loaded")
except Exception as e:
    graphql_ws_patterns = []
    logger.warning(f"⚠️ GraphQL WebSocket not loaded: {e}")

# Merge des deux routings WebSocket
all_ws_patterns = dashboard_ws + graphql_ws_patterns

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AuthMiddlewareStack(
        URLRouter(all_ws_patterns)
    ),
})

try:
    channel_layer = get_channel_layer()
    logger.info("✅ Channels layer initialized successfully")
except Exception as e:
    logger.warning(f"⚠️ Channels layer warning: {e}")

logger.info("🚀 ASGI application started")
logger.info("🌐 Server running at: http://127.0.0.1:8000")
logger.info("🔌 GraphQL endpoint: http://127.0.0.1:8000/graphql/")
logger.info("📡 GraphQL WebSocket: ws://127.0.0.1:8000/graphql/")