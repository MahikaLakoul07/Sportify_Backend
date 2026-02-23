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

    ground_size = models.CharField(max_length=10, choices=Size.choices, default=Size.FIVE)

    image = models.ImageField(upload_to="grounds/", blank=True, null=True)

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.location})"