# bookings/serializers.py
from rest_framework import serializers
from django.db import IntegrityError, transaction
from django.utils.dateparse import parse_date

from .models import Booking
from grounds.models import Ground
from grounds.slot_constants import FIXED_SLOTS


def is_fixed_slot(start_time, end_time):
    return any(s == start_time and e == end_time for (s, e) in FIXED_SLOTS)


class BookingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = ["ground", "date", "start_time", "end_time"]

    def validate(self, attrs):
        ground = attrs["ground"]
        if ground.status != Ground.Status.APPROVED:
            raise serializers.ValidationError("Ground is not approved.")

        if not is_fixed_slot(attrs["start_time"], attrs["end_time"]):
            raise serializers.ValidationError("Invalid slot (must match system fixed timings).")

        return attrs

    def create(self, validated_data):
        request = self.context["request"]

        # Atomic create so two players can't book same slot at same time. [web:73]
        with transaction.atomic():
            try:
                return Booking.objects.create(
                    player=request.user,
                    created_by=request.user,
                    source=Booking.Source.ONLINE,
                    status=Booking.Status.BOOKED,
                    **validated_data,
                )
            except IntegrityError:
                raise serializers.ValidationError("This slot is already booked.")


class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = [
            "id",
            "ground",
            "date",
            "start_time",
            "end_time",
            "status",
            "source",
            "created_at",
        ]
