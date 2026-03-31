from django.db.models import Q
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import ConnectionRequest
from .serializers import (
    ConnectionRequestSerializer,
    SendConnectionRequestSerializer,
    SimplePlayerSerializer,
)


class ConnectionViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=["post"], url_path="request")
    def send_request(self, request):
        serializer = SendConnectionRequestSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        connection_request = serializer.save()

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

        return Response(ConnectionRequestSerializer(connection_request).data)

    @action(detail=True, methods=["post"], url_path="reject")
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
            Q(sender=request.user, receiver_id=player_id) |
            Q(sender_id=player_id, receiver=request.user)
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