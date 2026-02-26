from django.urls import path
from .views import EsewaInitiateView, EsewaSuccessView, EsewaFailureView

urlpatterns = [
    path("esewa/initiate/", EsewaInitiateView.as_view()),
    path("esewa/success/", EsewaSuccessView.as_view()),
    path("esewa/failure/", EsewaFailureView.as_view()),
]
