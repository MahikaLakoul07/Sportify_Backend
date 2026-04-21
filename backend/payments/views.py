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
from chat.utils import create_temporary_chat_for_booking  # <-- IMPORTANT

from .utils import (
    esewa_make_signature,
    esewa_make_signature_from_signed_fields,
    b64_to_json,
)


CACHE_TIMEOUT_SECONDS = 60 * 30  # 30 minutes


def is_valid_multi_slot(start_time, end_time):
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


def normalize_amount(value) -> str:
    amt = Decimal(str(value)).quantize(Decimal("1.00"))
    s = format(amt, "f")
    if s.endswith(".00"):
        return str(int(amt))
    return s


def create_booking_from_intent(transaction_uuid: str, transaction_code: str = "", paid_amount=None):
    print("\n========== CREATE BOOKING FROM INTENT START ==========")
    print("transaction_uuid:", transaction_uuid)
    print("transaction_code:", transaction_code)

    intent = cache.get(payment_cache_key(transaction_uuid))
    if not intent:
        print("Intent not found in cache")
        print("========== CREATE BOOKING FROM INTENT END ==========\n")
        return None, "intent_not_found"

    print("Intent found:", intent)

    try:
        ground = Ground.objects.get(
            pk=intent["ground_id"],
            status=Ground.Status.APPROVED
        )
    except Ground.DoesNotExist:
        print("Ground not found")
        cache.delete(payment_cache_key(transaction_uuid))
        print("========== CREATE BOOKING FROM INTENT END ==========\n")
        return None, "ground_not_found"

    d = parse_date(intent["date"])
    start_t = parse_time(intent["start_time"])
    end_t = parse_time(intent["end_time"])
    user_id = intent["user_id"]
    booking_type = intent["booking_type"]
    required_players = int(intent["required_players"])
    open_game_note = intent["open_game_note"]
    payment_mode = intent.get("payment_mode", "PAY_DEPOSIT")

    print("Parsed booking intent:")
    print("ground:", ground.pk)
    print("date:", d)
    print("start_time:", start_t)
    print("end_time:", end_t)
    print("user_id:", user_id)
    print("booking_type:", booking_type)
    print("required_players:", required_players)
    print("payment_mode:", payment_mode)

    overlap = Booking.objects.filter(
        ground=ground,
        date=d,
        status=Booking.Status.BOOKED,
        start_time__lt=end_t,
        end_time__gt=start_t,
    ).exists()

    if overlap:
        print("Overlap found -> slot already taken")
        cache.delete(payment_cache_key(transaction_uuid))
        print("========== CREATE BOOKING FROM INTENT END ==========\n")
        return None, "slot_taken"

    existing = Booking.objects.filter(transaction_uuid=transaction_uuid).first()
    if existing:
        print("Booking already exists with transaction_uuid:", transaction_uuid)

        # Ensure chat exists if this is an OPEN booking
        if str(existing.booking_type).upper() == "OPEN":
            print("Existing booking is OPEN -> ensuring temporary chat exists")
            create_temporary_chat_for_booking(existing)

        cache.delete(payment_cache_key(transaction_uuid))
        print("========== CREATE BOOKING FROM INTENT END ==========\n")
        return existing, "already_exists"

    if paid_amount is None:
        paid_amount = Decimal(str(intent["total_amount"]))

    try:
        booking = Booking.objects.create(
            ground=ground,
            date=d,
            start_time=start_t,
            end_time=end_t,
            player_id=user_id,
            created_by_id=user_id,
            source=Booking.Source.ONLINE,
            payment_mode=payment_mode,
            status=Booking.Status.BOOKED,
            booking_type=booking_type,
            current_players=1,
            required_players=required_players if str(booking_type).upper() == "OPEN" else 1,
            open_game_note=open_game_note if str(booking_type).upper() == "OPEN" else "",
            transaction_uuid=transaction_uuid,
            transaction_code=transaction_code,
            paid_amount=Decimal(str(paid_amount)),
        )
        print("Booking created successfully -> booking.id:", booking.id)
    except Exception as e:
        print("BOOKING CREATE ERROR:", str(e))
        cache.delete(payment_cache_key(transaction_uuid))
        print("========== CREATE BOOKING FROM INTENT END ==========\n")
        return None, "create_failed"

    # Create temporary group chat for OPEN bookings
    try:
        if str(booking.booking_type).upper() == "OPEN":
            print("OPEN booking detected -> creating temporary chat")
            group = create_temporary_chat_for_booking(booking)
            print("Temporary chat created -> group.id:", group.id)
        else:
            print("Booking is not OPEN -> no temp chat needed")
    except Exception as e:
        print("TEMP CHAT CREATE ERROR:", str(e))

    cache.delete(payment_cache_key(transaction_uuid))
    print("========== CREATE BOOKING FROM INTENT END ==========\n")
    return booking, "created"


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
        payment_mode = request.data.get("payment_mode", "PAY_DEPOSIT")

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
            return Response({"detail": "Invalid date/time."}, status=400)

        if not is_valid_multi_slot(start_t, end_t):
            return Response({"detail": "Invalid slot."}, status=400)

        if booking_type not in [Booking.BookingType.OPEN, Booking.BookingType.CLOSED]:
            return Response({"detail": "Invalid booking type."}, status=400)

        if payment_mode not in ["PAY_DEPOSIT", "PAY_FULL_ONLINE"]:
            return Response({"detail": "Invalid payment mode."}, status=400)

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

        overlap = Booking.objects.filter(
            ground=ground,
            date=d,
            status=Booking.Status.BOOKED,
            start_time__lt=end_t,
            end_time__gt=start_t,
        ).exists()

        if overlap:
            return Response({"detail": "Slot already booked."}, status=400)

        transaction_uuid = uuid.uuid4().hex[:20]
        total_amount_str = normalize_amount(total_amount)

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
                "total_amount": total_amount_str,
                "payment_mode": payment_mode,
            },
            timeout=CACHE_TIMEOUT_SECONDS,
        )

        payment_mode_setting = getattr(settings, "PAYMENT_MODE", "esewa").lower()

        product_code = settings.ESEWA_PRODUCT_CODE
        signed_field_names = "total_amount,transaction_uuid,product_code"

        signature = esewa_make_signature(
            secret_key=settings.ESEWA_SECRET_KEY,
            total_amount=total_amount_str,
            transaction_uuid=transaction_uuid,
            product_code=product_code,
        )

        fields = {
            "amount": total_amount_str,
            "tax_amount": "0",
            "total_amount": total_amount_str,
            "transaction_uuid": transaction_uuid,
            "product_code": product_code,
            "product_service_charge": "0",
            "product_delivery_charge": "0",
            "success_url": settings.ESEWA_SUCCESS_URL,
            "failure_url": settings.ESEWA_FAILURE_URL,
            "signed_field_names": signed_field_names,
            "signature": signature,
        }

        print("ESEWA ACTION URL:", settings.ESEWA_FORM_URL)
        print("ESEWA FIELDS:", fields)

        return Response(
            {
                "mode": "esewa",
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
            print("ESEWA SUCCESS PAYLOAD:", payload)
        except Exception as e:
            print("ESEWA PAYLOAD DECODE ERROR:", str(e))
            return HttpResponseRedirect(
                f"{settings.FRONTEND_BASE_URL}/mybookings?payment=failure"
            )

        received_signature = payload.get("signature")
        expected_signature = esewa_make_signature_from_signed_fields(
            settings.ESEWA_SECRET_KEY,
            payload
        )

        if received_signature != expected_signature:
            print("ESEWA SIGNATURE MISMATCH")
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

        booking, status_code = create_booking_from_intent(
            transaction_uuid=transaction_uuid,
            transaction_code=transaction_code or "",
            paid_amount=Decimal(str(total_amount)),
        )

        if status_code in ["created", "already_exists"]:
            return HttpResponseRedirect(
                f"{settings.FRONTEND_BASE_URL}/mybookings?payment=success&booking_id={booking.pk}&tx={transaction_uuid}"
            )

        if status_code == "slot_taken":
            return HttpResponseRedirect(
                f"{settings.FRONTEND_BASE_URL}/mybookings?payment=slot_taken"
            )

        return HttpResponseRedirect(
            f"{settings.FRONTEND_BASE_URL}/mybookings?payment=failure"
        )


class EsewaFailureView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return HttpResponseRedirect(
            f"{settings.FRONTEND_BASE_URL}/mybookings?payment=failure"
        )