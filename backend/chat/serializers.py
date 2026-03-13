from rest_framework import serializers
from .models import ChatGroup, ChatGroupMember, ChatMessage


class ChatGroupMemberSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = ChatGroupMember
        fields = ["id", "user", "username", "joined_at"]


class ChatMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender.username", read_only=True)

    class Meta:
        model = ChatMessage
        fields = [
            "id",
            "group",
            "sender",
            "sender_name",
            "message",
            "created_at",
        ]
        read_only_fields = ["group", "sender", "created_at", "sender_name"]


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
        if not last:
            return "No messages yet"
        return last.message

    def get_last_time(self, obj):
        last = obj.messages.order_by("-created_at").first()
        if not last:
            return ""
        return last.created_at