from django.urls import path
from .views import (
    EsewaInitiateView,
    EsewaMockSuccessView,
    EsewaSuccessView,
    EsewaFailureView,
)

urlpatterns = [
    path("esewa/initiate/", EsewaInitiateView.as_view(), name="esewa-initiate"),
    path("esewa/mock-success/", EsewaMockSuccessView.as_view(), name="esewa-mock-success"),
    path("esewa/success/", EsewaSuccessView.as_view(), name="esewa-success"),
    path("esewa/failure/", EsewaFailureView.as_view(), name="esewa-failure"),
]