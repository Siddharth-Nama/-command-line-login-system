from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError('Username is required')
        user = self.model(username=username.lower(), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(username, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=150, unique=True, db_index=True)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)
    totp_secret = models.CharField(max_length=64, blank=True, default='')
    totp_enabled = models.BooleanField(default=False)
    totp_confirmed = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    class Meta:
        db_table = 'users'
        ordering = ['-date_joined']

    def __str__(self):
        return self.username

    def enable_totp(self, secret):
        self.totp_secret = secret
        self.totp_enabled = False
        self.totp_confirmed = False
        self.save(update_fields=['totp_secret', 'totp_enabled', 'totp_confirmed'])

    def confirm_totp(self):
        self.totp_enabled = True
        self.totp_confirmed = True
        self.save(update_fields=['totp_enabled', 'totp_confirmed'])

    def disable_totp(self):
        self.totp_secret = ''
        self.totp_enabled = False
        self.totp_confirmed = False
        self.save(update_fields=['totp_secret', 'totp_enabled', 'totp_confirmed'])

    def record_login(self):
        self.last_login = timezone.now()
        self.save(update_fields=['last_login'])
