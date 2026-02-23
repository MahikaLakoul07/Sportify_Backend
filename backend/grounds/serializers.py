from rest_framework import serializers
from .models import Ground


class GroundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ground
        fields = [
            "id",
            "owner",
            "name",
            "location",
            "price_per_hour",
            "description",
            "phone",
            "ground_size",
            "image",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "owner", "status", "created_at"]
