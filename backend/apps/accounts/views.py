from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.utils import timezone
import pyotp

from .serializers import RegisterSerializer, UserDetailSerializer
from .models import User, FailedLoginAttempt
from .throttles import AuthRateThrottle
from apps.sessions_app.models import UserSession


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        user = serializer.save()
        return Response(
            {
                'message': f'Account created for {user.username}.',
                'user': UserDetailSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        username = request.data.get('username', '').lower().strip()
        password = request.data.get('password', '')
        totp_code = request.data.get('totp_code', '').strip()
        ip = get_client_ip(request)

        if not username or not password:
            return Response(
                {'error': 'Username and password are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if FailedLoginAttempt.is_locked(username):
            remaining = FailedLoginAttempt.lockout_remaining_seconds(username)
            return Response(
                {
                    'error': 'Account locked due to too many failed attempts.',
                    'retry_after_seconds': remaining,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        user = authenticate(request, username=username, password=password)

        if user is None:
            FailedLoginAttempt.record(username, ip)
            remaining_attempts = 5 - FailedLoginAttempt.objects.filter(
                username=username,
                attempted_at__gte=timezone.now() - timezone.timedelta(minutes=15),
            ).count()
            return Response(
                {
                    'error': 'Invalid credentials.',
                    'attempts_remaining': max(0, remaining_attempts),
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.is_active:
            return Response({'error': 'Account is disabled.'}, status=status.HTTP_403_FORBIDDEN)

        if user.totp_enabled and user.totp_confirmed:
            if not totp_code:
                return Response(
                    {'error': 'TOTP code required.', 'requires_totp': True},
                    status=status.HTTP_200_OK,
                )
            totp = pyotp.TOTP(user.totp_secret)
            if not totp.verify(totp_code, valid_window=1):
                FailedLoginAttempt.record(username, ip)
                return Response(
                    {'error': 'Invalid TOTP code.'},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

        FailedLoginAttempt.clear(username)
        user.record_login()

        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

        jti = str(refresh['jti'])
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        session = UserSession.create_for_user(user, jti, ip, user_agent)

        return Response(
            {
                'access': str(access),
                'refresh': str(refresh),
                'user': UserDetailSerializer(user).data,
                'session_expires_at': session.expires_at.isoformat(),
            },
            status=status.HTTP_200_OK,
        )
