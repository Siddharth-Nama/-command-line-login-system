import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from apps.accounts.models import User, FailedLoginAttempt


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(username='loginuser', password='StrongPass1!')


@pytest.fixture
def login_url():
    return reverse('login')


@pytest.mark.django_db
def test_login_success(client, user, login_url):
    response = client.post(login_url, {'username': 'loginuser', 'password': 'StrongPass1!'}, format='json')
    assert response.status_code == 200
    assert 'access' in response.data
    assert 'refresh' in response.data
    assert 'session_expires_at' in response.data


@pytest.mark.django_db
def test_login_wrong_password(client, user, login_url):
    response = client.post(login_url, {'username': 'loginuser', 'password': 'WrongPass!'}, format='json')
    assert response.status_code == 401
    assert 'attempts_remaining' in response.data


@pytest.mark.django_db
def test_login_missing_fields(client, login_url):
    response = client.post(login_url, {}, format='json')
    assert response.status_code == 400


@pytest.mark.django_db
def test_login_nonexistent_user(client, login_url):
    response = client.post(login_url, {'username': 'nobody', 'password': 'anything'}, format='json')
    assert response.status_code == 401


@pytest.mark.django_db
def test_login_records_failed_attempts(client, user, login_url):
    for _ in range(3):
        client.post(login_url, {'username': 'loginuser', 'password': 'wrong'}, format='json')
    count = FailedLoginAttempt.objects.filter(username='loginuser').count()
    assert count == 3


@pytest.mark.django_db
def test_login_lockout_after_five_failures(client, user, login_url):
    for _ in range(5):
        client.post(login_url, {'username': 'loginuser', 'password': 'wrong'}, format='json')
    response = client.post(login_url, {'username': 'loginuser', 'password': 'StrongPass1!'}, format='json')
    assert response.status_code == 429
    assert 'retry_after_seconds' in response.data


@pytest.mark.django_db
def test_login_clears_attempts_on_success(client, user, login_url):
    for _ in range(2):
        client.post(login_url, {'username': 'loginuser', 'password': 'wrong'}, format='json')
    client.post(login_url, {'username': 'loginuser', 'password': 'StrongPass1!'}, format='json')
    count = FailedLoginAttempt.objects.filter(username='loginuser').count()
    assert count == 0


@pytest.mark.django_db
def test_login_inactive_user(client, login_url):
    inactive = User.objects.create_user(username='inactiveuser', password='Pass12345!')
    inactive.is_active = False
    inactive.save()
    from django.test import override_settings
    with override_settings(AUTHENTICATION_BACKENDS=['django.contrib.auth.backends.ModelBackend']):
        response = client.post(login_url, {'username': 'inactiveuser', 'password': 'Pass12345!'}, format='json')
    assert response.status_code in (401, 403)


@pytest.mark.django_db
def test_login_updates_last_login(client, user, login_url):
    assert user.last_login is None
    client.post(login_url, {'username': 'loginuser', 'password': 'StrongPass1!'}, format='json')
    user.refresh_from_db()
    assert user.last_login is not None
