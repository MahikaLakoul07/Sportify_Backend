from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone

from .models import Booking
from .serializers import (
    BookingCreateSerializer,
    BookingSerializer,
    JoinOpenBookingSerializer,
)

from chat.utils import (
    create_temporary_chat_for_booking,
    add_user_to_booking_chat,
)


class BookingViewSet(viewsets.ModelViewSet):
    # By default, user must be logged in to access booking endpoints
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Return only bookings belonging to the current logged-in user
        return (
            Booking.objects
            .select_related("ground", "created_by")
            .filter(player=self.request.user)
            .order_by("-created_at")
        )

    def get_serializer_class(self):
        # Use booking creation serializer only when creating a booking
        if self.action == "create":
            return BookingCreateSerializer
        return BookingSerializer

    def list(self, request, *args, **kwargs):
        # Return all bookings of the current user
        qs = self.get_queryset()
        ser = BookingSerializer(qs, many=True, context={"request": request})
        return Response(ser.data)

    @action(detail=False, methods=["get"], url_path="my")
    def my(self, request):
        # Custom endpoint to get current user's bookings
        qs = self.get_queryset()
        ser = BookingSerializer(qs, many=True, context={"request": request})
        return Response(ser.data)

    def create(self, request, *args, **kwargs):
        # Validate and create a new booking
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        booking = serializer.save()

        # If this is an open/public booking, create a temporary group chat for it
        if booking.booking_type == Booking.BookingType.OPEN:
            create_temporary_chat_for_booking(booking)

        return Response(
            BookingSerializer(booking, context={"request": request}).data,
            status=status.HTTP_201_CREATED
        )

    @action(
        detail=False,
        methods=["get"],
        url_path="open-games",
        permission_classes=[permissions.AllowAny],
    )
    def open_games(self, request):
        # Return all confirmed open bookings that still have space left
        qs = (
            Booking.objects
            .select_related("ground", "created_by")
            .filter(
                booking_type=Booking.BookingType.OPEN,
                status=Booking.Status.BOOKED,
            )
            .order_by("date", "start_time")
        )

        # Optional filter: only show today's open games
        today_only = request.query_params.get("today")
        if today_only == "1":
            qs = qs.filter(date=timezone.localdate())

        # Remove already full games
        qs = [b for b in qs if b.current_players < b.required_players]

        ser = BookingSerializer(qs, many=True, context={"request": request})
        return Response(ser.data)

    @action(detail=True, methods=["post"], url_path="join")
    def join(self, request, pk=None):
        # Get the selected booking object
        booking = self.get_object()

        # Validate whether current user can join this open booking
        serializer = JoinOpenBookingSerializer(
            data=request.data,
            context={"booking": booking, "request": request}
        )
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()

        # Add the current user to that booking's chat group after joining
        add_user_to_booking_chat(booking, request.user)

        return Response(
            BookingSerializer(booking, context={"request": request}).data,
            status=status.HTTP_200_OK
        )