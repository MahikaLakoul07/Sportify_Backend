import uuid
import requests
from django.conf import settings
from django.http import HttpResponseRedirect
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.utils.dateparse import parse_date
from django.utils.dateparse import parse_time

from bookings.models import Booking
from grounds.models import Ground
from grounds.slot_constants import FIXED_SLOTS
from .utils import esewa_make_signature, b64_to_json

def is_fixed_slot(start_time, end_time):
    return any(s == start_time and e == end_time for (s, e) in FIXED_SLOTS)

class EsewaInitiateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    # POST /api/payments/esewa/initiate/
    # {ground, date:"YYYY-MM-DD", start_time:"06:00", end_time:"07:00", total_amount: 200}
    def post(self, request):
        ground_id = request.data.get("ground")
        date_str = request.data.get("date")
        start_str = request.data.get("start_time")
        end_str = request.data.get("end_time")
        total_amount = request.data.get("total_amount")

        ground = Ground.objects.get(pk=ground_id, status=Ground.Status.APPROVED)
        d = parse_date(date_str)
        start_t = parse_time(start_str)
        end_t = parse_time(end_str)

        if not (d and start_t and end_t):
            return Response({"detail": "Invalid date/time"}, status=400)
        if not is_fixed_slot(start_t, end_t):
            return Response({"detail": "Invalid slot"}, status=400)

        # Create PENDING booking (locks the slot via UniqueConstraint)
        tx_uuid = str(uuid.uuid4())
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
                transaction_uuid=tx_uuid,
            )
        except Exception:
            return Response({"detail": "Slot already booked."}, status=400)

        product_code = settings.ESEWA_PRODUCT_CODE
        secret = settings.ESEWA_SECRET_KEY

        # eSewa requires signed_field_names + signature over total_amount,transaction_uuid,product_code [page:1]
        signed_field_names = "total_amount,transaction_uuid,product_code"
        signature = esewa_make_signature(
            secret_key=secret,
            total_amount=str(total_amount),
            transaction_uuid=tx_uuid,
            product_code=product_code,
        )

        fields = {
            "amount": str(total_amount),
            "tax_amount": "0",
            "total_amount": str(total_amount),
            "transaction_uuid": tx_uuid,
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
            return Response({"detail": "Missing data"}, status=400)

        payload = b64_to_json(data_b64)

        received = payload.get("signature")
        expected = esewa_make_signature_from_signed_fields(settings.ESEWA_SECRET_KEY, payload)

        if received != expected:
            return Response({"detail": "Invalid signature"}, status=400)
class EsewaFailureView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        # You may or may not get data here; safest: just redirect
        return HttpResponseRedirect(f"{settings.FRONTEND_BASE_URL}/payment/failure")
