# grounds/views.py
from rest_framework import viewsets, permissions, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db import transaction

from .models import Ground, GroundAvailability
from .serializers import (
    GroundCreateSerializer,
    GroundListSerializer,
    GroundDetailSerializer,
    AvailabilityBulkUpsertSerializer,
)


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