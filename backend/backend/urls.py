from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),

    path("authapp/", include("authapp.urls")),
    path("api/auth/", include("authapp.urls")),

    path("api/", include("grounds.urls")),
    path("api/", include("bookings.urls")),
    path("api/payments/", include("payments.urls")),
    path("api/", include("chat.urls")),
    path("api/", include("connections.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)