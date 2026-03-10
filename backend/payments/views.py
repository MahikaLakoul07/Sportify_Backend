import uuid
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponseRedirect
from django.utils.dateparse import parse_date, parse_time

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions

from bookings.models import Booking
from grounds.models import Ground
from grounds.slot_constants import FIXED_SLOTS

from .utils import (
    esewa_make_signature,
    esewa_make_signature_from_signed_fields,
    b64_to_json,
)


CACHE_TIMEOUT_SECONDS = 60 * 30  # 30 minutes


def is_valid_multi_slot(start_time, end_time):
    """
    Allow 1 to 5 consecutive fixed slots.

    Examples:
    06:00 -> 07:00 = valid
    06:00 -> 08:00 = valid
    10:00 -> 15:00 = valid
    10:00 -> 16:00 = invalid
    """
    slots = list(FIXED_SLOTS)

    start_indexes = [i for i, (s, _) in enumerate(slots) if s == start_time]
    end_indexes = [i for i, (_, e) in enumerate(slots) if e == end_time]

    if not start_indexes or not end_indexes:
        return False

    start_idx = start_indexes[0]
    end_idx = end_indexes[0]

    if end_idx < start_idx:
        return False

    slot_count = end_idx - start_idx + 1
    return 1 <= slot_count <= 5


def payment_cache_key(tx_uuid: str) -> str:
    return f"esewa_booking_intent:{tx_uuid}"


class EsewaInitiateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        ground_id = request.data.get("ground")
        date_str = request.data.get("date")
        start_str = request.data.get("start_time")
        end_str = request.data.get("end_time")
        total_amount = request.data.get("total_amount")

        booking_type = request.data.get("booking_type", Booking.BookingType.CLOSED)
        required_players = request.data.get("required_players", 1)
        open_game_note = request.data.get("open_game_note", "")
        needed_positions = request.data.get("needed_positions", [])

        try:
            ground = Ground.objects.get(
                pk=ground_id,
                status=Ground.Status.APPROVED
            )
        except Ground.DoesNotExist:
            return Response({"detail": "Ground not found."}, status=404)

        d = parse_date(date_str)
        start_t = parse_time(start_str)
        end_t = parse_time(end_str)

        if not (d and start_t and end_t):
            return Response({"detail": "Invalid date/time"}, status=400)

        # changed: allow 1 to 5 consecutive slots
        if not is_valid_multi_slot(start_t, end_t):
            return Response({"detail": "Invalid slot"}, status=400)

        if booking_type not in [Booking.BookingType.OPEN, Booking.BookingType.CLOSED]:
            return Response({"detail": "Invalid booking type."}, status=400)

        try:
            required_players = int(required_players)
        except (TypeError, ValueError):
            return Response({"detail": "Invalid required players."}, status=400)

        if booking_type == Booking.BookingType.OPEN:
            if required_players < 1:
                return Response({"detail": "Required players must be at least 1."}, status=400)
        else:
            required_players = 1
            open_game_note = ""
            needed_positions = []

        try:
            total_amount = Decimal(str(total_amount))
            if total_amount <= 0:
                return Response({"detail": "Invalid total amount."}, status=400)
        except (InvalidOperation, TypeError, ValueError):
            return Response({"detail": "Invalid total amount."}, status=400)

        # changed: overlap check for multi-slot booking
        overlap = Booking.objects.filter(
            ground=ground,
            date=d,
            status=Booking.Status.BOOKED,
            start_time__lt=end_t,
            end_time__gt=start_t,
        ).exists()

        if overlap:
            return Response({"detail": "Slot already booked."}, status=400)

        transaction_uuid = str(uuid.uuid4())

        cache.set(
            payment_cache_key(transaction_uuid),
            {
                "ground_id": ground.pk,
                "date": date_str,
                "start_time": start_str,
                "end_time": end_str,
                "user_id": request.user.pk,
                "booking_type": booking_type,
                "required_players": required_players,
                "open_game_note": open_game_note,
                "needed_positions": needed_positions,
                "total_amount": str(total_amount),
            },
            timeout=CACHE_TIMEOUT_SECONDS,
        )

        product_code = settings.ESEWA_PRODUCT_CODE
        secret = settings.ESEWA_SECRET_KEY
        signed_field_names = "total_amount,transaction_uuid,product_code"

        signature = esewa_make_signature(
            secret_key=secret,
            total_amount=str(total_amount),
            transaction_uuid=transaction_uuid,
            product_code=product_code,
        )

        fields = {
            "amount": str(total_amount),
            "tax_amount": "0",
            "total_amount": str(total_amount),
            "transaction_uuid": transaction_uuid,
            "product_code": product_code,
            "product_service_charge": "0",
            "product_delivery_charge": "0",
            "success_url": settings.ESEWA_SUCCESS_URL,
            "failure_url": settings.ESEWA_FAILURE_URL,
            "signed_field_names": signed_field_names,
            "signature": signature,
        }

        return Response(
            {
                "action_url": settings.ESEWA_FORM_URL,
                "fields": fields,
            },
            status=200,
        )


class EsewaSuccessView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        data_b64 = request.query_params.get("data")

        if not data_b64:
            return HttpResponseRedirect(
                f"{settings.FRONTEND_BASE_URL}/mybookings?payment=failure"
            )

        try:
            payload = b64_to_json(data_b64)
        except Exception:
            return HttpResponseRedirect(
                f"{settings.FRONTEND_BASE_URL}/mybookings?payment=failure"
            )

        received_signature = payload.get("signature")

        expected_signature = esewa_make_signature_from_signed_fields(
            settings.ESEWA_SECRET_KEY,
            payload
        )

        if received_signature != expected_signature:
            return HttpResponseRedirect(
                f"{settings.FRONTEND_BASE_URL}/mybookings?payment=failure"
            )

        status_value = payload.get("status")
        transaction_uuid = payload.get("transaction_uuid")
        transaction_code = payload.get("transaction_code")
        total_amount = payload.get("total_amount")

        if status_value != "COMPLETE":
            return HttpResponseRedirect(
                f"{settings.FRONTEND_BASE_URL}/mybookings?payment=failure"
            )

        intent = cache.get(payment_cache_key(transaction_uuid))
        if not intent:
            return HttpResponseRedirect(
                f"{settings.FRONTEND_BASE_URL}/mybookings?payment=failure"
            )

        try:
            ground = Ground.objects.get(
                pk=intent["ground_id"],
                status=Ground.Status.APPROVED
            )
        except Ground.DoesNotExist:
            cache.delete(payment_cache_key(transaction_uuid))
            return HttpResponseRedirect(
                f"{settings.FRONTEND_BASE_URL}/mybookings?payment=failure"
            )

        d = parse_date(intent["date"])
        start_t = parse_time(intent["start_time"])
        end_t = parse_time(intent["end_time"])
        user_id = intent["user_id"]
        booking_type = intent["booking_type"]
        required_players = int(intent["required_players"])
        open_game_note = intent["open_game_note"]

        # changed: overlap re-check at payment success time
        overlap = Booking.objects.filter(
            ground=ground,
            date=d,
            status=Booking.Status.BOOKED,
            start_time__lt=end_t,
            end_time__gt=start_t,
        ).exists()

        if overlap:
            cache.delete(payment_cache_key(transaction_uuid))
            return HttpResponseRedirect(
                f"{settings.FRONTEND_BASE_URL}/mybookings?payment=slot_taken"
            )

        try:
            booking = Booking.objects.create(
                ground=ground,
                date=d,
                start_time=start_t,
                end_time=end_t,
                player_id=user_id,
                created_by_id=user_id,
                source=Booking.Source.ONLINE,
                status=Booking.Status.BOOKED,
                booking_type=booking_type,
                current_players=1,
                required_players=required_players if booking_type == Booking.BookingType.OPEN else 1,
                open_game_note=open_game_note if booking_type == Booking.BookingType.OPEN else "",
                transaction_uuid=transaction_uuid,
                transaction_code=transaction_code,
                paid_amount=Decimal(total_amount),
            )
        except Exception:
            cache.delete(payment_cache_key(transaction_uuid))
            return HttpResponseRedirect(
                f"{settings.FRONTEND_BASE_URL}/mybookings?payment=failure"
            )

        cache.delete(payment_cache_key(transaction_uuid))

        return HttpResponseRedirect(
            f"{settings.FRONTEND_BASE_URL}/mybookings?payment=success&booking_id={booking.pk}&tx={transaction_uuid}"
        )


class EsewaFailureView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return HttpResponseRedirect(
            f"{settings.FRONTEND_BASE_URL}/mybookings?payment=failure"
        )