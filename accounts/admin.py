from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Trip, CompanionRequest


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    ordering = ("email",)
    list_display = ("email", "first_name", "role", "is_staff")
    search_fields = ("email", "first_name")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Личная информация", {"fields": ("first_name", "last_name", "role")}),
        ("Права", {"fields": ("is_active", "is_staff", "is_superuser")}),
    )
    add_fieldsets = (
        (None, {
            "fields": ("email", "password1", "password2"),
        }),
    )


admin.site.register(Trip)
admin.site.register(CompanionRequest)
