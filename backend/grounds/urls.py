from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    GroundViewSet,
    OwnerMyGroundsView,
    GroundAvailabilityBulkUpsertView,
    GroundSlotsForDateView,
    OwnerGroundDetailUpdateView,
)

router = DefaultRouter()
router.register(r"grounds", GroundViewSet, basename="grounds")

urlpatterns = [
    path("", include(router.urls)),

    # owner grounds
    path("owner/grounds/", OwnerMyGroundsView.as_view(), name="owner-my-grounds"),
    path("owner/grounds/<int:pk>/edit/", OwnerGroundDetailUpdateView.as_view(), name="owner-ground-edit"),

    # availability
    path(
        "grounds/<int:pk>/availability/bulk/",
        GroundAvailabilityBulkUpsertView.as_view(),
        name="ground-availability-bulk",
    ),
    path(
        "grounds/<int:pk>/slots/",
        GroundSlotsForDateView.as_view(),
        name="ground-slots-for-date",
    ),
]