from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, FailedLoginAttempt


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'is_active', 'totp_enabled', 'date_joined', 'last_login')
    list_filter = ('is_active', 'is_staff', 'totp_enabled')
    search_fields = ('username', 'email')
    ordering = ('-date_joined',)
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Info', {'fields': ('email', 'date_joined', 'last_login')}),
        ('2FA', {'fields': ('totp_enabled', 'totp_confirmed', 'totp_secret')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2'),
        }),
    )
    readonly_fields = ('date_joined', 'last_login')


@admin.register(FailedLoginAttempt)
class FailedLoginAttemptAdmin(admin.ModelAdmin):
    list_display = ('username', 'ip_address', 'attempted_at')
    list_filter = ('username',)
    search_fields = ('username', 'ip_address')
    ordering = ('-attempted_at',)
