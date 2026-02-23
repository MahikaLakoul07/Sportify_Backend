from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model

from .serializers import RegisterSerializer, LoginSerializer, ProfileSerializer

User = get_user_model()


# views.py
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from .serializers import RegisterSerializer

User = get_user_model()

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        return Response(
            {
                "user": {
                    "user_id": user.user_id,
                    "username": user.username,
                    "email": user.email,
                    "phone": user.phone,
                    "user_type": user.user_type,
                    "gender": user.gender,
                },
                "refresh": str(refresh),
                "access": access_token,
            },
            status=status.HTTP_201_CREATED,
        )


# LOGIN
class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        response = Response({
            "user": {
                "user_id": user.user_id,
                "username": user.username,
                "email": user.email,
                "phone": user.phone,
                "user_type": user.user_type,
            },
            "refresh": str(refresh),
            "access": access_token,
        }, status=status.HTTP_200_OK)

        # Store access & refresh in HttpOnly cookies
        response.set_cookie("access", access_token, httponly=True, max_age=3600)
        response.set_cookie("refresh", str(refresh), httponly=True, max_age=7*24*3600)

        return response

# PROFILE
class ProfileView(generics.RetrieveAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user
