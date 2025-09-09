# chatbot_app/routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/progress/$', consumers.ChatProgressConsumer.as_asgi()),
]
