from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from authapp.models import User
from chat.utils import get_or_create_direct_chat
from .models import ConnectionNotification, ConnectionRequest
from .serializers import (
    ConnectionNotificationSerializer,
    ConnectionRequestSerializer,
    SimplePlayerSerializer,
)


class ConnectionViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def _create_notification(self, *, user, actor, connection_request, notification_type, message):
        ConnectionNotification.objects.create(
            user=user,
            actor=actor,
            connection_request=connection_request,
            notification_type=notification_type,
            message=message,
        )

    @action(detail=False, methods=["post"], url_path="request")
    @transaction.atomic
    def send_request(self, request):
        receiver_id = request.data.get("receiver_id")

        if not receiver_id:
            return Response(
                {"detail": "receiver_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            receiver = User.objects.get(pk=receiver_id)
        except User.DoesNotExist:
            return Response(
                {"detail": "Player not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if receiver.pk == request.user.pk:
            return Response(
                {"detail": "You cannot send a connection request to yourself."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Already connected in either direction
        accepted_request = ConnectionRequest.objects.filter(
            status=ConnectionRequest.Status.ACCEPTED
        ).filter(
            Q(sender=request.user, receiver=receiver) |
            Q(sender=receiver, receiver=request.user)
        ).order_by("-created_at").first()

        if accepted_request:
            return Response(
                ConnectionRequestSerializer(accepted_request).data,
                status=status.HTTP_200_OK,
            )

        # Same direction existing request
        existing_same = ConnectionRequest.objects.filter(
            sender=request.user,
            receiver=receiver,
        ).order_by("-created_at").first()

        if existing_same:
            if existing_same.status == ConnectionRequest.Status.PENDING:
                return Response(
                    ConnectionRequestSerializer(existing_same).data,
                    status=status.HTTP_200_OK,
                )

            if existing_same.status == ConnectionRequest.Status.REJECTED:
                existing_same.status = ConnectionRequest.Status.PENDING
                existing_same.responded_at = None
                existing_same.save(update_fields=["status", "responded_at"])

                self._create_notification(
                    user=receiver,
                    actor=request.user,
                    connection_request=existing_same,
                    notification_type=ConnectionNotification.Type.REQUEST_SENT,
                    message=f"{request.user.username} has sent you a connection request.",
                )

                return Response(
                    ConnectionRequestSerializer(existing_same).data,
                    status=status.HTTP_200_OK,
                )

        # Reverse direction existing request
        existing_reverse = ConnectionRequest.objects.filter(
            sender=receiver,
            receiver=request.user,
        ).order_by("-created_at").first()

        if existing_reverse:
            if existing_reverse.status == ConnectionRequest.Status.PENDING:
                existing_reverse.status = ConnectionRequest.Status.ACCEPTED
                existing_reverse.responded_at = timezone.now()
                existing_reverse.save(update_fields=["status", "responded_at"])

                get_or_create_direct_chat(existing_reverse.sender, existing_reverse.receiver)

                self._create_notification(
                    user=existing_reverse.sender,
                    actor=request.user,
                    connection_request=existing_reverse,
                    notification_type=ConnectionNotification.Type.REQUEST_ACCEPTED,
                    message=f"{request.user.username} accepted your connection request.",
                )

                return Response(
                    ConnectionRequestSerializer(existing_reverse).data,
                    status=status.HTTP_200_OK,
                )

        # Fresh request
        connection_request = ConnectionRequest.objects.create(
            sender=request.user,
            receiver=receiver,
            status=ConnectionRequest.Status.PENDING,
        )

        self._create_notification(
            user=receiver,
            actor=request.user,
            connection_request=connection_request,
            notification_type=ConnectionNotification.Type.REQUEST_SENT,
            message=f"{request.user.username} has sent you a connection request.",
        )

        return Response(
            ConnectionRequestSerializer(connection_request).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"], url_path="requests/incoming")
    def incoming_requests(self, request):
        qs = ConnectionRequest.objects.filter(
            receiver=request.user,
            status=ConnectionRequest.Status.PENDING,
        ).select_related("sender", "receiver")

        return Response(ConnectionRequestSerializer(qs, many=True).data)

    @action(detail=False, methods=["get"], url_path="requests/outgoing")
    def outgoing_requests(self, request):
        qs = ConnectionRequest.objects.filter(
            sender=request.user,
            status=ConnectionRequest.Status.PENDING,
        ).select_related("sender", "receiver")

        return Response(ConnectionRequestSerializer(qs, many=True).data)

    @action(detail=True, methods=["post"], url_path="accept")
    @transaction.atomic
    def accept_request(self, request, pk=None):
        try:
            connection_request = ConnectionRequest.objects.select_related(
                "sender", "receiver"
            ).get(
                pk=pk,
                receiver=request.user,
                status=ConnectionRequest.Status.PENDING,
            )
        except ConnectionRequest.DoesNotExist:
            return Response(
                {"detail": "Pending request not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        connection_request.status = ConnectionRequest.Status.ACCEPTED
        connection_request.responded_at = timezone.now()
        connection_request.save(update_fields=["status", "responded_at"])

        get_or_create_direct_chat(connection_request.sender, connection_request.receiver)

        self._create_notification(
            user=connection_request.sender,
            actor=request.user,
            connection_request=connection_request,
            notification_type=ConnectionNotification.Type.REQUEST_ACCEPTED,
            message=f"{request.user.username} accepted your connection request.",
        )

        return Response(ConnectionRequestSerializer(connection_request).data)

    @action(detail=True, methods=["post"], url_path="reject")
    @transaction.atomic
    def reject_request(self, request, pk=None):
        try:
            connection_request = ConnectionRequest.objects.select_related(
                "sender", "receiver"
            ).get(
                pk=pk,
                receiver=request.user,
                status=ConnectionRequest.Status.PENDING,
            )
        except ConnectionRequest.DoesNotExist:
            return Response(
                {"detail": "Pending request not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        connection_request.status = ConnectionRequest.Status.REJECTED
        connection_request.responded_at = timezone.now()
        connection_request.save(update_fields=["status", "responded_at"])

        self._create_notification(
            user=connection_request.sender,
            actor=request.user,
            connection_request=connection_request,
            notification_type=ConnectionNotification.Type.REQUEST_REJECTED,
            message=f"{request.user.username} declined your connection request.",
        )

        return Response(ConnectionRequestSerializer(connection_request).data)

    @action(detail=False, methods=["get"], url_path="my")
    def my_connections(self, request):
        accepted = ConnectionRequest.objects.filter(
            status=ConnectionRequest.Status.ACCEPTED
        ).filter(
            Q(sender=request.user) | Q(receiver=request.user)
        ).select_related("sender", "receiver")

        connected_users = []
        seen_ids = set()

        for item in accepted:
            other_user = item.receiver if item.sender == request.user else item.sender
            other_user_id = getattr(other_user, "user_id", None)

            if other_user_id and other_user_id not in seen_ids:
                seen_ids.add(other_user_id)
                connected_users.append(other_user)

        return Response(SimplePlayerSerializer(connected_users, many=True).data)

    @action(detail=False, methods=["get"], url_path=r"status/(?P<player_id>\d+)")
    def connection_status(self, request, player_id=None):
        if str(getattr(request.user, "user_id", "")) == str(player_id):
            return Response({"status": "SELF"})

        relation = ConnectionRequest.objects.filter(
            Q(sender=request.user, receiver_id=player_id)
            | Q(sender_id=player_id, receiver=request.user)
        ).order_by("-created_at").first()

        if not relation:
            return Response({"status": "NONE"})

        if relation.status == ConnectionRequest.Status.ACCEPTED:
            return Response({"status": "CONNECTED", "request_id": relation.id})

        if relation.status == ConnectionRequest.Status.PENDING:
            if relation.sender == request.user:
                return Response({"status": "OUTGOING_PENDING", "request_id": relation.id})
            return Response({"status": "INCOMING_PENDING", "request_id": relation.id})

        return Response({"status": "NONE"})

    @action(detail=False, methods=["get"], url_path="notifications")
    def my_notifications(self, request):
        notifications = ConnectionNotification.objects.filter(
            user=request.user
        ).select_related(
            "actor",
            "connection_request",
            "connection_request__sender",
            "connection_request__receiver",
        )

        return Response(ConnectionNotificationSerializer(notifications, many=True).data)

    @action(detail=True, methods=["post"], url_path="notifications/read")
    def mark_notification_read(self, request, pk=None):
        try:
            notification = ConnectionNotification.objects.get(pk=pk, user=request.user)
        except ConnectionNotification.DoesNotExist:
            return Response(
                {"detail": "Notification not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        notification.is_read = True
        notification.save(update_fields=["is_read"])

        return Response({"detail": "Notification marked as read."})

    @action(detail=False, methods=["post"], url_path="notifications/read-all")
    def mark_all_notifications_read(self, request):
        ConnectionNotification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({"detail": "All notifications marked as read."})