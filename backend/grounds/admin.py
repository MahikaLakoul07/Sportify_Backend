from django.contrib import admin
from .models import Ground


@admin.register(Ground)
class GroundAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "location",
        "price_per_hour",
        "ground_size",
        "status",
        "owner",
        "created_at",
    )

    list_filter = ("status", "ground_size", "created_at")
    search_fields = ("name", "location", "owner__username")

    # ✅ This makes status editable directly from list page
    list_editable = ("status",)

    ordering = ("-created_at",)