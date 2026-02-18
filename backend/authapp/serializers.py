from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.password_validation import validate_password

User = get_user_model()

# Registration Serializer
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True, required=True)

    # Allow frontend to send role_name (player/owner) like your Postman
    role_name = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        # Keep user_type in fields so backend can store it
        # Add role_name so frontend can send it too
        fields = ['username', 'email', 'gender', 'password', 'confirm_password', 'user_type', 'role_name']

    def validate(self, attrs):
        # 1) Password match check
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})

        # 2) Accept user_type OR role_name and normalize
        role_name = attrs.get("role_name")
        user_type = attrs.get("user_type")

        # If role_name is provided (from frontend), convert it to UserType enum
        if role_name:
            role_name = str(role_name).strip().lower()
            if role_name == "player":
                attrs["user_type"] = User.UserType.PLAYER
            elif role_name == "owner":
                attrs["user_type"] = User.UserType.OWNER
            else:
                raise serializers.ValidationError({"role_name": "Role must be either 'player' or 'owner'."})

        # If user_type is provided directly, validate it
        if attrs.get("user_type") not in [User.UserType.PLAYER, User.UserType.OWNER]:
            raise serializers.ValidationError({"user_type": "User type must be PLAYER or OWNER."})

        return attrs

    def create(self, validated_data):
        # remove confirm_password because it is not part of User model
        validated_data.pop('confirm_password', None)

        # remove role_name because it's not part of User model
        validated_data.pop('role_name', None)

        user = User.objects.create_user(**validated_data)
        return user

# Login Serializer
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        user = authenticate(username=email, password=password)
        if not user:
            raise serializers.ValidationError("Invalid email or password")
        attrs['user'] = user
        return attrs

# Profile Serializer
class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'gender', 'user_type']
        read_only_fields = ['id', 'email', 'user_type']
