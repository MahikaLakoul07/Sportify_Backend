from django.urls import path
from .views import (
    LoginView,
    PlayerDetailView,
    PlayerListView,
    ProfileView,
    RegisterView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("profile/", ProfileView.as_view(), name="profile"),

    path("players/", PlayerListView.as_view(), name="players-list"),
    path("players/<int:user_id>/", PlayerDetailView.as_view(), name="player-detail"),
]