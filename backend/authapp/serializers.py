# users/serializers.py

# Import serializers from Django REST Framework.
# Serializers are used to convert model objects into JSON
# and also to validate incoming JSON data before saving it to the database.
from rest_framework import serializers

# Import get_user_model so Django gives us the currently active User model.
# This is the best practice because you are using a custom User model.
from django.contrib.auth import get_user_model, authenticate

# Import RefreshToken from SimpleJWT.
# It is commonly used when creating JWT access/refresh tokens for logged-in users.
# In this file, it is imported but not actually used yet.
from rest_framework_simplejwt.tokens import RefreshToken

# Get the active custom User model.
# Since you created your own User model in users/models.py,
# this line makes sure this serializer uses that model.
User = get_user_model()


# Serializer used for user registration/signup.
# ModelSerializer is useful because it automatically creates serializer fields
# based on the fields from the User model.
class RegisterSerializer(serializers.ModelSerializer):

    # Create a password field that accepts input but never shows it in API responses.
    # write_only=True means the client can send this value,
    # but it will not be returned back in the response.
    # min_length=6 means password must be at least 6 characters long.
    password = serializers.CharField(write_only=True, min_length=6)

    # Extra field used only for checking whether the user typed the same password twice.
    # This field is not part of the User model itself.
    # It is only used during validation.
    confirm_password = serializers.CharField(write_only=True, min_length=6)

    # Meta class tells Django REST Framework which model and fields to use.
    class Meta:
        # This serializer is based on the custom User model.
        model = User

        # These are the fields that will be accepted and/or returned by the serializer.
        # user_id is included so it can be shown in the response,
        # but it is read-only and not manually entered during registration.
        fields = [
            "user_id",
            "username",
            "email",
            "phone",
            "password",
            "confirm_password",
            "user_type",
            "gender",
        ]

        # read_only_fields means this field cannot be submitted for creating/updating.
        # Django will generate user_id automatically.
        read_only_fields = ["user_id"]

    # Custom validation method used to validate multiple fields together.
    # Here we compare password and confirm_password.
    def validate(self, attrs):
        # Get password value from incoming request data.
        password = attrs.get("password")

        # Get confirm_password value from incoming request data.
        confirm_password = attrs.get("confirm_password")

        # If both passwords do not match, raise a validation error.
        # This stops the registration process.
        if password != confirm_password:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )

        # If validation passes, return the validated attributes.
        return attrs

    # Custom create method to control how the user is saved.
    # This is needed because passwords must be hashed properly.
    def create(self, validated_data):
        # Remove confirm_password before saving because it is not an actual database field.
        validated_data.pop("confirm_password")  # remove before saving

        # Remove the plain password from validated_data and store it separately.
        # We do this because we should never save raw password directly.
        password = validated_data.pop("password")

        # Create a User object using the remaining validated fields
        # such as username, email, phone, gender, and user_type.
        user = User(**validated_data)

        # Hash the plain password properly before saving it.
        # This converts the raw password into a secure hashed version.
        user.set_password(password)

        # Save the new user into the database.
        user.save()

        # Return the created user object.
        return user


# Serializer used for user login.
# We use serializers.Serializer instead of ModelSerializer
# because login does not directly create or update a database model record.
# It only validates login credentials.
class LoginSerializer(serializers.Serializer):

    # Email field for login input.
    # This ensures the value looks like a valid email format.
    email = serializers.EmailField()

    # Password input field.
    # write_only=True means the password will not appear in the API response.
    password = serializers.CharField(write_only=True)

    # Custom validation logic for login.
    def validate(self, data):
        # Get email from request data.
        email = data.get("email")

        # Get password from request data.
        password = data.get("password")

        try:
            # Try to find the user with the given email.
            # Since the authentication is based on username by default,
            # you first fetch the user object using email.
            user_obj = User.objects.get(email=email)

        except User.DoesNotExist:
            # If no user exists with this email,
            # raise a generic validation error.
            raise serializers.ValidationError("Invalid credentials")

        # Authenticate the user using username and password.
        # Django's default authenticate usually expects username, not email.
        # So here we use the found user's username together with the entered password.
        user = authenticate(username=user_obj.username, password=password)

        # If authentication fails, it means password is wrong
        # or login is otherwise invalid.
        if not user:
            raise serializers.ValidationError("Invalid credentials")

        # If login is successful, attach the authenticated user object
        # into the validated data so it can be used later in the view.
        data["user"] = user

        # Return the validated data.
        return data


# Serializer used to show user profile information.
# This is typically used when returning currently logged-in user's data.
class ProfileSerializer(serializers.ModelSerializer):

    # Meta class defines which model and fields this serializer works with.
    class Meta:
        # Use the custom User model.
        model = User

        # These are the profile fields that will be included in the response.
        # This serializer is useful when you want to show user details
        # without exposing sensitive information like password.
        fields = [
            "user_id",
            "username",
            "email",
            "phone",
            "gender",
            "user_type",
        ]