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
        qs = self.get_queryset().filter(player=request.user)
        ser = BookingSerializer(qs, many=True, context={"request": request})
        return Response(ser.data)

    @action(detail=False, methods=["get"], url_path="my")
    def my(self, request):
        qs = self.get_queryset().filter(player=request.user)
        ser = BookingSerializer(qs, many=True, context={"request": request})
        return Response(ser.data)

    @action(detail=False, methods=["get"], url_path="open-games", permission_classes=[permissions.AllowAny])
    def open_games(self, request):
        qs = self.get_queryset().filter(
            booking_type=Booking.BookingType.OPEN,
            status=Booking.Status.BOOKED,
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

        return Response(
            BookingSerializer(booking, context={"request": request}).data,
            status=status.HTTP_200_OK
        )