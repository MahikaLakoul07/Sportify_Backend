from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import GroundViewSet, GroundAvailabilityBulkUpsertView, GroundSlotsForDateView

router = DefaultRouter()
router.register(r"grounds", GroundViewSet, basename="grounds")

urlpatterns = [
    path("", include(router.urls)),
    path("grounds/<int:pk>/availability/bulk/", GroundAvailabilityBulkUpsertView.as_view()),
    path("grounds/<int:pk>/slots/", GroundSlotsForDateView.as_view()),
]
