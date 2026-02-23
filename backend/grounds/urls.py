# grounds/urls.py
from rest_framework.routers import DefaultRouter
from .views import GroundViewSet

router = DefaultRouter()
router.register(r"grounds", GroundViewSet, basename="grounds")

urlpatterns = router.urls