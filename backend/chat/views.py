from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from bookings.models import Booking
from authapp.models import User

from .models import (
    ChatGroup,
    ChatGroupMember,
    ChatMessage,
    DirectChat,
    DirectMessage,
)
from .serializers import (
    ChatGroupSerializer,
    ChatMessageSerializer,
    MyChatGroupListSerializer,
    DirectChatSerializer,
    DirectMessageSerializer,
)
from .utils import get_or_create_direct_chat


def is_group_active(group):
    group.refresh_status()
    return group.is_active


def is_direct_chat_member(chat, user):
    return chat.user1_id == user.pk or chat.user2_id == user.pk


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

        for g in groups:
            is_group_active(g)

        serializer = MyChatGroupListSerializer(groups, many=True)
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
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)

        is_group_active(group)

        serializer = ChatGroupSerializer(group)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ChatMessageListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, group_id):
        group = get_object_or_404(ChatGroup, pk=group_id)

        is_member = ChatGroupMember.objects.filter(group=group, user=request.user).exists()
        if not is_member:
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)

        if not is_group_active(group):
            return Response({"detail": "This group chat has expired."}, status=status.HTTP_400_BAD_REQUEST)

        messages = group.messages.select_related("sender").order_by("created_at")
        serializer = ChatMessageSerializer(messages, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, group_id):
        group = get_object_or_404(ChatGroup, pk=group_id)

        is_member = ChatGroupMember.objects.filter(group=group, user=request.user).exists()
        if not is_member:
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)

        if not is_group_active(group):
            return Response({"detail": "This group chat has expired."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ChatMessageSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        msg = ChatMessage.objects.create(
            group=group,
            sender=request.user,
            message=serializer.validated_data["message"],
        )
        return Response(
            ChatMessageSerializer(msg, context={"request": request}).data,
            status=status.HTTP_201_CREATED
        )


class MyDirectChatsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        chats = (
            DirectChat.objects
            .filter(is_active=True)
            .filter(user1=request.user) |
            DirectChat.objects
            .filter(is_active=True)
            .filter(user2=request.user)
        )
        chats = chats.order_by("-created_at").distinct()

        serializer = DirectChatSerializer(chats, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class DirectChatCreateOrGetView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        other_user_id = request.data.get("user_id")
        if not other_user_id:
            return Response({"detail": "user_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        other_user = get_object_or_404(User, pk=other_user_id)

        try:
            chat = get_or_create_direct_chat(request.user, other_user)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = DirectChatSerializer(chat, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class DirectChatDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, chat_id):
        chat = get_object_or_404(DirectChat, pk=chat_id, is_active=True)

        if not is_direct_chat_member(chat, request.user):
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)

        serializer = DirectChatSerializer(chat, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class DirectMessageListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, chat_id):
        chat = get_object_or_404(DirectChat, pk=chat_id, is_active=True)

        if not is_direct_chat_member(chat, request.user):
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)

        messages = chat.messages.select_related("sender").order_by("created_at")
        serializer = DirectMessageSerializer(messages, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, chat_id):
        chat = get_object_or_404(DirectChat, pk=chat_id, is_active=True)

        if not is_direct_chat_member(chat, request.user):
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)

        serializer = DirectMessageSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        msg = DirectMessage.objects.create(
            chat=chat,
            sender=request.user,
            message=serializer.validated_data["message"],
        )
        return Response(
            DirectMessageSerializer(msg, context={"request": request}).data,
            status=status.HTTP_201_CREATED
        )