import pytest
from django.urls import reverse
from rest_framework.test import APIClient
import pyotp
from apps.accounts.models import User


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(username='totpuser', password='SecurePass1!')


@pytest.fixture
def auth_client(client, user):
    login_url = reverse('login')
    resp = client.post(login_url, {'username': 'totpuser', 'password': 'SecurePass1!'}, format='json')
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")
    return client


@pytest.fixture
def enable_url():
    return reverse('totp-enable')


@pytest.fixture
def verify_url():
    return reverse('totp-verify')


@pytest.fixture
def disable_url():
    return reverse('totp-disable')


@pytest.fixture
def whoami_url():
    return reverse('whoami')


@pytest.mark.django_db
def test_enable_2fa_returns_secret_and_qr(auth_client, enable_url):
    response = auth_client.post(enable_url, format='json')
    assert response.status_code == 200
    assert 'secret' in response.data
    assert 'qr_code' in response.data
    assert response.data['qr_code'].startswith('data:image/png;base64,')


@pytest.mark.django_db
def test_enable_2fa_already_enabled(auth_client, enable_url, verify_url, user):
    auth_client.post(enable_url, format='json')
    user.refresh_from_db()
    code = pyotp.TOTP(user.totp_secret).now()
    auth_client.post(verify_url, {'code': code}, format='json')
    response = auth_client.post(enable_url, format='json')
    assert response.status_code == 400


@pytest.mark.django_db
def test_verify_2fa_success(auth_client, enable_url, verify_url, user):
    auth_client.post(enable_url, format='json')
    user.refresh_from_db()
    code = pyotp.TOTP(user.totp_secret).now()
    response = auth_client.post(verify_url, {'code': code}, format='json')
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.totp_enabled is True
    assert user.totp_confirmed is True


@pytest.mark.django_db
def test_verify_2fa_wrong_code(auth_client, enable_url, verify_url):
    auth_client.post(enable_url, format='json')
    response = auth_client.post(verify_url, {'code': '000000'}, format='json')
    assert response.status_code == 400


@pytest.mark.django_db
def test_disable_2fa_success(auth_client, enable_url, verify_url, disable_url, user):
    auth_client.post(enable_url, format='json')
    user.refresh_from_db()
    code = pyotp.TOTP(user.totp_secret).now()
    auth_client.post(verify_url, {'code': code}, format='json')
    user.refresh_from_db()
    code2 = pyotp.TOTP(user.totp_secret).now()
    response = auth_client.post(disable_url, {'password': 'SecurePass1!', 'code': code2}, format='json')
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.totp_enabled is False


@pytest.mark.django_db
def test_disable_2fa_wrong_password(auth_client, enable_url, verify_url, disable_url, user):
    auth_client.post(enable_url, format='json')
    user.refresh_from_db()
    code = pyotp.TOTP(user.totp_secret).now()
    auth_client.post(verify_url, {'code': code}, format='json')
    response = auth_client.post(disable_url, {'password': 'wrongpass', 'code': '000000'}, format='json')
    assert response.status_code == 401


@pytest.mark.django_db
def test_whoami_returns_user_data(auth_client, whoami_url):
    response = auth_client.get(whoami_url)
    assert response.status_code == 200
    assert response.data['username'] == 'totpuser'
    assert 'date_joined' in response.data
    assert 'mfa_enabled' in response.data
    assert 'session_expires_at' in response.data


@pytest.mark.django_db
def test_whoami_requires_auth(client, whoami_url):
    response = client.get(whoami_url)
    assert response.status_code == 401
