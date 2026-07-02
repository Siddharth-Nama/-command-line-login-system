from django.urls import path
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView,
    LoginView,
    LogoutView,
    TOTPEnableView,
    TOTPVerifyView,
    TOTPDisableView,
)

class TokenRefreshAllowAnyView(TokenRefreshView):
    permission_classes = [AllowAny]

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshAllowAnyView.as_view(), name='token_refresh'),
    path('2fa/enable/', TOTPEnableView.as_view(), name='totp-enable'),
    path('2fa/verify/', TOTPVerifyView.as_view(), name='totp-verify'),
    path('2fa/disable/', TOTPDisableView.as_view(), name='totp-disable'),
]
