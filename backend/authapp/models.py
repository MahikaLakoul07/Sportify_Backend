from django.db import models
from django.contrib.auth.models import AbstractUser  # ✅ needed import

# Make sure you have Role defined somewhere, or import it
# from .role import Role   # Example if you have a Role model in another file

class User(AbstractUser):
    class UserType(models.TextChoices):
        PLAYER = "player", "Player"
        OWNER = "owner", "Owner"

    user_id = models.AutoField(primary_key=True)
    # Ensure Role model exists or comment this out for now
    # role = models.ForeignKey(Role, on_delete=models.CASCADE)
    phone = models.CharField(max_length=15, unique=True)
    user_type = models.CharField(
        max_length=10,
        choices=UserType.choices,
        default=UserType.PLAYER
    )
    gender = models.CharField(max_length=10, null=True, blank=True)

    def __str__(self):
        return self.username
