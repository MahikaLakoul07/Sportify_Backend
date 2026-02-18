from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import RegisterSerializer, LoginSerializer, ProfileSerializer
from django.contrib.auth import get_user_model

User = get_user_model()

# REGISTER VIEW
class RegisterPlayerView(generics.CreateAPIView):
    serializer_class = RegisterSerializer

# LOGIN VIEW
class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        # Validate input
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Get validated user
        user = serializer.validated_data['user']

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        # Return response
        return Response({
            "user": {
                # IMPORTANT: use user_id not id (since you have custom PK)
                "user_id": user.user_id,
                "username": user.username,
                "email": user.email,
                "user_type": user.user_type
            },
            "refresh": str(refresh),
            "access": str(refresh.access_token)
        })

# PROFILE VIEW
class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user
