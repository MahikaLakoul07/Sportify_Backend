# bookings/models.py
from django.conf import settings
from django.db import models
from django.utils import timezone

from grounds.models import Ground


class Booking(models.Model):
    class Status(models.TextChoices):
        BOOKED = "BOOKED", "Booked"
        CANCELLED = "CANCELLED", "Cancelled"

    class Source(models.TextChoices):
        ONLINE = "ONLINE", "Online"
        OFFLINE = "OFFLINE", "Offline/Physical"

    ground = models.ForeignKey(Ground, on_delete=models.CASCADE, related_name="bookings")

    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    # player (online booking). For offline booking, can be null.
    player = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bookings",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_bookings",
    )

    source = models.CharField(max_length=10, choices=Source.choices, default=Source.ONLINE)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.BOOKED)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["ground", "date", "start_time", "end_time"],
                name="uniq_booking_slot",
            ),
        ]

    def __str__(self):
        return f"{self.ground_id} {self.date} {self.start_time}-{self.end_time}"
