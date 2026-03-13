from django.urls import path
from .views import (
    MyChatGroupsView,
    BookingChatGroupView,
    ChatGroupDetailView,
    ChatMessageListCreateView,
)

urlpatterns = [
    path("chat-groups/my/", MyChatGroupsView.as_view()),
    path("bookings/<int:booking_id>/chat-group/", BookingChatGroupView.as_view()),
    path("chat-groups/<int:group_id>/", ChatGroupDetailView.as_view()),
    path("chat-groups/<int:group_id>/messages/", ChatMessageListCreateView.as_view()),
]