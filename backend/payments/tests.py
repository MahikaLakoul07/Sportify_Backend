# backend/payments/tests.py

from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from authapp.models import User
from bookings.models import Booking
from grounds.models import Ground
from payments.views import create_booking_from_intent, payment_cache_key
from chat.models import ChatGroup


@override_settings(
    ESEWA_PRODUCT_CODE="EPAYTEST",
    ESEWA_SECRET_KEY="test_secret",
    ESEWA_FORM_URL="https://rc-epay.esewa.com.np/api/epay/main/v2/form",
    ESEWA_SUCCESS_URL="http://127.0.0.1:8000/api/payments/esewa/success/",
    ESEWA_FAILURE_URL="http://127.0.0.1:8000/api/payments/esewa/failure/",
    FRONTEND_BASE_URL="http://localhost:5173",
)
class PaymentInitiateTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner1",
            email="owner1@test.com",
            password="test12345",
            user_type="owner",
            phone="9800000101",
        )

        self.player = User.objects.create_user(
            username="player1",
            email="player1@test.com",
            password="test12345",
            user_type="player",
            phone="9800000102",
        )

        self.ground = Ground.objects.create(
            owner=self.owner,
            name="Payment Ground",
            location="Kathmandu",
            price_per_hour=1200,
            status=Ground.Status.APPROVED,
        )
#     # TC-P-01
#     def test_esewa_initiate_returns_payment_fields(self):
#         self.client.force_authenticate(user=self.player)

#         response = self.client.post("/api/payments/esewa/initiate/", {
#             "ground": self.ground.id,
#             "date": "2026-04-12",
#             "start_time": "06:00:00",
#             "end_time": "07:00:00",
#             "total_amount": "1200",
#             "booking_type": "CLOSED",
#             "payment_mode": "PAY_DEPOSIT",
#         }, format="json")

#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(response.data["mode"], "esewa")
#         self.assertIn("action_url", response.data)
#         self.assertIn("fields", response.data)
#         self.assertIn("transaction_uuid", response.data["fields"])


# class PaymentBookingCreationTests(TestCase):
#     def setUp(self):
#         self.owner = User.objects.create_user(
#             username="owner2",
#             email="owner2@test.com",
#             password="test12345",
#             user_type="owner",
#             phone="9800000201",
#         )

#         self.player = User.objects.create_user(
#             username="player2",
#             email="player2@test.com",
#             password="test12345",
#             user_type="player",
#             phone="9800000202",
#         )

#         self.ground = Ground.objects.create(
#             owner=self.owner,
#             name="Booked Ground",
#             location="Lalitpur",
#             price_per_hour=1500,
#             status=Ground.Status.APPROVED,
#         )

#     # TC-P-02
#     def test_create_booking_from_intent_creates_open_booking_and_chat(self):
#         tx_uuid = "tx1234567890abcd"

#         cache.set(payment_cache_key(tx_uuid), {
#             "ground_id": self.ground.pk,
#             "date": "2026-04-15",
#             "start_time": "06:00:00",
#             "end_time": "07:00:00",
#             "user_id": self.player.pk,
#             "booking_type": "OPEN",
#             "required_players": 5,
#             "open_game_note": "Need 4 more players",
#             "total_amount": "1500",
#             "payment_mode": "PAY_DEPOSIT",
#         }, timeout=1800)

#         booking, result = create_booking_from_intent(
#             transaction_uuid=tx_uuid,
#             transaction_code="TESTCODE123",
#             paid_amount="1500",
#         )

#         self.assertEqual(result, "created")
#         self.assertIsNotNone(booking)
#         self.assertEqual(booking.status, Booking.Status.BOOKED)
#         self.assertEqual(booking.booking_type, Booking.BookingType.OPEN)
#         self.assertTrue(ChatGroup.objects.filter(booking=booking).exists())

# class PaymentFailureTests(APITestCase):
#     def setUp(self):
#         self.owner = User.objects.create_user(
#             username="owner",
#             email="owner@test.com",
#             password="test123",
#             user_type="owner",
#             phone="9800000101",
#         )

#         self.player = User.objects.create_user(
#             username="player",
#             email="player@test.com",
#             password="test123",
#             user_type="player",
#             phone="9800000102",
#         )

#         self.ground = Ground.objects.create(
#             owner=self.owner,
#             name="Ground",
#             location="Kathmandu",
#             price_per_hour=1200,
#             phone="9800000103",
#             status=Ground.Status.APPROVED,
#         )

#     # TC-PF-01
#     def test_esewa_initiate_fails_for_invalid_ground(self):
#         self.client.force_authenticate(user=self.player)

#         response = self.client.post("/api/payments/esewa/initiate/", {
#             "ground": 999999,
#             "date": "2026-04-12",
#             "start_time": "06:00:00",
#             "end_time": "07:00:00",
#             "total_amount": "1200",
#             "booking_type": "CLOSED",
#             "payment_mode": "PAY_DEPOSIT",
#         }, format="json")

#         self.assertIn(response.status_code, [
#             status.HTTP_400_BAD_REQUEST,
#             status.HTTP_404_NOT_FOUND
#         ])

class PaymentIntentFailureTests(TestCase):

    # TC-PF-02
    def test_create_booking_from_missing_intent_fails(self):
        booking, result = create_booking_from_intent(
            transaction_uuid="invalid_uuid",
            transaction_code="TEST123",
            paid_amount="1000"
        )

        self.assertIsNone(booking)
        self.assertEqual(result, "intent_not_found")

        