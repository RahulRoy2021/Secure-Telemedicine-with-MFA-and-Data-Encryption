"""
ASGI config for backend project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

# import os
# import django
# from django.core.asgi import get_asgi_application
# from channels.routing import ProtocolTypeRouter, URLRouter
# from channels.auth import AuthMiddlewareStack
# from chat.routing import websocket_urlpatterns  # Import WebSocket routes

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

# django.setup()

# application = ProtocolTypeRouter({
#     "http": get_asgi_application(),  # Handle HTTP requests
#     "websocket": AuthMiddlewareStack(
#         URLRouter(websocket_urlpatterns)
#     ),
# })
import os
import django  # ✅ Import Django first before anything else

# ✅ Ensure Django settings are loaded
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()  # ✅ Setup Django before any imports

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from chat.routing import websocket_urlpatterns  # ✅ Import AFTER django.setup()
from channels.auth import AuthMiddlewareStack
import chat.routing
# ✅ Configure ASGI Application
application = ProtocolTypeRouter({
    "http": get_asgi_application(),  # Handles HTTP requests
    "websocket": AuthMiddlewareStack(
        URLRouter(chat.routing.websocket_urlpatterns)  # ✅ Ensure WebSockets routing works
    ),
})

