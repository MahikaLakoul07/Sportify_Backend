from django.contrib import admin
from .models import ConnectionRequest, ConnectionNotification


@admin.register(ConnectionRequest)
class ConnectionRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "sender", "receiver", "status", "created_at", "responded_at")
    list_filter = ("status", "created_at")
    search_fields = ("sender__username", "receiver__username", "sender__email", "receiver__email")


@admin.register(ConnectionNotification)
class ConnectionNotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "actor", "notification_type", "is_read", "created_at")
    list_filter = ("notification_type", "is_read", "created_at")
    search_fields = ("user__username", "actor__username", "message")