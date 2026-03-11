from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    GroundViewSet,
    OwnerMyGroundsView,
    GroundAvailabilityBulkUpsertView,
    GroundSlotsForDateView,
)

router = DefaultRouter()
router.register(r"grounds", GroundViewSet, basename="grounds")

urlpatterns = [
    path("", include(router.urls)),

    # owner grounds
    path("owner/grounds/", OwnerMyGroundsView.as_view(), name="owner-my-grounds"),

    # availability
    path("grounds/<int:pk>/availability/bulk/", GroundAvailabilityBulkUpsertView.as_view()),
    path("grounds/<int:pk>/slots/", GroundSlotsForDateView.as_view()),
]