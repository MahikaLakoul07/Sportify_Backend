# grounds/views.py
from rest_framework import viewsets, permissions
from rest_framework.parsers import MultiPartParser, FormParser

from .models import Ground
from .serializers import GroundCreateSerializer, GroundListSerializer, GroundDetailSerializer


class GroundViewSet(viewsets.ModelViewSet):
    queryset = Ground.objects.all().order_by("-created_at")
    parser_classes = (MultiPartParser, FormParser)  # needed for FormData + image uploads [web:16]

    def get_permissions(self):
        # Anyone can read approved grounds; only logged-in users can create/update their own
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

        # For public list: show only approved
        if self.action in ["list", "retrieve"]:
            return qs.filter(status=Ground.Status.APPROVED)

        # For authenticated actions: you can restrict later if needed
        return qs

    def perform_create(self, serializer):
        # Attach logged-in user as owner, force status=PENDING
        serializer.save(owner=self.request.user, status=Ground.Status.PENDING)