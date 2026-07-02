import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from apps.accounts.models import User


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def register_url():
    return reverse('register')


@pytest.mark.django_db
def test_register_success(client, register_url):
    payload = {
        'username': 'testuser',
        'password': 'SecurePass123!',
        'password_confirm': 'SecurePass123!',
    }
    response = client.post(register_url, payload, format='json')
    assert response.status_code == 201
    assert response.data['user']['username'] == 'testuser'
    assert User.objects.filter(username='testuser').exists()


@pytest.mark.django_db
def test_register_duplicate_username(client, register_url):
    User.objects.create_user(username='existing', password='Pass12345!')
    payload = {
        'username': 'existing',
        'password': 'AnotherPass1!',
        'password_confirm': 'AnotherPass1!',
    }
    response = client.post(register_url, payload, format='json')
    assert response.status_code == 400
    assert 'username' in response.data


@pytest.mark.django_db
def test_register_password_mismatch(client, register_url):
    payload = {
        'username': 'newuser',
        'password': 'Pass12345!',
        'password_confirm': 'DifferentPass!',
    }
    response = client.post(register_url, payload, format='json')
    assert response.status_code == 400


@pytest.mark.django_db
def test_register_short_username(client, register_url):
    payload = {
        'username': 'ab',
        'password': 'Pass12345!',
        'password_confirm': 'Pass12345!',
    }
    response = client.post(register_url, payload, format='json')
    assert response.status_code == 400


@pytest.mark.django_db
def test_register_missing_fields(client, register_url):
    response = client.post(register_url, {}, format='json')
    assert response.status_code == 400


@pytest.mark.django_db
def test_register_username_stored_lowercase(client, register_url):
    payload = {
        'username': 'MixedCase',
        'password': 'SecurePass123!',
        'password_confirm': 'SecurePass123!',
    }
    response = client.post(register_url, payload, format='json')
    assert response.status_code == 201
    assert response.data['user']['username'] == 'mixedcase'
