from django.contrib import admin
from .models import UserSession


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'jti', 'is_active', 'created_at', 'expires_at', 'last_activity', 'ip_address')
    list_filter = ('is_active',)
    search_fields = ('user__username', 'jti', 'ip_address')
    ordering = ('-created_at',)
    readonly_fields = ('jti', 'created_at', 'last_activity')
