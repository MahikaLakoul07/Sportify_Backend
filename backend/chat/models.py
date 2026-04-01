from django.conf import settings
from django.db import models
from django.utils import timezone
from datetime import datetime, timedelta

from bookings.models import Booking

User = settings.AUTH_USER_MODEL


class ChatGroup(models.Model):
    booking = models.OneToOneField(
        Booking,
        on_delete=models.CASCADE,
        related_name="chat_group"
    )
    name = models.CharField(max_length=255)
    is_temporary = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def refresh_status(self):
        if self.is_active and timezone.now() >= self.expires_at:
            self.is_active = False
            self.save(update_fields=["is_active"])

    def __str__(self):
        return self.name


class ChatGroupMember(models.Model):
    group = models.ForeignKey(
        ChatGroup,
        on_delete=models.CASCADE,
        related_name="members"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="chat_memberships"
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("group", "user")

    def __str__(self):
        return f"{self.user} in {self.group}"


class ChatMessage(models.Model):
    group = models.ForeignKey(
        ChatGroup,
        on_delete=models.CASCADE,
        related_name="messages"
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="chat_messages"
    )
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender} -> {self.group}"


class DirectChat(models.Model):
    user1 = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="direct_chats_as_user1",
    )
    user2 = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="direct_chats_as_user2",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user1", "user2"],
                name="unique_direct_chat_pair"
            )
        ]

    def __str__(self):
        return f"DirectChat({self.user1} <-> {self.user2})"


class DirectMessage(models.Model):
    chat = models.ForeignKey(
        DirectChat,
        on_delete=models.CASCADE,
        related_name="messages"
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="direct_messages"
    )
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender} -> DirectChat({self.chat_id})"