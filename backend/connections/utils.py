from .models import ConnectionNotification


def create_notification(
    *,
    user,
    actor,
    notification_type,
    message,
    connection_request=None,
):
    return ConnectionNotification.objects.create(
        user=user,
        actor=actor,
        connection_request=connection_request,
        notification_type=notification_type,
        message=message,
    )