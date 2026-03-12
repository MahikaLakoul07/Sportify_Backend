from rest_framework import serializers
from django.db import IntegrityError, transaction
from django.db.models import F

from .models import Booking
from grounds.models import Ground
from grounds.slot_constants import FIXED_SLOTS


def is_fixed_slot(start_time, end_time):
    return any(s == start_time and e == end_time for (s, e) in FIXED_SLOTS)


class BookingCreateSerializer(serializers.ModelSerializer):
    booking_type = serializers.ChoiceField(
        choices=Booking.BookingType.choices,
        required=False,
        default=Booking.BookingType.CLOSED
    )
    required_players = serializers.IntegerField(required=False, default=1)
    open_game_note = serializers.CharField(required=False, allow_blank=True, default="")

    class Meta:
        model = Booking
        fields = [
            "ground",
            "date",
            "start_time",
            "end_time",
            "booking_type",
            "required_players",
            "open_game_note",
        ]

    def validate(self, attrs):
        ground = attrs["ground"]
        booking_type = attrs.get("booking_type", Booking.BookingType.CLOSED)
        required_players = attrs.get("required_players", 1)

        if ground.status != Ground.Status.APPROVED:
            raise serializers.ValidationError("Ground is not approved.")

        if not is_fixed_slot(attrs["start_time"], attrs["end_time"]):
            raise serializers.ValidationError("Invalid slot (must match system fixed timings).")

        if booking_type == Booking.BookingType.OPEN:
            if required_players < 1:
                raise serializers.ValidationError("Required players must be at least 1.")
        else:
            attrs["required_players"] = 1
            attrs["open_game_note"] = ""

        return attrs

    def create(self, validated_data):
        request = self.context["request"]

        booking_type = validated_data.get("booking_type", Booking.BookingType.CLOSED)
        required_players = validated_data.get("required_players", 1)

        with transaction.atomic():
            try:
                return Booking.objects.create(
                    player=request.user,
                    created_by=request.user,
                    source=Booking.Source.ONLINE,
                    status=Booking.Status.PENDING,
                    booking_type=booking_type,
                    current_players=1,
                    required_players=required_players if booking_type == Booking.BookingType.OPEN else 1,
                    **validated_data,
                )
            except IntegrityError:
                raise serializers.ValidationError("This slot is already booked.")


class BookingSerializer(serializers.ModelSerializer):
    ground_name = serializers.CharField(source="ground.name", read_only=True)
    location = serializers.CharField(source="ground.location", read_only=True)
    ground_phone = serializers.CharField(source="ground.phone", read_only=True)
    ground_price_per_hour = serializers.DecimalField(
        source="ground.price_per_hour",
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    ground_image_url = serializers.SerializerMethodField()
    spots_left = serializers.ReadOnlyField()
    is_open_joinable = serializers.ReadOnlyField()
    total_amount = serializers.SerializerMethodField()
    remaining_amount = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            "id",
            "ground",
            "ground_name",
            "location",
            "ground_phone",
            "ground_price_per_hour",
            "ground_image_url",
            "date",
            "start_time",
            "end_time",
            "status",
            "source",
            "booking_type",
            "current_players",
            "required_players",
            "spots_left",
            "is_open_joinable",
            "open_game_note",
            "transaction_uuid",
            "transaction_code",
            "paid_amount",
            "total_amount",
            "remaining_amount",
            "created_at",
        ]

    def get_ground_image_url(self, obj):
        request = self.context.get("request")
        image = getattr(obj.ground, "image", None)
        if not image:
            return None
        url = image.url
        return request.build_absolute_uri(url) if request else url

    def get_total_amount(self, obj):
        from decimal import Decimal

        if not obj.start_time or not obj.end_time or not obj.ground.price_per_hour:
            return None

        start_minutes = obj.start_time.hour * 60 + obj.start_time.minute
        end_minutes = obj.end_time.hour * 60 + obj.end_time.minute
        duration_hours = Decimal(end_minutes - start_minutes) / Decimal(60)

        total = Decimal(obj.ground.price_per_hour) * duration_hours
        return str(total.quantize(Decimal("0.01")))

    def get_remaining_amount(self, obj):
        from decimal import Decimal

        total_str = self.get_total_amount(obj)
        if total_str is None:
            return None

        total = Decimal(total_str)
        paid = Decimal(obj.paid_amount or 0)
        remaining = total - paid

        if remaining < 0:
            remaining = Decimal("0.00")

        return str(remaining.quantize(Decimal("0.01")))

class JoinOpenBookingSerializer(serializers.Serializer):
    def validate(self, attrs):
        booking = self.context["booking"]

        if booking.booking_type != Booking.BookingType.OPEN:
            raise serializers.ValidationError("This is not an open booking.")

        if booking.status != Booking.Status.BOOKED:
            raise serializers.ValidationError("This booking is not active.")

        if booking.current_players >= booking.required_players:
            raise serializers.ValidationError("This game is already full.")

        return attrs

    def save(self, **kwargs):
        booking = self.context["booking"]

        with transaction.atomic():
            booking = Booking.objects.select_for_update().get(pk=booking.pk)

            if booking.booking_type != Booking.BookingType.OPEN:
                raise serializers.ValidationError("This is not an open booking.")

            if booking.status != Booking.Status.BOOKED:
                raise serializers.ValidationError("This booking is not active.")

            if booking.current_players >= booking.required_players:
                raise serializers.ValidationError("This game is already full.")

            booking.current_players = F("current_players") + 1
            booking.save(update_fields=["current_players"])
            booking.refresh_from_db()

        return booking