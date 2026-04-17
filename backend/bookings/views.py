from datetime import datetime, timedelta

from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Booking
from .serializers import (
    BookingCreateSerializer,
    BookingSerializer,
    JoinOpenBookingSerializer,
    OwnerDirectBookingSerializer,
)
from chat.utils import (
    add_user_to_booking_chat,
    create_temporary_chat_for_booking,
    deactivate_booking_chat,
)
from connections.models import ConnectionNotification
from connections.utils import create_notification


class BookingViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        base_qs = (
            Booking.objects
            .select_related("ground", "created_by", "chat_group", "ground__owner", "player")
            .order_by("-created_at")
        )

        if self.action in {
            "open_games",
            "retrieve",
            "join",
            "deactivate_chat",
            "owner_bookings",
            "owner_ground_bookings",
        }:
            return base_qs

        return base_qs.filter(player=self.request.user)

    def get_permissions(self):
        if self.action == "open_games":
            return [permissions.AllowAny()]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action == "create":
            return BookingCreateSerializer
        if self.action == "owner_direct_booking":
            return OwnerDirectBookingSerializer
        return BookingSerializer

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        serializer = BookingSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="my")
    def my(self, request):
        qs = self.get_queryset()
        serializer = BookingSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="owner-bookings")
    def owner_bookings(self, request):
        user_role = getattr(request.user, "role", None) or getattr(request.user, "user_type", None)

        if str(user_role).upper() != "OWNER":
            return Response(
                {"detail": "Only owners can view owner bookings."},
                status=status.HTTP_403_FORBIDDEN,
            )

        bookings = (
            Booking.objects
            .select_related("ground", "player", "created_by", "ground__owner")
            .filter(ground__owner=request.user)
            .order_by("-date", "-start_time", "-created_at")
        )

        serializer = BookingSerializer(bookings, many=True, context={"request": request})
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        booking = self.get_object()

        is_own_booking = (
            booking.player_id == request.user.pk
            or booking.created_by_id == request.user.pk
        )
        is_public_open_game = (
            booking.booking_type == Booking.BookingType.OPEN
            and booking.status == Booking.Status.BOOKED
        )
        is_ground_owner = getattr(booking.ground, "owner_id", None) == request.user.pk

        if not (is_own_booking or is_public_open_game or is_ground_owner):
            return Response(
                {"detail": "Not allowed."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = BookingSerializer(booking, context={"request": request})
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()

        if str(booking.booking_type).upper() == "OPEN":
            create_temporary_chat_for_booking(booking)
            booking.refresh_from_db()

        owner = getattr(booking.ground, "owner", None)
        if owner and owner.pk != request.user.pk:
            create_notification(
                user=owner,
                actor=request.user,
                notification_type=ConnectionNotification.Type.BOOKING_REQUEST,
                message=(
                    f"{request.user.username} booked {booking.ground.name} on "
                    f"{booking.date} from "
                    f"{booking.start_time.strftime('%H:%M')} to "
                    f"{booking.end_time.strftime('%H:%M')}."
                ),
            )

        return Response(
            BookingSerializer(booking, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=False,
        methods=["get"],
        url_path="open-games",
        permission_classes=[permissions.AllowAny],
    )
    def open_games(self, request):
        qs = (
            Booking.objects
            .select_related("ground", "created_by", "chat_group")
            .filter(
                booking_type=Booking.BookingType.OPEN,
                status=Booking.Status.BOOKED,
            )
            .order_by("date", "start_time")
        )

        today_only = request.query_params.get("today")
        if today_only == "1":
            qs = qs.filter(date=timezone.localdate())

        qs = [booking for booking in qs if booking.current_players < booking.required_players]

        serializer = BookingSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="join")
    def join(self, request, pk=None):
        booking = self.get_object()

        serializer = JoinOpenBookingSerializer(
            data={},
            context={"booking": booking, "request": request},
        )
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()

        group = add_user_to_booking_chat(booking, request.user)
        booking.refresh_from_db()

        data = BookingSerializer(booking, context={"request": request}).data
        data["group_chat_id"] = getattr(group, "id", None)

        return Response(data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel_booking(self, request, pk=None):
        booking = self.get_object()

        if booking.player_id != request.user.pk and booking.created_by_id != request.user.pk:
            return Response(
                {"detail": "You can only cancel your own booking."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if booking.status == Booking.Status.CANCELLED:
            return Response(
                {"detail": "Booking is already cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if booking.status not in {Booking.Status.PENDING, Booking.Status.BOOKED}:
            return Response(
                {"detail": "Only active bookings can be cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        booking_start = timezone.make_aware(
            datetime.combine(booking.date, booking.start_time),
            timezone.get_current_timezone(),
        )

        if booking_start <= timezone.now():
            return Response(
                {"detail": "Past or ongoing bookings cannot be cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if booking_start - timezone.now() <= timedelta(hours=3):
            return Response(
                {"detail": "Booking cannot be cancelled within 3 hours of the game start time."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        booking.status = Booking.Status.CANCELLED
        booking.save(update_fields=["status"])

        if booking.booking_type == Booking.BookingType.OPEN and booking.chat_group_id:
            deactivate_booking_chat(booking)

        owner = getattr(booking.ground, "owner", None)
        if owner and owner.pk != request.user.pk:
            create_notification(
                user=owner,
                actor=request.user,
                notification_type=ConnectionNotification.Type.BOOKING_CANCELLED,
                message=(
                    f"{request.user.username} cancelled the booking for "
                    f"{booking.ground.name} on {booking.date} "
                    f"from {booking.start_time.strftime('%H:%M')} to {booking.end_time.strftime('%H:%M')}."
                ),
            )

        return Response(
            {
                "detail": "Booking cancelled successfully.",
                "booking_id": booking.id,
                "status": booking.status,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="deactivate-chat")
    def deactivate_chat(self, request, pk=None):
        booking = self.get_object()

        if booking.created_by_id != request.user.pk:
            return Response(
                {"detail": "Only the booking creator can deactivate this chat."},
                status=status.HTTP_403_FORBIDDEN,
            )

        deactivate_booking_chat(booking)
        return Response({"detail": "Chat deactivated."}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="owner-direct-booking")
    def owner_direct_booking(self, request):
        user_role = getattr(request.user, "role", None) or getattr(request.user, "user_type", None)

        if str(user_role).upper() != "OWNER":
            return Response(
                {"detail": "Only owners can create direct bookings."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = OwnerDirectBookingSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()

        return Response(
            BookingSerializer(booking, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"], url_path=r"owner/grounds/(?P<ground_id>\d+)/bookings")
    def owner_ground_bookings(self, request, ground_id=None):
        user_role = getattr(request.user, "role", None) or getattr(request.user, "user_type", None)

        if str(user_role).upper() != "OWNER":
            return Response(
                {"detail": "Only owners can view ground bookings."},
                status=status.HTTP_403_FORBIDDEN,
            )

        bookings = (
            Booking.objects
            .select_related("ground", "player", "created_by")
            .filter(
                ground_id=ground_id,
                ground__owner=request.user,
            )
            .order_by("-date", "-start_time", "-created_at")
        )

        serializer = BookingSerializer(bookings, many=True, context={"request": request})
        return Response(serializer.data)