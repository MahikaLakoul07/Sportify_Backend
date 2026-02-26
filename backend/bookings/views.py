# bookings/views.py
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Booking
from .serializers import BookingCreateSerializer, BookingSerializer


class BookingViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Booking.objects.filter(player=self.request.user).order_by("-created_at")

    def get_serializer_class(self):
        if self.action == "create":
            return BookingCreateSerializer
        return BookingSerializer

    @action(detail=False, methods=["get"], url_path="my")
    def my(self, request):
        ser = BookingSerializer(self.get_queryset(), many=True)
        return Response(ser.data)
