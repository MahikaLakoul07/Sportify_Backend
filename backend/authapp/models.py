# users/models.py

# Import Django's models module so we can create database tables using Python classes.
from django.db import models

# Import AbstractUser so we can extend Django's built-in user system
# instead of building authentication completely from scratch.
from django.contrib.auth.models import AbstractUser


# Create a custom User model by inheriting from Django's default AbstractUser.
# This means this model already includes built-in fields like:
# username, first_name, last_name, password, is_staff, is_active, etc.
# We are simply adding extra fields such as phone, email, user_type, and gender.
class User(AbstractUser):

    # This inner class is used to define fixed choices for the "user_type" field.
    # TextChoices helps us avoid typing random strings manually in many places.
    # It gives cleaner code and safer database values.
    class UserType(models.TextChoices):
        # PLAYER is the actual value stored in the database.
        # "Player" is the display label shown in forms/admin.
        PLAYER = "player", "Player"

        # OWNER is the database value.
        # "Owner" is the display label.
        OWNER = "owner", "Owner"

    # This inner class defines fixed choices for the "gender" field.
    # Again, this prevents invalid values like "abc" or "unknown text"
    # unless you explicitly add them here.
    class Gender(models.TextChoices):
        # Stores "male" in the database and shows "Male" in forms/admin.
        MALE = "male", "Male"

        # Stores "female" in the database and shows "Female" in forms/admin.
        FEMALE = "female", "Female"

    # Custom primary key for the user table.
    # AutoField means Django will automatically generate values like 1, 2, 3, 4...
    # primary_key=True means this becomes the main unique identifier for each user.
    # Since user_id is being used here, Django will use this instead of the default "id".
    user_id = models.AutoField(primary_key=True)

    # Phone number field for the user.
    # max_length=15 means the phone number can contain up to 15 characters.
    # unique=True means no two users can register with the same phone number.
    phone = models.CharField(max_length=15, unique=True)

    # Email field for the user.
    # unique=True means each email can only be used once in the system.
    email = models.EmailField(unique=True)

    # Field to store whether the user is a player or an owner.
    # choices=UserType.choices restricts the allowed values to only:
    # "player" or "owner"
    # default=UserType.PLAYER means if no value is provided, Django will save "player".
    user_type = models.CharField(
        max_length=10,
        choices=UserType.choices,
        default=UserType.PLAYER
    )

    # Field to store gender of the user.
    # choices=Gender.choices restricts the values to:
    # "male" or "female"
    # default=Gender.MALE means if nothing is selected, Django will save "male".
    gender = models.CharField(
        max_length=10,
        choices=Gender.choices,
        default=Gender.MALE
    )

    # This special method controls what gets shown when you print a User object.
    # For example, in Django admin, shell, or logs,
    # instead of seeing something unclear like "User object (1)",
    # you will see the username of that user.
    def __str__(self):
        # Return the username of the current user as the string representation.
        return self.username