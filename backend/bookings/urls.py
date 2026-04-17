from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BookingViewSet

router = DefaultRouter()
router.register(r"bookings", BookingViewSet, basename="booking")

owner_ground_bookings = BookingViewSet.as_view({
    "get": "owner_ground_bookings",
})

urlpatterns = [
    path("", include(router.urls)),
    path(
        "owner/grounds/<int:ground_id>/bookings/",
        owner_ground_bookings,
        name="owner-ground-bookings",
    ),
]