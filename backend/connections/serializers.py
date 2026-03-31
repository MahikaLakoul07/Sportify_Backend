from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers

from .models import ConnectionRequest

User = get_user_model()


class SimplePlayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["user_id", "username", "email"]


class ConnectionRequestSerializer(serializers.ModelSerializer):
    sender = SimplePlayerSerializer(read_only=True)
    receiver = SimplePlayerSerializer(read_only=True)

    class Meta:
        model = ConnectionRequest
        fields = [
            "id",
            "sender",
            "receiver",
            "status",
            "created_at",
            "responded_at",
        ]


class SendConnectionRequestSerializer(serializers.Serializer):
    receiver_id = serializers.IntegerField()

    def validate_receiver_id(self, value):
        request = self.context["request"]

        if getattr(request.user, "user_id", None) == value:
            raise serializers.ValidationError("You cannot send a request to yourself.")

        try:
            receiver = User.objects.get(user_id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("Receiver not found.")

        self.context["receiver"] = receiver
        return value

    def validate(self, attrs):
        request = self.context["request"]
        receiver = self.context["receiver"]

        already_connected = ConnectionRequest.objects.filter(
            status=ConnectionRequest.Status.ACCEPTED
        ).filter(
            Q(sender=request.user, receiver=receiver) |
            Q(sender=receiver, receiver=request.user)
        ).exists()

        if already_connected:
            raise serializers.ValidationError("You are already connected.")

        if ConnectionRequest.objects.filter(
            sender=request.user,
            receiver=receiver,
            status=ConnectionRequest.Status.PENDING,
        ).exists():
            raise serializers.ValidationError("Connection request already sent.")

        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        receiver = self.context["receiver"]

        reverse_request = ConnectionRequest.objects.filter(
            sender=receiver,
            receiver=request.user,
            status=ConnectionRequest.Status.PENDING,
        ).first()

        if reverse_request:
            reverse_request.status = ConnectionRequest.Status.ACCEPTED
            reverse_request.responded_at = timezone.now()
            reverse_request.save(update_fields=["status", "responded_at"])
            return reverse_request

        return ConnectionRequest.objects.create(
            sender=request.user,
            receiver=receiver,
            status=ConnectionRequest.Status.PENDING,
        )