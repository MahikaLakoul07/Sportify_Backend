from django.urls import re_path
from .consumers import GroupChatConsumer, DirectChatConsumer

websocket_urlpatterns = [
    re_path(r"ws/chat/(?P<group_id>\d+)/$", GroupChatConsumer.as_asgi()),
    re_path(r"ws/direct-chat/(?P<chat_id>\d+)/$", DirectChatConsumer.as_asgi()),
]