from datetime import datetime, timedelta
from django.utils import timezone

from .models import ChatGroup, ChatGroupMember


def create_temporary_chat_for_booking(booking):
    if hasattr(booking, "chat_group"):
        return booking.chat_group

    naive_end = datetime.combine(booking.date, booking.end_time)
    aware_end = timezone.make_aware(
        naive_end,
        timezone.get_current_timezone()
    )

    expires_at = aware_end + timedelta(hours=1)

    group = ChatGroup.objects.create(
        booking=booking,
        name=f"{booking.ground.name} - {booking.date} {booking.start_time}-{booking.end_time}",
        is_temporary=True,
        is_active=True,
        expires_at=expires_at,
    )

    # host / creator goes into chat first
    ChatGroupMember.objects.get_or_create(
        group=group,
        user=booking.created_by,
    )

    return group


def add_user_to_booking_chat(booking, user):
    group = getattr(booking, "chat_group", None)
    if not group:
        return None

    if not group.is_active:
        return None

    ChatGroupMember.objects.get_or_create(
        group=group,
        user=user,
    )

    return group