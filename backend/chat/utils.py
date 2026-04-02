from datetime import datetime, timedelta

from django.db import transaction
from django.utils import timezone

from .models import ChatGroup, ChatGroupMember, DirectChat


def get_booking_chat_expiry(booking):
    """
    Temporary group chat stays active until 1 hour after the booking end time.
    """
    naive_end = datetime.combine(booking.date, booking.end_time)
    aware_end = timezone.make_aware(
        naive_end,
        timezone.get_current_timezone()
    )
    return aware_end + timedelta(hours=1)


@transaction.atomic
def create_temporary_chat_for_booking(booking):
    """
    Create one temporary chat group for an OPEN booking and add the creator as a member.
    If one already exists, return the existing group.
    """
    print("\n========== CREATE TEMP CHAT START ==========")
    print("booking.id:", booking.id)
    print("booking.booking_type:", booking.booking_type)
    print("booking.created_by_id:", booking.created_by_id)

    existing_group = getattr(booking, "chat_group", None)
    if existing_group:
        print("Chat group already exists ->", existing_group.id)

        # Safety: ensure creator is a member too
        member, created = ChatGroupMember.objects.get_or_create(
            group=existing_group,
            user=booking.created_by,
            defaults={"joined_at": timezone.now()} if hasattr(ChatGroupMember, "joined_at") else {},
        )
        print("Ensured creator membership -> member_id:", member.id, "created:", created)

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

    creator_defaults = {}
    if hasattr(ChatGroupMember, "joined_at"):
        creator_defaults["joined_at"] = timezone.now()

    member, created = ChatGroupMember.objects.get_or_create(
        group=group,
        user=booking.created_by,
        defaults=creator_defaults,
    )
    print("ChatGroupMember result -> member_id:", member.id, "created:", created)

    print("========== CREATE TEMP CHAT END ==========\n")
    return group


@transaction.atomic
def add_user_to_booking_chat(booking, user):
    """
    Add a player to the booking's temporary group chat.
    If the group does not exist yet, create it first.
    If the member already exists, keep it active and return the group.
    """
    print("\n========== ADD USER TO BOOKING CHAT START ==========")
    print("booking.id:", booking.id)
    print("user.id:", user.pk)

    group = getattr(booking, "chat_group", None)
    if not group:
        print("No chat group found for booking -> creating one now")
        group = create_temporary_chat_for_booking(booking)

    if not group:
        print("Failed to get/create group")
        print("========== ADD USER TO BOOKING CHAT END ==========\n")
        return None

    # Refresh status safely
    if hasattr(group, "refresh_status"):
        group.refresh_status()
        # refresh from db in case refresh_status changes/saves fields
        group.refresh_from_db(fields=["is_active"])

    print("group.id:", group.id)
    print("group.is_active:", group.is_active)

    if not group.is_active:
        print("Group inactive -> returning None")
        print("========== ADD USER TO BOOKING CHAT END ==========\n")
        return None

    member_defaults = {}
    if hasattr(ChatGroupMember, "joined_at"):
        member_defaults["joined_at"] = timezone.now()

    member, created = ChatGroupMember.objects.get_or_create(
        group=group,
        user=user,
        defaults=member_defaults,
    )

    # If membership already exists and your model has an active flag, reactivate it
    if not created:
        updated_fields = []

        if hasattr(member, "is_active") and member.is_active is False:
            member.is_active = True
            updated_fields.append("is_active")

        if hasattr(member, "left_at") and getattr(member, "left_at", None) is not None:
            member.left_at = None
            updated_fields.append("left_at")

        if updated_fields:
            member.save(update_fields=updated_fields)

    print("Member add/get result -> member_id:", member.id, "created:", created)
    print("========== ADD USER TO BOOKING CHAT END ==========\n")
    return group


@transaction.atomic
def deactivate_booking_chat(booking):
    """
    Mark temporary booking chat inactive.
    """
    group = getattr(booking, "chat_group", None)
    if not group:
        return None

    if group.is_active:
        group.is_active = False
        group.save(update_fields=["is_active"])

    return group


@transaction.atomic
def get_or_create_direct_chat(user_a, user_b):
    """
    Return one unique direct chat between two users.
    """
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