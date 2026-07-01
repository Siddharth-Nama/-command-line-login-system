from django.urls import path
from .views import RegisterView, LoginView, TOTPEnableView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('2fa/enable/', TOTPEnableView.as_view(), name='totp-enable'),
]
