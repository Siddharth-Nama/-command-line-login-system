from django.http import JsonResponse
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from apps.sessions_app.models import UserSession


class SessionTimeoutMiddleware:
    EXEMPT_PATHS = {
        '/api/auth/login/',
        '/api/auth/register/',
        '/api/health/',
        '/admin/',
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self._is_exempt(request.path):
            return self.get_response(request)

        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith('Bearer '):
            return self.get_response(request)

        authenticator = JWTAuthentication()
        try:
            validated = authenticator.authenticate(request)
            if validated is None:
                return self.get_response(request)
            _, token = validated
            jti = str(token['jti'])
            session = UserSession.get_active(jti)
            if session is None:
                return JsonResponse(
                    {'error': 'Session expired. Please log in again.', 'code': 'session_expired'},
                    status=401,
                )
        except (InvalidToken, TokenError):
            pass

        return self.get_response(request)

    def _is_exempt(self, path):
        return any(path.startswith(exempt) for exempt in self.EXEMPT_PATHS)
