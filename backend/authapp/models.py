from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):

    class UserType(models.TextChoices):
        PLAYER = "player", "Player"
        OWNER = "owner", "Owner"

    class Gender(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"

    user_id = models.AutoField(primary_key=True)
    phone = models.CharField(max_length=15, unique=True)
    email = models.EmailField(unique=True)

    user_type = models.CharField(
        max_length=10,
        choices=UserType.choices,
        default=UserType.PLAYER
    )

    gender = models.CharField(
        max_length=10,
        choices=Gender.choices,
        default=Gender.MALE
    )

    def __str__(self):
        return self.username
