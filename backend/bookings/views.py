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
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Booking.objects
            .select_related("ground", "created_by")
            .filter(player=self.request.user)
            .order_by("-created_at")
        )

    def get_serializer_class(self):
        if self.action == "create":
            return BookingCreateSerializer
        return BookingSerializer

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        ser = BookingSerializer(qs, many=True, context={"request": request})
        return Response(ser.data)

    @action(detail=False, methods=["get"], url_path="my")
    def my(self, request):
        qs = self.get_queryset()
        ser = BookingSerializer(qs, many=True, context={"request": request})
        return Response(ser.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        booking = serializer.save()

        # STEP 11:
        # if public/open booking, create temporary group chat
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
        qs = (
            Booking.objects
            .select_related("ground", "created_by")
            .filter(
                booking_type=Booking.BookingType.OPEN,
                status=Booking.Status.BOOKED,
            )
            .order_by("date", "start_time")
        )

        today_only = request.query_params.get("today")
        if today_only == "1":
            qs = qs.filter(date=timezone.localdate())

        qs = [b for b in qs if b.current_players < b.required_players]

        ser = BookingSerializer(qs, many=True, context={"request": request})
        return Response(ser.data)

    @action(detail=True, methods=["post"], url_path="join")
    def join(self, request, pk=None):
        booking = self.get_object()

        serializer = JoinOpenBookingSerializer(
            data=request.data,
            context={"booking": booking, "request": request}
        )
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()

        # STEP 12:
        # add the current user into that booking's group chat
        add_user_to_booking_chat(booking, request.user)

        return Response(
            BookingSerializer(booking, context={"request": request}).data,
            status=status.HTTP_200_OK
        )