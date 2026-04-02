# backend/bookings/serializers.py

from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import F
from rest_framework import serializers

from .models import Booking
from grounds.models import Ground
from grounds.slot_constants import FIXED_SLOTS
from chat.models import ChatGroupMember


def is_fixed_slot(start_time, end_time):
    return any(s == start_time and e == end_time for (s, e) in FIXED_SLOTS)


class BookingCreateSerializer(serializers.ModelSerializer):
    booking_type = serializers.ChoiceField(
        choices=Booking.BookingType.choices,
        required=False,
        default=Booking.BookingType.CLOSED,
    )
    required_players = serializers.IntegerField(required=False, default=1)
    open_game_note = serializers.CharField(required=False, allow_blank=True, default="")
    payment_mode = serializers.ChoiceField(
        choices=Booking.PaymentMode.choices,
        required=False,
        default=Booking.PaymentMode.PAY_DEPOSIT,
    )

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
            "payment_mode",
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
        payment_mode = validated_data.get("payment_mode", Booking.PaymentMode.PAY_DEPOSIT)

        with transaction.atomic():
            try:
                booking = Booking.objects.create(
                    player=request.user,
                    created_by=request.user,
                    source=Booking.Source.ONLINE,
                    payment_mode=payment_mode,
                    status=Booking.Status.PENDING,
                    booking_type=booking_type,
                    current_players=1,
                    required_players=required_players if booking_type == Booking.BookingType.OPEN else 1,
                    **validated_data,
                )
                return booking
            except IntegrityError:
                raise serializers.ValidationError("This slot is already booked.")


class BookingSerializer(serializers.ModelSerializer):
    player = serializers.IntegerField(source="player_id", read_only=True)
    created_by = serializers.IntegerField(source="created_by_id", read_only=True)
    ground_name = serializers.CharField(source="ground.name", read_only=True)
    location = serializers.CharField(source="ground.location", read_only=True)
    ground_phone = serializers.CharField(source="ground.phone", read_only=True)
    ground_owner_id = serializers.IntegerField(source="ground.owner_id", read_only=True)

    ground_price_per_hour = serializers.DecimalField(
        source="ground.price_per_hour",
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )

    ground_image_url = serializers.SerializerMethodField()
    spots_left = serializers.ReadOnlyField()
    is_open_joinable = serializers.ReadOnlyField()
    total_amount = serializers.SerializerMethodField()
    remaining_amount = serializers.SerializerMethodField()
    payment_display = serializers.SerializerMethodField()
    group_chat_id = serializers.SerializerMethodField()
    is_joined = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            "id",
            "player",
            "ground",
            "ground_name",
            "location",
            "ground_phone",
            "ground_owner_id",
            "ground_price_per_hour",
            "ground_image_url",
            "date",
            "start_time",
            "end_time",
            "status",
            "source",
            "payment_mode",
            "payment_display",
            "booking_type",
            "created_by",
            "current_players",
            "required_players",
            "spots_left",
            "is_open_joinable",
            "is_joined",
            "group_chat_id",
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
        if not obj.start_time or not obj.end_time or not obj.ground.price_per_hour:
            return None

        start_minutes = obj.start_time.hour * 60 + obj.start_time.minute
        end_minutes = obj.end_time.hour * 60 + obj.end_time.minute
        duration_hours = Decimal(end_minutes - start_minutes) / Decimal(60)

        total = Decimal(obj.ground.price_per_hour) * duration_hours
        return str(total.quantize(Decimal("0.01")))

    def get_remaining_amount(self, obj):
        total_str = self.get_total_amount(obj)
        if total_str is None:
            return None

        total = Decimal(total_str)
        paid = Decimal(obj.paid_amount or 0)
        remaining = total - paid

        if remaining < 0:
            remaining = Decimal("0.00")

        return str(remaining.quantize(Decimal("0.01")))

    def get_payment_display(self, obj):
        if obj.payment_mode == Booking.PaymentMode.PAY_DEPOSIT:
            return "PAY ON FIELD"
        if obj.payment_mode == Booking.PaymentMode.PAY_FULL_ONLINE:
            return "ONLINE"
        if obj.source == Booking.Source.OFFLINE:
            return "PAY ON FIELD"
        if obj.source == Booking.Source.ONLINE:
            return "ONLINE"
        return "N/A"

    def get_group_chat_id(self, obj):
        group = getattr(obj, "chat_group", None)
        return group.id if group else None

    def get_is_joined(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)

        if not user or not user.is_authenticated:
            return False

        if obj.created_by_id == user.pk:
            return True

        group = getattr(obj, "chat_group", None)
        if not group:
            return False

        return ChatGroupMember.objects.filter(group=group, user=user).exists()


class JoinOpenBookingSerializer(serializers.Serializer):
    def validate(self, attrs):
        booking = self.context["booking"]
        request = self.context["request"]
        group = getattr(booking, "chat_group", None)

        if booking.booking_type != Booking.BookingType.OPEN:
            raise serializers.ValidationError("This is not an open booking.")

        if booking.status != Booking.Status.BOOKED:
            raise serializers.ValidationError("This booking is not active.")

        if booking.created_by_id == request.user.pk:
            raise serializers.ValidationError("You cannot join a game you created.")

        if group and ChatGroupMember.objects.filter(group=group, user=request.user).exists():
            raise serializers.ValidationError("You have already joined this game.")

        if booking.current_players >= booking.required_players:
            raise serializers.ValidationError("This game is already full.")

        return attrs

    def save(self, **kwargs):
        booking = self.context["booking"]
        request = self.context["request"]

        with transaction.atomic():
            booking = Booking.objects.select_for_update().get(pk=booking.pk)
            group = getattr(booking, "chat_group", None)

            if booking.booking_type != Booking.BookingType.OPEN:
                raise serializers.ValidationError("This is not an open booking.")

            if booking.status != Booking.Status.BOOKED:
                raise serializers.ValidationError("This booking is not active.")

            if booking.created_by_id == request.user.pk:
                raise serializers.ValidationError("You cannot join a game you created.")

            if group and ChatGroupMember.objects.filter(group=group, user=request.user).exists():
                raise serializers.ValidationError("You have already joined this game.")

            if booking.current_players >= booking.required_players:
                raise serializers.ValidationError("This game is already full.")

            booking.current_players = F("current_players") + 1
            booking.save(update_fields=["current_players"])
            booking.refresh_from_db()

        return booking


class OwnerDirectBookingSerializer(serializers.ModelSerializer):
    notes = serializers.CharField(write_only=True, required=False, allow_blank=True, default="")

    class Meta:
        model = Booking
        fields = [
            "ground",
            "date",
            "start_time",
            "end_time",
            "notes",
        ]

    def validate(self, attrs):
        request = self.context["request"]
        ground = attrs["ground"]

        if ground.owner_id != request.user.user_id:
            raise serializers.ValidationError("You can only book your own ground.")

        if ground.status != Ground.Status.APPROVED:
            raise serializers.ValidationError("Ground is not approved.")

        if not is_fixed_slot(attrs["start_time"], attrs["end_time"]):
            raise serializers.ValidationError("Invalid slot.")

        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        notes = validated_data.pop("notes", "")

        with transaction.atomic():
            overlap_exists = Booking.objects.select_for_update().filter(
                ground=validated_data["ground"],
                date=validated_data["date"],
                status=Booking.Status.BOOKED,
                start_time__lt=validated_data["end_time"],
                end_time__gt=validated_data["start_time"],
            ).exists()

            if overlap_exists:
                raise serializers.ValidationError("This slot is already booked.")

            booking = Booking.objects.create(
                player=request.user,
                created_by=request.user,
                source=Booking.Source.OFFLINE,
                status=Booking.Status.BOOKED,
                booking_type=Booking.BookingType.CLOSED,
                payment_mode=Booking.PaymentMode.PAY_DEPOSIT,
                current_players=1,
                required_players=1,
                open_game_note=notes,
                paid_amount=0,
                **validated_data,
            )

        return booking