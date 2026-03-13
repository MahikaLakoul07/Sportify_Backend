from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from bookings.models import Booking
from .models import ChatGroup, ChatGroupMember
from .serializers import (
    ChatGroupSerializer,
    ChatMessageSerializer,
    MyChatGroupListSerializer,
)


def is_group_active(group):
    if not group.is_active:
        return False

    if timezone.now() >= group.expires_at:
        group.is_active = False
        group.save(update_fields=["is_active"])
        return False

    return True


class MyChatGroupsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        groups = (
            ChatGroup.objects
            .filter(members__user=request.user)
            .prefetch_related("members", "messages")
            .order_by("-created_at")
            .distinct()
        )

        # auto-expire if needed
        for g in groups:
            is_group_active(g)

        serializer = MyChatGroupListSerializer(groups, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class BookingChatGroupView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, booking_id):
        booking = get_object_or_404(Booking, pk=booking_id)
        group = get_object_or_404(ChatGroup, booking=booking)

        is_member = ChatGroupMember.objects.filter(
            group=group,
            user=request.user
        ).exists()

        if not is_member:
            return Response(
                {"detail": "Not allowed."},
                status=status.HTTP_403_FORBIDDEN
            )

        is_group_active(group)

        serializer = ChatGroupSerializer(group)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ChatGroupDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, group_id):
        group = get_object_or_404(ChatGroup.objects.prefetch_related("members"), pk=group_id)

        is_member = ChatGroupMember.objects.filter(
            group=group,
            user=request.user
        ).exists()

        if not is_member:
            return Response(
                {"detail": "Not allowed."},
                status=status.HTTP_403_FORBIDDEN
            )

        is_group_active(group)

        serializer = ChatGroupSerializer(group)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ChatMessageListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, group_id):
        group = get_object_or_404(ChatGroup, pk=group_id)

        is_member = ChatGroupMember.objects.filter(
            group=group,
            user=request.user
        ).exists()

        if not is_member:
            return Response(
                {"detail": "Not allowed."},
                status=status.HTTP_403_FORBIDDEN
            )

        if not is_group_active(group):
            return Response(
                {"detail": "This group chat has expired."},
                status=status.HTTP_400_BAD_REQUEST
            )

        messages = group.messages.select_related("sender").order_by("created_at")
        serializer = ChatMessageSerializer(messages, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, group_id):
        group = get_object_or_404(ChatGroup, pk=group_id)

        is_member = ChatGroupMember.objects.filter(
            group=group,
            user=request.user
        ).exists()

        if not is_member:
            return Response(
                {"detail": "Not allowed."},
                status=status.HTTP_403_FORBIDDEN
            )

        if not is_group_active(group):
            return Response(
                {"detail": "This group chat has expired."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = ChatMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(group=group, sender=request.user)

        return Response(serializer.data, status=status.HTTP_201_CREATED)