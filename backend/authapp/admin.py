from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


class CustomUserAdmin(UserAdmin):
    model = User

    # What to display in list view
    list_display = ("user_id", "username", "email", "phone", "user_type", "is_staff", "is_superuser")

    # Filters on right side
    list_filter = ("user_type", "is_staff", "is_superuser")

    # Search bar
    search_fields = ("username", "email", "phone")

    # Default ordering
    ordering = ("user_id",)

    # Field layout when editing user
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal Info", {"fields": ("email", "phone", "gender")}),
        ("Roles", {"fields": ("user_type",)}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
    )

    # Field layout when creating user
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "email", "phone", "user_type", "password1", "password2"),
        }),
    )


admin.site.register(User, CustomUserAdmin)