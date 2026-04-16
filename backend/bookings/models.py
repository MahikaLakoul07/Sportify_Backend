from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone
from grounds.models import Ground


class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending Payment"
        BOOKED = "BOOKED", "Booked"
        CANCELLED = "CANCELLED", "Cancelled"

    class Source(models.TextChoices):
        ONLINE = "ONLINE", "Online"
        OFFLINE = "OFFLINE", "Offline/Physical"

    class BookingType(models.TextChoices):
        OPEN = "OPEN", "Open Booking"
        CLOSED = "CLOSED", "Closed Booking"

    class PaymentMode(models.TextChoices):
        PAY_DEPOSIT = "PAY_DEPOSIT", "Pay on Field"
        PAY_FULL_ONLINE = "PAY_FULL_ONLINE", "Pay Full Online"

    ground = models.ForeignKey(
        Ground,
        on_delete=models.CASCADE,
        related_name="bookings"
    )

    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()

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

    source = models.CharField(
        max_length=10,
        choices=Source.choices,
        default=Source.ONLINE
    )

    payment_mode = models.CharField(
        max_length=20,
        choices=PaymentMode.choices,
        default=PaymentMode.PAY_DEPOSIT
    )

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING
    )

    booking_type = models.CharField(
        max_length=15,
        choices=BookingType.choices,
        default=BookingType.CLOSED
    )

    current_players = models.PositiveIntegerField(default=1)
    required_players = models.PositiveIntegerField(default=1)
    open_game_note = models.TextField(blank=True, default="")

    transaction_uuid = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True
    )
    transaction_code = models.CharField(
        max_length=32,
        null=True,
        blank=True
    )
    paid_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["ground", "date", "start_time", "end_time"],
                condition=~Q(status="CANCELLED"),
                name="uniq_active_booking_slot",
            ),
        ]

    def __str__(self):
        return f"{self.ground_id} {self.date} {self.start_time}-{self.end_time}"

    @property
    def spots_left(self):
        return max(self.required_players - self.current_players, 0)

    @property
    def is_open_joinable(self):
        return (
            self.booking_type == self.BookingType.OPEN
            and self.status == self.Status.BOOKED
            and self.current_players < self.required_players
        )