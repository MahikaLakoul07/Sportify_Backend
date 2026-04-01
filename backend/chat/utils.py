from datetime import datetime, timedelta

from django.db import transaction
from django.utils import timezone

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
    print("\n========== CREATE TEMP CHAT START ==========")
    print("booking.id:", booking.id)
    print("booking.booking_type:", booking.booking_type)
    print("booking.created_by_id:", booking.created_by_id)

    existing_group = getattr(booking, "chat_group", None)
    if existing_group:
        print("Chat group already exists ->", existing_group.id)
        print("========== CREATE TEMP CHAT END ==========\n")
        return existing_group

    group = ChatGroup.objects.create(
        booking=booking,
        name=f"{booking.ground.name} - {booking.date} {booking.start_time}-{booking.end_time}",
        is_temporary=True,
        is_active=True,
        expires_at=get_booking_chat_expiry(booking),
    )
    print("ChatGroup created ->", group.id)

    member, created = ChatGroupMember.objects.get_or_create(
        group=group,
        user=booking.created_by,
    )
    print("ChatGroupMember result -> member_id:", member.id, "created:", created)

    print("========== CREATE TEMP CHAT END ==========\n")
    return group


@transaction.atomic
def add_user_to_booking_chat(booking, user):
    print("\n========== ADD USER TO BOOKING CHAT START ==========")
    print("booking.id:", booking.id)
    print("user.id:", user.pk)

    group = getattr(booking, "chat_group", None)
    if not group:
        print("No chat group found for booking -> creating one now")
        group = create_temporary_chat_for_booking(booking)

    group.refresh_status()
    print("group.id:", group.id)
    print("group.is_active:", group.is_active)

    if not group.is_active:
        print("Group inactive -> returning None")
        print("========== ADD USER TO BOOKING CHAT END ==========\n")
        return None

    member, created = ChatGroupMember.objects.get_or_create(
        group=group,
        user=user,
    )
    print("Member add/get result -> member_id:", member.id, "created:", created)

    print("========== ADD USER TO BOOKING CHAT END ==========\n")
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