from rest_framework import serializers
from .models import Ground, GroundAvailability


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
        read_only_fields = ["id", "status", "created_at"]


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
    owner_id = serializers.IntegerField(read_only=True)

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


# -----------------------------
# ✅ Availability Bulk Serializers
# -----------------------------

class AvailabilityWindowSerializer(serializers.Serializer):
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()

    def validate(self, attrs):
        if attrs["end_time"] <= attrs["start_time"]:
            raise serializers.ValidationError("end_time must be after start_time.")
        return attrs


class DayAvailabilitySerializer(serializers.Serializer):
    day_of_week = serializers.IntegerField(min_value=0, max_value=6)
    windows = AvailabilityWindowSerializer(many=True)

    def validate(self, attrs):
        windows = attrs["windows"]

        # sort by start_time
        windows_sorted = sorted(windows, key=lambda w: (w["start_time"], w["end_time"]))

        # check duplicates + overlaps
        prev_end = None
        seen = set()

        for w in windows_sorted:
            key = (w["start_time"], w["end_time"])
            if key in seen:
                raise serializers.ValidationError("Duplicate time window found.")
            seen.add(key)

            if prev_end is not None and w["start_time"] < prev_end:
                raise serializers.ValidationError("Overlapping time windows are not allowed.")
            prev_end = w["end_time"]

        return attrs


class AvailabilityBulkUpsertSerializer(serializers.Serializer):
    availability = DayAvailabilitySerializer(many=True)