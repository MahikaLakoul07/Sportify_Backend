from django.urls import path
from .views import (
    MyChatGroupsView,
    ChatGroupDetailView,
    ChatMessageListCreateView,
    MyDirectChatsView,
    DirectChatCreateOrGetView,
    DirectChatDetailView,
    DirectMessageListCreateView,
)

urlpatterns = [
    path("chat-groups/my/", MyChatGroupsView.as_view()),
    path("chat-groups/<int:group_id>/", ChatGroupDetailView.as_view()),
    path("chat-groups/<int:group_id>/messages/", ChatMessageListCreateView.as_view()),

    path("direct-chats/my/", MyDirectChatsView.as_view()),
    path("direct-chats/get-or-create/", DirectChatCreateOrGetView.as_view()),
    path("direct-chats/<int:chat_id>/", DirectChatDetailView.as_view()),
    path("direct-chats/<int:chat_id>/messages/", DirectMessageListCreateView.as_view()),
]