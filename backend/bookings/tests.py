from datetime import date, time

from rest_framework import status
from rest_framework.test import APITestCase

from authapp.models import User
from bookings.models import Booking
from chat.models import ChatGroup, ChatGroupMember
from chat.utils import create_temporary_chat_for_booking
from grounds.models import Ground

class BookingTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner1",
            email="owner1@test.com",
            password="test12345",
            user_type="owner",
            phone="9800000001",
        )

        self.player1 = User.objects.create_user(
            username="player1",
            email="player1@test.com",
            password="test12345",
            user_type="player",
            phone="9800000002",
        )

        self.player2 = User.objects.create_user(
            username="player2",
            email="player2@test.com",
            password="test12345",
            user_type="player",
            phone="9800000003",
        )

        self.ground = Ground.objects.create(
            owner=self.owner,
            name="Test Ground",
            location="Kathmandu",
            price_per_hour=1000,
            phone="9801111111",
            status=Ground.Status.APPROVED,
        )

    def auth_as(self, user):
        self.client.force_authenticate(user=user)

    # TC-B-01
    def test_create_private_booking(self):
        self.auth_as(self.player1)

        response = self.client.post(
            "/api/bookings/",
            {
                "ground": self.ground.id,
                "date": "2026-04-11",
                "start_time": "07:00:00",
                "end_time": "08:00:00",
                "booking_type": Booking.BookingType.CLOSED,
                "payment_mode": Booking.PaymentMode.PAY_DEPOSIT,
            },
            format="json",
        )

        if response.status_code != status.HTTP_201_CREATED:
            print("PRIVATE BOOKING ERROR:", response.data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        booking = Booking.objects.get(id=response.data["id"])
        self.assertEqual(booking.booking_type, Booking.BookingType.CLOSED)
        self.assertEqual(booking.current_players, 1)
        self.assertEqual(booking.required_players, 1)
        self.assertEqual(booking.player, self.player1)
        self.assertEqual(booking.created_by, self.player1)
        self.assertEqual(booking.status, Booking.Status.PENDING)
        self.assertEqual(booking.payment_mode, Booking.PaymentMode.PAY_DEPOSIT)

    # TC-B-02
    def test_create_public_booking(self):
        self.auth_as(self.player1)

        response = self.client.post(
            "/api/bookings/",
            {
                "ground": self.ground.id,
                "date": "2026-04-10",
                "start_time": "06:00:00",
                "end_time": "07:00:00",
                "booking_type": Booking.BookingType.OPEN,
                "required_players": 5,
                "open_game_note": "Need players",
                "payment_mode": Booking.PaymentMode.PAY_DEPOSIT,
            },
            format="json",
        )

        if response.status_code != status.HTTP_201_CREATED:
            print("PUBLIC BOOKING ERROR:", response.data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        booking = Booking.objects.get(id=response.data["id"])
        self.assertEqual(booking.booking_type, Booking.BookingType.OPEN)
        self.assertEqual(booking.current_players, 1)
        self.assertEqual(booking.required_players, 5)
        self.assertEqual(booking.open_game_note, "Need players")

        # open booking should auto-create temporary chat
        self.assertTrue(ChatGroup.objects.filter(booking=booking).exists())

    # TC-B-03
    def test_second_player_can_join_open_game(self):
        booking = Booking.objects.create(
            player=self.player1,
            created_by=self.player1,
            ground=self.ground,
            date=date(2026, 4, 10),
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

        self.auth_as(self.player2)
        response = self.client.post(
            f"/api/bookings/{booking.id}/join/",
            {},
            format="json",
        )

        if response.status_code != status.HTTP_200_OK:
            print("JOIN OPEN GAME ERROR:", response.data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        booking.refresh_from_db()
        self.assertEqual(booking.current_players, 2)
        self.assertTrue(
            ChatGroupMember.objects.filter(group=group, user=self.player2).exists()
        )

    # TC-B-04
    def test_full_open_game_cannot_be_joined(self):
        booking = Booking.objects.create(
            player=self.player1,
            created_by=self.player1,
            ground=self.ground,
            date=date(2026, 4, 10),
            start_time=time(6, 0),
            end_time=time(7, 0),
            status=Booking.Status.BOOKED,
            source=Booking.Source.ONLINE,
            booking_type=Booking.BookingType.OPEN,
            current_players=5,
            required_players=5,
            payment_mode=Booking.PaymentMode.PAY_DEPOSIT,
        )
        create_temporary_chat_for_booking(booking)

        self.auth_as(self.player2)
        response = self.client.post(
            f"/api/bookings/{booking.id}/join/",
            {},
            format="json",
        )

        if response.status_code != status.HTTP_400_BAD_REQUEST:
            print("FULL GAME JOIN ERROR:", response.data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

class BookingFailureTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="ownerf",
            email="ownerf@test.com",
            password="test12345",
            user_type="owner",
            phone="9810000001",
        )
        self.player1 = User.objects.create_user(
            username="playerf1",
            email="playerf1@test.com",
            password="test12345",
            user_type="player",
            phone="9810000002",
        )
        self.player2 = User.objects.create_user(
            username="playerf2",
            email="playerf2@test.com",
            password="test12345",
            user_type="player",
            phone="9810000003",
        )
        self.ground = Ground.objects.create(
            owner=self.owner,
            name="Failure Ground",
            location="Kathmandu",
            price_per_hour=1000,
            phone="9801000000",
            status=Ground.Status.APPROVED,
        )

    def auth_as(self, user):
        self.client.force_authenticate(user=user)

    def test_private_booking_fails_when_date_missing(self):
        self.auth_as(self.player1)

        response = self.client.post(
            "/api/bookings/",
            {
                "ground": self.ground.id,
                "start_time": "07:00:00",
                "end_time": "08:00:00",
                "booking_type": Booking.BookingType.CLOSED,
                "payment_mode": Booking.PaymentMode.PAY_DEPOSIT,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_public_booking_fails_when_required_players_invalid(self):
        self.auth_as(self.player1)

        response = self.client.post(
            "/api/bookings/",
            {
                "ground": self.ground.id,
                "date": "2026-04-20",
                "start_time": "06:00:00",
                "end_time": "07:00:00",
                "booking_type": Booking.BookingType.OPEN,
                "required_players": 0,
                "payment_mode": Booking.PaymentMode.PAY_DEPOSIT,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_join_full_open_game_fails(self):
        booking = Booking.objects.create(
            player=self.player1,
            created_by=self.player1,
            ground=self.ground,
            date=date(2026, 4, 20),
            start_time=time(6, 0),
            end_time=time(7, 0),
            status=Booking.Status.BOOKED,
            source=Booking.Source.ONLINE,
            booking_type=Booking.BookingType.OPEN,
            current_players=5,
            required_players=5,
            payment_mode=Booking.PaymentMode.PAY_DEPOSIT,
        )
        create_temporary_chat_for_booking(booking)

        self.auth_as(self.player2)
        response = self.client.post(f"/api/bookings/{booking.id}/join/", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_join_request_fails(self):
        booking = Booking.objects.create(
            player=self.player1,
            created_by=self.player1,
            ground=self.ground,
            date=date(2026, 4, 20),
            start_time=time(6, 0),
            end_time=time(7, 0),
            status=Booking.Status.BOOKED,
            source=Booking.Source.ONLINE,
            booking_type=Booking.BookingType.OPEN,
            current_players=1,
            required_players=5,
            payment_mode=Booking.PaymentMode.PAY_DEPOSIT,
        )
        create_temporary_chat_for_booking(booking)

        self.auth_as(self.player2)
        self.client.post(f"/api/bookings/{booking.id}/join/", {}, format="json")
        second_response = self.client.post(f"/api/bookings/{booking.id}/join/", {}, format="json")

        self.assertEqual(second_response.status_code, status.HTTP_400_BAD_REQUEST) 
