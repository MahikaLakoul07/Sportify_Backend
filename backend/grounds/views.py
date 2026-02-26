from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date

from rest_framework import permissions, status, viewsets
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from bookings.models import Booking
from .models import Ground, GroundAvailability
from .serializers import (
    AvailabilityBulkUpsertSerializer,
    GroundCreateSerializer,
    GroundDetailSerializer,
    GroundListSerializer,
)
from .slot_constants import FIXED_SLOTS


class GroundViewSet(viewsets.ModelViewSet):
    queryset = Ground.objects.all().order_by("-created_at")
    parser_classes = (MultiPartParser, FormParser)

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy", "my"]:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_serializer_class(self):
        if self.action == "create":
            return GroundCreateSerializer
        if self.action == "list":
            return GroundListSerializer
        return GroundDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset()

        if self.action in ["list", "retrieve"]:
            return qs.filter(status=Ground.Status.APPROVED)

        return qs

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user, status=Ground.Status.PENDING)


class GroundAvailabilityBulkUpsertView(APIView):
    """
    POST /api/grounds/<id>/availability/bulk/
    Body:
    {
      "availability": [
        {"day_of_week": 6, "windows": [{"start_time":"07:00","end_time":"08:00"}]},
        {"day_of_week": 0, "windows": [{"start_time":"08:00","end_time":"10:00"}]}
      ]
    }
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        ground = get_object_or_404(Ground, pk=pk)

        # ✅ owner-only
        if ground.owner_id != request.user.pk:
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)

        serializer = AvailabilityBulkUpsertSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data["availability"]

        # Replace per day (delete old windows for those days)
        with transaction.atomic():
            days = [d["day_of_week"] for d in data]
            GroundAvailability.objects.filter(ground=ground, day_of_week__in=days).delete()

            to_create = []
            for d in data:
                dow = d["day_of_week"]
                for w in d["windows"]:
                    to_create.append(
                        GroundAvailability(
                            ground=ground,
                            day_of_week=dow,
                            start_time=w["start_time"],
                            end_time=w["end_time"],
                        )
                    )

            GroundAvailability.objects.bulk_create(to_create)

        return Response({"detail": "Availability saved successfully."}, status=status.HTTP_200_OK)
class GroundSlotsForDateView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        ground = get_object_or_404(Ground, pk=pk, status=Ground.Status.APPROVED)

        date_str = request.query_params.get("date")
        d = parse_date(date_str) if date_str else None
        if not d:
            return Response({"detail": "date=YYYY-MM-DD is required"}, status=400)

        dow = d.weekday()

        windows = list(GroundAvailability.objects.filter(ground=ground, day_of_week=dow))

        def within_availability(s, e):
            if not windows:
                return True
            return any(w.start_time <= s and e <= w.end_time for w in windows)

        booked = set(
            Booking.objects.filter(
                ground=ground,
                date=d,
                status__in=[Booking.Status.PENDING, Booking.Status.BOOKED],
            ).values_list("start_time", "end_time")
        )

        slots = []
        for s, e in FIXED_SLOTS:
            open_ = within_availability(s, e)
            is_booked = (s, e) in booked
            slots.append(
                {
                    "start_time": s.strftime("%H:%M"),
                    "end_time": e.strftime("%H:%M"),
                    "booked": bool(is_booked),
                    "available": bool(open_ and not is_booked),
                }
            )

        return Response({"ground_id": ground.id, "date": date_str, "slots": slots}, status=200)

    permission_classes = [permissions.AllowAny]

    # GET /api/grounds/<id>/slots/?date=YYYY-MM-DD
    def get(self, request, pk):
        ground = get_object_or_404(Ground, pk=pk, status=Ground.Status.APPROVED)

        date_str = request.query_params.get("date")
        d = parse_date(date_str) if date_str else None
        if not d:
            return Response({"detail": "date=YYYY-MM-DD is required"}, status=400)

        dow = d.weekday()

        # weekly availability windows (if none set => treat as fully open)
        windows = list(GroundAvailability.objects.filter(ground=ground, day_of_week=dow))

        def within_availability(s, e):
            if not windows:
                return True
            return any(w.start_time <= s and e <= w.end_time for w in windows)

        booked = set(
            Booking.objects.filter(
                ground=ground, date=d, status=Booking.Status.BOOKED
            ).values_list("start_time", "end_time")
        )

        slots = []
        for s, e in FIXED_SLOTS:
            open_ = within_availability(s, e)
            is_booked = (s, e) in booked
            slots.append({
                "start_time": s.strftime("%H:%M"),
                "end_time": e.strftime("%H:%M"),
                "booked": bool(is_booked),
                "available": bool(open_ and not is_booked),
            })

        return Response({"ground_id": ground.id, "date": date_str, "slots": slots})