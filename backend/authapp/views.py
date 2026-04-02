from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import (
    LoginSerializer,
    PlayerDetailSerializer,
    PlayerListSerializer,
    ProfileSerializer,
    RegisterSerializer,
)

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

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
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                },
                "refresh": str(refresh),
                "access": access_token,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]

        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        response = Response(
            {
                "user": {
                    "user_id": user.user_id,
                    "username": user.username,
                    "email": user.email,
                    "phone": user.phone,
                    "user_type": user.user_type,
                    "gender": user.gender,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                },
                "refresh": str(refresh),
                "access": access_token,
            },
            status=status.HTTP_200_OK,
        )

        response.set_cookie("access", access_token, httponly=True, max_age=3600)
        response.set_cookie("refresh", str(refresh), httponly=True, max_age=7 * 24 * 3600)
        return response


class ProfileView(generics.RetrieveAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class PlayerListView(generics.ListAPIView):
    serializer_class = PlayerListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        search = self.request.query_params.get("search", "").strip()

        qs = User.objects.filter(user_type=User.UserType.PLAYER).exclude(user_id=user.user_id)

        if search:
            qs = qs.filter(
                Q(username__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(email__icontains=search)
                | Q(phone__icontains=search)
            )

        return qs.order_by("username")


class PlayerDetailView(generics.RetrieveAPIView):
    serializer_class = PlayerDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "user_id"

    def get_queryset(self):
        return User.objects.filter(user_type=User.UserType.PLAYER)