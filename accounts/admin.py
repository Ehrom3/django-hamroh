from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Trip, CompanionRequest

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Дополнительно', {'fields': ('role',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Дополнительно', {'fields': ('role',)}),
    )


admin.site.register(Trip)

admin.site.register(CompanionRequest)
