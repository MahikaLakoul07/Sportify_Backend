# backend/bookings/views.py

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


class BookingViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        base_qs = (
            Booking.objects
            .select_related("ground", "created_by", "chat_group")
            .order_by("-created_at")
        )

        if self.action in {"open_games", "retrieve", "join", "deactivate_chat"}:
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

        if not (is_own_booking or is_public_open_game):
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