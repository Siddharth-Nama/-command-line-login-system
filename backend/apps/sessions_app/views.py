from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import UserSession
from django.utils import timezone


class WhoAmIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        auth = JWTAuthentication()
        session = None

        try:
            validated = auth.authenticate(request)
            if validated:
                token = validated[1]
                jti = str(token['jti'])
                session = UserSession.get_active(jti)
                if session:
                    session.refresh()
        except Exception:
            pass

        data = {
            'username': user.username,
            'email': user.email,
            'date_joined': user.date_joined.isoformat(),
            'last_login': user.last_login.isoformat() if user.last_login else None,
            'mfa_enabled': user.totp_enabled and user.totp_confirmed,
            'session_expires_at': session.expires_at.isoformat() if session else None,
        }
        return Response(data)
