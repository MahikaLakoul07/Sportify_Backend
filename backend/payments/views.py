import uuid
from decimal import Decimal

from django.conf import settings
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


def is_fixed_slot(start_time, end_time):
    return any(s == start_time and e == end_time for (s, e) in FIXED_SLOTS)


class EsewaInitiateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        ground_id = request.data.get("ground")
        date_str = request.data.get("date")
        start_str = request.data.get("start_time")
        end_str = request.data.get("end_time")
        total_amount = request.data.get("total_amount")

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

        if not is_fixed_slot(start_t, end_t):
            return Response({"detail": "Invalid slot"}, status=400)

        transaction_uuid = str(uuid.uuid4())

        try:
            booking = Booking.objects.create(
                ground=ground,
                date=d,
                start_time=start_t,
                end_time=end_t,
                player=request.user,
                created_by=request.user,
                source=Booking.Source.ONLINE,
                status=Booking.Status.PENDING,
                transaction_uuid=transaction_uuid,
            )
        except Exception:
            return Response({"detail": "Slot already booked."}, status=400)

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
                "booking_id": booking.id,
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

        try:
            booking = Booking.objects.get(transaction_uuid=transaction_uuid)
            booking.status = Booking.Status.BOOKED
            booking.transaction_code = transaction_code
            booking.paid_amount = Decimal(total_amount)
            booking.save()
        except Booking.DoesNotExist:
            return HttpResponseRedirect(
                f"{settings.FRONTEND_BASE_URL}/mybookings?payment=failure"
            )

        return HttpResponseRedirect(
            f"{settings.FRONTEND_BASE_URL}/mybookings/{booking.id}?payment=success&tx={transaction_uuid}"
        )


class EsewaFailureView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return HttpResponseRedirect(
            f"{settings.FRONTEND_BASE_URL}/mybookings?payment=failure"
        )