from rest_framework import serializers
from .models import Ground


class GroundCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ground
        fields = [
            "id",
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
        read_only_fields = ["id", "status", "created_at"]  # status forced to PENDING


class GroundListSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Ground
        fields = [
            "id",
            "name",
            "location",
            "price_per_hour",
            "ground_size",
            "image_url",
            "status",
            "created_at",
        ]

    def get_image_url(self, obj):
        request = self.context.get("request")
        if not obj.image:
            return None
        url = obj.image.url
        return request.build_absolute_uri(url) if request else url


class GroundDetailSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    owner_id = serializers.IntegerField(source="owner_id", read_only=True)

    class Meta:
        model = Ground
        fields = [
            "id",
            "owner_id",
            "name",
            "location",
            "price_per_hour",
            "description",
            "phone",
            "ground_size",
            "image_url",
            "status",
            "created_at",
        ]

    def get_image_url(self, obj):
        request = self.context.get("request")
        if not obj.image:
            return None
        url = obj.image.url
        return request.build_absolute_uri(url) if request else url