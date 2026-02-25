# grounds/models.py
from django.conf import settings
from django.db import models


class Ground(models.Model):
    class Size(models.TextChoices):
        FIVE = "FIVE", "5-a-side"
        SEVEN = "SEVEN", "7-a-side"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="grounds",
    )

    name = models.CharField(max_length=150)
    location = models.CharField(max_length=200)
    price_per_hour = models.PositiveIntegerField()
    description = models.TextField(blank=True)
    phone = models.CharField(max_length=30, blank=True)

    ground_size = models.CharField(
        max_length=10,
        choices=Size.choices,
        default=Size.FIVE,
    )

    image = models.ImageField(upload_to="grounds/", blank=True, null=True)

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.location})"


class GroundAvailability(models.Model):
    """
    Weekly recurring availability windows.
    Example:
      Sun 07:00-08:00
      Sun 09:00-10:00
      Mon 15:00-18:00
    """

    class DayOfWeek(models.IntegerChoices):
        MON = 0, "Mon"
        TUE = 1, "Tue"
        WED = 2, "Wed"
        THU = 3, "Thu"
        FRI = 4, "Fri"
        SAT = 5, "Sat"
        SUN = 6, "Sun"

    ground = models.ForeignKey(
        Ground,
        on_delete=models.CASCADE,
        related_name="availabilities",
    )

    day_of_week = models.IntegerField(choices=DayOfWeek.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["ground", "day_of_week", "start_time"]
        indexes = [
            models.Index(fields=["ground", "day_of_week", "start_time"]),
        ]
        constraints = [
            # Django 6+ uses "condition=" (not "check=")
            models.CheckConstraint(
                condition=models.Q(end_time__gt=models.F("start_time")),
                name="availability_end_after_start",
            ),
        ]

    def __str__(self):
        return (
            f"{self.ground.name} - {self.get_day_of_week_display()} "
            f"{self.start_time}-{self.end_time}"
        )


class GroundBlock(models.Model):
    """
    Optional but recommended:
    One-off blocks for a specific date/time (maintenance, private event, etc.)
    This overrides weekly availability for that date.
    """

    ground = models.ForeignKey(
        Ground,
        on_delete=models.CASCADE,
        related_name="blocks",
    )

    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    reason = models.CharField(max_length=200, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["ground", "date", "start_time"]
        indexes = [
            models.Index(fields=["ground", "date", "start_time"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_time__gt=models.F("start_time")),
                name="block_end_after_start",
            ),
        ]

    def __str__(self):
        return (
            f"{self.ground.name} BLOCK - {self.date} "
            f"{self.start_time}-{self.end_time}"
        )