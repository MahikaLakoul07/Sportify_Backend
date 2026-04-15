# backend/chat/tests.py

from datetime import date, time, timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from authapp.models import User
from bookings.models import Booking
from grounds.models import Ground
from chat.models import ChatGroup, ChatGroupMember, ChatMessage, DirectChat
from chat.utils import create_temporary_chat_for_booking
from connections.models import ConnectionRequest


class ChatTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="ownerchat",
            email="ownerchat@test.com",
            password="test12345",
            user_type="owner",
            phone="9800000401",
        )

        self.player1 = User.objects.create_user(
            username="chatplayer1",
            email="chatplayer1@test.com",
            password="test12345",
            user_type="player",
            phone="9800000402",
        )

        self.player2 = User.objects.create_user(
            username="chatplayer2",
            email="chatplayer2@test.com",
            password="test12345",
            user_type="player",
            phone="9800000403",
        )

        self.ground = Ground.objects.create(
            owner=self.owner,
            name="Chat Ground",
            location="Bhaktapur",
            price_per_hour=900,
            status=Ground.Status.APPROVED,
        )

    # def test_open_booking_creates_temporary_group_chat(self):
    #     booking = Booking.objects.create(
    #         player=self.player1,
    #         created_by=self.player1,
    #         ground=self.ground,
    #         date=date(2026, 4, 18),
    #         start_time=time(6, 0),
    #         end_time=time(7, 0),
    #         status=Booking.Status.BOOKED,
    #         source=Booking.Source.ONLINE,
    #         booking_type=Booking.BookingType.OPEN,
    #         current_players=1,
    #         required_players=5,
    #         payment_mode=Booking.PaymentMode.PAY_DEPOSIT,
    #     )

    #     group = create_temporary_chat_for_booking(booking)

    #     self.assertIsNotNone(group)
    #     self.assertTrue(ChatGroup.objects.filter(booking=booking).exists())
    #     self.assertTrue(ChatGroupMember.objects.filter(group=group, user=self.player1).exists())

    # def test_group_member_can_send_message(self):
    #     booking = Booking.objects.create(
    #         player=self.player1,
    #         created_by=self.player1,
    #         ground=self.ground,
    #         date=date(2026, 4, 18),
    #         start_time=time(6, 0),
    #         end_time=time(7, 0),
    #         status=Booking.Status.BOOKED,
    #         source=Booking.Source.ONLINE,
    #         booking_type=Booking.BookingType.OPEN,
    #         current_players=1,
    #         required_players=5,
    #         payment_mode=Booking.PaymentMode.PAY_DEPOSIT,
    #     )
    #     group = create_temporary_chat_for_booking(booking)

    #     self.client.force_authenticate(user=self.player1)
    #     response = self.client.post(
    #         f"/api/chat-groups/{group.id}/messages/",
    #         {"message": "Hello team"},
    #         format="json"
    #     )

    #     self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    #     self.assertTrue(ChatMessage.objects.filter(group=group, sender=self.player1).exists())

    # def test_expired_group_chat_is_inaccessible(self):
    #     booking = Booking.objects.create(
    #         player=self.player1,
    #         created_by=self.player1,
    #         ground=self.ground,
    #         date=date(2026, 4, 18),
    #         start_time=time(6, 0),
    #         end_time=time(7, 0),
    #         status=Booking.Status.BOOKED,
    #         source=Booking.Source.ONLINE,
    #         booking_type=Booking.BookingType.OPEN,
    #         current_players=1,
    #         required_players=5,
    #         payment_mode=Booking.PaymentMode.PAY_DEPOSIT,
    #     )
    #     group = create_temporary_chat_for_booking(booking)
    #     group.expires_at = timezone.now() - timedelta(minutes=1)
    #     group.save(update_fields=["expires_at"])

    #     self.client.force_authenticate(user=self.player1)
    #     response = self.client.get(f"/api/chat-groups/{group.id}/messages/")

    #     self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # def test_connected_users_can_get_or_create_direct_chat(self):
    #     ConnectionRequest.objects.create(
    #         sender=self.player1,
    #         receiver=self.player2,
    #         status=ConnectionRequest.Status.ACCEPTED,
    #     )

    #     self.client.force_authenticate(user=self.player1)
    #     response = self.client.post("/api/direct-chats/get-or-create/", {
    #         "user_id": self.player2.user_id
    #     }, format="json")

    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #     self.assertTrue(DirectChat.objects.exists())

class ChatFailureTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner",
            email="owner@test.com",
            password="test123",
            user_type="owner",
            phone="9800000301",
        )

        self.player1 = User.objects.create_user(
            username="player1",
            email="player1@test.com",
            password="test123",
            user_type="player",
            phone="9800000302",
        )

        self.player2 = User.objects.create_user(
            username="player2",
            email="player2@test.com",
            password="test123",
            user_type="player",
            phone="9800000303",
        )

        self.ground = Ground.objects.create(
            owner=self.owner,
            name="Ground",
            location="Bhaktapur",
            price_per_hour=900,
            phone="9800000304",
            status=Ground.Status.APPROVED,
        )

    # # TC-CHF-01
    # def test_non_member_cannot_access_group_chat(self):
    #     booking = Booking.objects.create(
    #         player=self.player1,
    #         created_by=self.player1,
    #         ground=self.ground,
    #         date=date(2026, 4, 18),
    #         start_time=time(6, 0),
    #         end_time=time(7, 0),
    #         status=Booking.Status.BOOKED,
    #         source=Booking.Source.ONLINE,
    #         booking_type=Booking.BookingType.OPEN,
    #         current_players=1,
    #         required_players=5,
    #         payment_mode=Booking.PaymentMode.PAY_DEPOSIT,
    #     )

    #     group = create_temporary_chat_for_booking(booking)

    #     self.client.force_authenticate(user=self.player2)
    #     response = self.client.get(f"/api/chat-groups/{group.id}/messages/")

    #     self.assertIn(response.status_code, [
    #         status.HTTP_400_BAD_REQUEST,
    #         status.HTTP_403_FORBIDDEN
    #     ])

# TC-CHF-02
    def test_expired_group_chat_is_inaccessible(self):
        booking = Booking.objects.create(
            player=self.player1,
            created_by=self.player1,
            ground=self.ground,
            date=date(2026, 4, 18),
            start_time=time(6, 0),
            end_time=time(7, 0),
            status=Booking.Status.BOOKED,
            source=Booking.Source.ONLINE,
            booking_type=Booking.BookingType.OPEN,
            current_players=1,
            required_players=5,
            payment_mode=Booking.PaymentMode.PAY_DEPOSIT,
        )

        group = create_temporary_chat_for_booking(booking)
        group.expires_at = timezone.now() - timedelta(minutes=1)
        group.save()

        self.client.force_authenticate(user=self.player1)
        response = self.client.get(f"/api/chat-groups/{group.id}/messages/")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        