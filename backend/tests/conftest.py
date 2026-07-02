import pytest
from apps.accounts import views as account_views
from apps.sessions_app import views as session_views


@pytest.fixture(autouse=True)
def disable_throttling(monkeypatch):
    monkeypatch.setattr(account_views.LoginView, 'throttle_classes', [])
    monkeypatch.setattr(account_views.RegisterView, 'throttle_classes', [])
