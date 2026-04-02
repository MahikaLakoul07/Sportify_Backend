from datetime import datetime, timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from connections.models import ConnectionRequest
from .models import (
    ChatGroup,
    ChatGroupMember,
    DirectChat,
)


def get_booking_chat_expiry(booking):
    naive_end = datetime.combine(booking.date, booking.end_time)
    aware_end = timezone.make_aware(
        naive_end,
        timezone.get_current_timezone()
    )
    return aware_end + timedelta(hours=1)


@transaction.atomic
def create_temporary_chat_for_booking(booking):
    existing_group = getattr(booking, "chat_group", None)
    if existing_group:
        return existing_group

    group = ChatGroup.objects.create(
        booking=booking,
        name=f"{booking.ground.name} - {booking.date} {booking.start_time}-{booking.end_time}",
        is_temporary=True,
        is_active=True,
        expires_at=get_booking_chat_expiry(booking),
    )

    ChatGroupMember.objects.get_or_create(
        group=group,
        user=booking.created_by,
    )

    return group


@transaction.atomic
def add_user_to_booking_chat(booking, user):
    group = getattr(booking, "chat_group", None)
    if not group:
        group = create_temporary_chat_for_booking(booking)

    group.refresh_status()

    if not group.is_active:
        return None

    ChatGroupMember.objects.get_or_create(
        group=group,
        user=user,
    )
    return group


def deactivate_booking_chat(booking):
    group = getattr(booking, "chat_group", None)
    if not group:
        return None
    if group.is_active:
        group.is_active = False
        group.save(update_fields=["is_active"])
    return group


@transaction.atomic
def get_or_create_direct_chat(user_a, user_b):
    if user_a.pk == user_b.pk:
        raise ValueError("A user cannot create a direct chat with themselves.")

    is_connected = ConnectionRequest.objects.filter(
        status=ConnectionRequest.Status.ACCEPTED
    ).filter(
        Q(sender=user_a, receiver=user_b) | Q(sender=user_b, receiver=user_a)
    ).exists()

    if not is_connected:
        raise ValueError("Users must be connected before starting a direct chat.")

    first, second = sorted([user_a.pk, user_b.pk])

    chat, created = DirectChat.objects.get_or_create(
        user1_id=first,
        user2_id=second,
        defaults={"is_active": True},
    )

    if not chat.is_active:
        chat.is_active = True
        chat.save(update_fields=["is_active"])

    return chat