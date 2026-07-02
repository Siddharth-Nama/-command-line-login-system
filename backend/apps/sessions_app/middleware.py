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
            user_obj, token = validated

            # Try to resolve a session by jti claim when present. Some access
            # tokens (depending on SimpleJWT configuration) may not include a
            # `jti` claim. In tshat case, fall back to the user's most recent
            # actidve session. This prevents valid access tokens from being
            # rejected if the session was created using the refresh token's jti.
            jti = token.get('jti') if hasattr(token, 'get') else None
            session = None
            if jti:
                try:
                    session = UserSession.get_active(str(jti))
                except Exception:
                    session = None

            if session is None:
                # fall back to the latest active session for this user.
                try:
                    session = (
                        UserSession.objects.filter(user=user_obj, is_active=True)
                        .order_by('-created_at')
                        .first()
                    )
                    if session and session.is_expired:
                        session.terminate()
                        session = None
                except Exception:
                    session = None

            if session is None:
                return JsonResponse(
                    {'error': 'Session expired. Please log in again.', 'code': 'session_expired'},
                    status=401,
                )
        except (InvalidToken, TokenError):
            # Token validation failed — allow downstream handlers to respond.
            pass

        return self.get_response(request)

    def _is_exempt(self, path):
        return any(path.startswith(exempt) for exempt in self.EXEMPT_PATHS)
