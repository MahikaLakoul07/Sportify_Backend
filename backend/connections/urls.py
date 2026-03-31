from rest_framework.routers import DefaultRouter
from .views import ConnectionViewSet

router = DefaultRouter()
router.register(r"connections", ConnectionViewSet, basename="connections")

urlpatterns = router.urls