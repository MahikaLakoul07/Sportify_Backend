# backend/connections/tests.py

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from authapp.models import User
from chat.models import DirectChat
from connections.models import ConnectionRequest


# class ConnectionTests(APITestCase):
#     def setUp(self):
#         self.player1 = User.objects.create_user(
#             username="player1",
#             email="cp1@test.com",
#             password="test12345",
#             user_type="player",
#             phone="9800000301",
#         )

#         self.player2 = User.objects.create_user(
#             username="player2",
#             email="cp2@test.com",
#             password="test12345",
#             user_type="player",
#             phone="9800000302",
#         )

#     def test_send_connection_request(self):
#         self.client.force_authenticate(user=self.player1)

#         response = self.client.post("/api/connections/request/", {
#             "receiver_id": self.player2.user_id
#         }, format="json")

#         self.assertEqual(response.status_code, status.HTTP_201_CREATED)

#         req = ConnectionRequest.objects.get(sender=self.player1, receiver=self.player2)
#         self.assertEqual(req.status, ConnectionRequest.Status.PENDING)

#     def test_accept_connection_request_creates_direct_chat(self):
#         req = ConnectionRequest.objects.create(
#             sender=self.player1,
#             receiver=self.player2,
#             status=ConnectionRequest.Status.PENDING,
#         )

#         self.client.force_authenticate(user=self.player2)
#         response = self.client.post(f"/api/connections/{req.id}/accept/", {}, format="json")

#         self.assertEqual(response.status_code, status.HTTP_200_OK)

#         req.refresh_from_db()
#         self.assertEqual(req.status, ConnectionRequest.Status.ACCEPTED)
#         self.assertTrue(
#             DirectChat.objects.filter(
#                 user1_id=min(self.player1.pk, self.player2.pk),
#                 user2_id=max(self.player1.pk, self.player2.pk),
#             ).exists()
#         )

class ConnectionFailureTests(APITestCase):
    def setUp(self):
        self.player1 = User.objects.create_user(
            username="p1",
            email="p1@test.com",
            password="test123",
            user_type="player",
            phone="9800000201",
        )

        self.player2 = User.objects.create_user(
            username="p2",
            email="p2@test.com",
            password="test123",
            user_type="player",
            phone="9800000202",
        )

    # TC-CF-01
    def test_duplicate_connection_request_is_blocked(self):
        self.client.force_authenticate(user=self.player1)

        first = self.client.post("/api/connections/request/", {
            "receiver_id": self.player2.user_id
        }, format="json")

        second = self.client.post("/api/connections/request/", {
            "receiver_id": self.player2.user_id
        }, format="json")

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)

    # TC-CF-02
    def test_user_cannot_send_connection_request_to_self(self):
        self.client.force_authenticate(user=self.player1)

        response = self.client.post("/api/connections/request/", {
            "receiver_id": self.player1.user_id
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)