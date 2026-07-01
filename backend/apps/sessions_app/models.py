from django.db import models
from django.utils import timezone
from django.conf import settings


class UserSession(models.Model):
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='sessions'
    )
    jti = models.CharField(max_length=255, unique=True, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    last_activity = models.DateTimeField(default=timezone.now)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'user_sessions'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.expires_at:
            timeout = settings.SESSION_TIMEOUT_MINUTES
            self.expires_at = timezone.now() + timezone.timedelta(minutes=timeout)
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    def refresh(self):
        timeout = settings.SESSION_TIMEOUT_MINUTES
        self.expires_at = timezone.now() + timezone.timedelta(minutes=timeout)
        self.last_activity = timezone.now()
        self.save(update_fields=['expires_at', 'last_activity'])

    def terminate(self):
        self.is_active = False
        self.save(update_fields=['is_active'])

    @classmethod
    def create_for_user(cls, user, jti, ip_address=None, user_agent=''):
        timeout = settings.SESSION_TIMEOUT_MINUTES
        return cls.objects.create(
            user=user,
            jti=jti,
            expires_at=timezone.now() + timezone.timedelta(minutes=timeout),
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @classmethod
    def get_active(cls, jti):
        try:
            session = cls.objects.get(jti=jti, is_active=True)
            if session.is_expired:
                session.terminate()
                return None
            return session
        except cls.DoesNotExist:
            return None
