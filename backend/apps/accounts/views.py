from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.utils import timezone
import pyotp
import qrcode
import io
import base64

from .serializers import RegisterSerializer, UserDetailSerializer
from .models import User, FailedLoginAttempt
from .throttles import AuthRateThrottle
from apps.sessions_app.models import UserSession


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def generate_qr_base64(totp_uri):
    img = qrcode.make(totp_uri)
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return base64.b64encode(buffer.getvalue()).decode('utf-8')


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


class TOTPEnableView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if user.totp_enabled and user.totp_confirmed:
            return Response(
                {'error': '2FA is already enabled. Disable it first.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        secret = pyotp.random_base32()
        user.enable_totp(secret)

        from django.conf import settings
        totp = pyotp.TOTP(secret)
        uri = totp.provisioning_uri(name=user.username, issuer_name=settings.TOTP_ISSUER_NAME)
        qr_base64 = generate_qr_base64(uri)

        return Response(
            {
                'secret': secret,
                'qr_code': f'data:image/png;base64,{qr_base64}',
                'message': 'Scan the QR code with Google Authenticator then call verify-2fa to confirm.',
            },
            status=status.HTTP_200_OK,
        )


class TOTPVerifyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        code = request.data.get('code', '').strip()

        if not code:
            return Response({'error': 'TOTP code is required.'}, status=status.HTTP_400_BAD_REQUEST)

        if not user.totp_secret:
            return Response(
                {'error': 'Enable 2FA first before verifying.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user.totp_confirmed:
            return Response({'error': '2FA is already confirmed.'}, status=status.HTTP_400_BAD_REQUEST)

        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(code, valid_window=1):
            return Response({'error': 'Invalid code. Try again.'}, status=status.HTTP_400_BAD_REQUEST)

        user.confirm_totp()
        return Response(
            {'message': '2FA enabled successfully. Future logins will require a TOTP code.'},
            status=status.HTTP_200_OK,
        )


class TOTPDisableView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        code = request.data.get('code', '').strip()
        password = request.data.get('password', '')

        if not user.totp_enabled:
            return Response({'error': '2FA is not enabled.'}, status=status.HTTP_400_BAD_REQUEST)

        if not password:
            return Response({'error': 'Password is required to disable 2FA.'}, status=status.HTTP_400_BAD_REQUEST)

        if not user.check_password(password):
            return Response({'error': 'Incorrect password.'}, status=status.HTTP_401_UNAUTHORIZED)

        if user.totp_confirmed:
            if not code:
                return Response({'error': 'Current TOTP code required.'}, status=status.HTTP_400_BAD_REQUEST)
            totp = pyotp.TOTP(user.totp_secret)
            if not totp.verify(code, valid_window=1):
                return Response({'error': 'Invalid TOTP code.'}, status=status.HTTP_401_UNAUTHORIZED)

        user.disable_totp()
        return Response(
            {'message': '2FA has been disabled.'},
            status=status.HTTP_200_OK,
        )
