from django.urls import path
from .views import GroundListCreateView, GroundDetailView

urlpatterns = [
    path("", GroundListCreateView.as_view(), name="ground-list-create"),
    path("<int:pk>/", GroundDetailView.as_view(), name="ground-detail"),
]
