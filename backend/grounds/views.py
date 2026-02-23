from rest_framework import generics, permissions
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Ground
from .serializers import GroundSerializer


class GroundListCreateView(generics.ListCreateAPIView):
    serializer_class = GroundSerializer
    parser_classes = [MultiPartParser, FormParser]  # ✅ IMPORTANT for image uploads

    def get_queryset(self):
        # Players see only APPROVED grounds
        return Ground.objects.filter(status="APPROVED").order_by("-created_at")

    def perform_create(self, serializer):
        # Only logged-in users can create
        # Owner set automatically
        serializer.save(owner=self.request.user, status="PENDING")


class GroundDetailView(generics.RetrieveAPIView):
    serializer_class = GroundSerializer

    def get_queryset(self):
        # Ground detail only if APPROVED (matches your requirement)
        return Ground.objects.filter(status="APPROVED")
