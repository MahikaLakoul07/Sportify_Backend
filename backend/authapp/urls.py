from django.urls import path
from .views import RegisterPlayerView, LoginView, ProfileView

urlpatterns = [
    path('register/', RegisterPlayerView.as_view(), name='register-player'),
    path('login/', LoginView.as_view(), name='login'),
    path('profile/', ProfileView.as_view(), name='profile'),
]
