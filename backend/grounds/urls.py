from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import GroundViewSet, GroundAvailabilityBulkUpsertView

router = DefaultRouter()
router.register(r"grounds", GroundViewSet, basename="grounds")

urlpatterns = router.urls + [
    path(
        "grounds/<int:pk>/availability/bulk/",
        GroundAvailabilityBulkUpsertView.as_view(),
        name="ground-availability-bulk",
    ),
]