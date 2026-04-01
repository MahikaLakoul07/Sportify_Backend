from rest_framework import serializers

from .models import (
    ChatGroup,
    ChatGroupMember,
    ChatMessage,
    DirectChat,
    DirectMessage,
)


class ChatGroupMemberSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    user_id = serializers.IntegerField(source="user.pk", read_only=True)

    class Meta:
        model = ChatGroupMember
        fields = ["id", "user_id", "username", "joined_at"]


class ChatMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender.username", read_only=True)
    sender_id = serializers.IntegerField(source="sender.pk", read_only=True)
    is_mine = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = [
            "id",
            "group",
            "sender_id",
            "sender_name",
            "message",
            "created_at",
            "is_mine",
        ]
        read_only_fields = ["group", "sender_id", "sender_name", "created_at", "is_mine"]

    def get_is_mine(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return obj.sender_id == request.user.pk


class ChatGroupSerializer(serializers.ModelSerializer):
    members = ChatGroupMemberSerializer(many=True, read_only=True)
    member_count = serializers.IntegerField(source="members.count", read_only=True)

    class Meta:
        model = ChatGroup
        fields = [
            "id",
            "booking",
            "name",
            "is_temporary",
            "is_active",
            "expires_at",
            "created_at",
            "member_count",
            "members",
        ]


class MyChatGroupListSerializer(serializers.ModelSerializer):
    member_count = serializers.IntegerField(source="members.count", read_only=True)
    last_message = serializers.SerializerMethodField()
    last_time = serializers.SerializerMethodField()

    class Meta:
        model = ChatGroup
        fields = [
            "id",
            "name",
            "member_count",
            "last_message",
            "last_time",
            "expires_at",
            "is_active",
        ]

    def get_last_message(self, obj):
        last = obj.messages.order_by("-created_at").first()
        return last.message if last else "No messages yet"

    def get_last_time(self, obj):
        last = obj.messages.order_by("-created_at").first()
        return last.created_at if last else ""


class DirectChatSerializer(serializers.ModelSerializer):
    other_user_id = serializers.SerializerMethodField()
    other_username = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    last_time = serializers.SerializerMethodField()

    class Meta:
        model = DirectChat
        fields = [
            "id",
            "other_user_id",
            "other_username",
            "last_message",
            "last_time",
            "is_active",
            "created_at",
        ]

    def _other_user(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        return obj.user2 if obj.user1_id == request.user.pk else obj.user1

    def get_other_user_id(self, obj):
        other = self._other_user(obj)
        return other.pk if other else None

    def get_other_username(self, obj):
        other = self._other_user(obj)
        return other.username if other else "User"

    def get_last_message(self, obj):
        last = obj.messages.order_by("-created_at").first()
        return last.message if last else "No messages yet"

    def get_last_time(self, obj):
        last = obj.messages.order_by("-created_at").first()
        return last.created_at if last else ""


class DirectMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender.username", read_only=True)
    sender_id = serializers.IntegerField(source="sender.pk", read_only=True)
    is_mine = serializers.SerializerMethodField()

    class Meta:
        model = DirectMessage
        fields = [
            "id",
            "chat",
            "sender_id",
            "sender_name",
            "message",
            "created_at",
            "is_mine",
        ]
        read_only_fields = ["chat", "sender_id", "sender_name", "created_at", "is_mine"]

    def get_is_mine(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return obj.sender_id == request.user.pk