from datetime import datetime, timezone

import jwt

from app.access.security import create_access_token, get_current_user
from app.config import settings
from app.errors import ApiError


def test_demo_user_receives_bearer_token(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "demo@conciliador.local", "password": "Demo1234!"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 1800
    assert body["user"] == {"id": 1, "email": "demo@conciliador.local"}

    claims = jwt.decode(
        body["access_token"], settings.jwt_secret_key, algorithms=["HS256"]
    )
    assert claims["sub"] == "1"
    assert datetime.fromtimestamp(claims["exp"], timezone.utc) > datetime.now(
        timezone.utc
    )


def test_invalid_password_is_rejected_without_exposing_user(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "demo@conciliador.local", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_CREDENTIALS"
    assert response.json()["message"] == "Invalid email or password"
    assert "demo@conciliador.local" not in response.text


def test_unknown_email_has_the_same_rejection(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "unknown@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_CREDENTIALS"
    assert response.json()["message"] == "Invalid email or password"
    assert "unknown@example.com" not in response.text


def test_valid_token_resolves_active_user(demo_user):
    user = get_current_user(create_access_token(demo_user.id), _SessionForUser(demo_user))

    assert user.id == demo_user.id


def test_invalid_token_is_rejected(demo_user):
    try:
        get_current_user("not-a-jwt", _SessionForUser(demo_user))
    except ApiError as error:
        assert error.status_code == 401
        assert error.code == "INVALID_TOKEN"
    else:
        raise AssertionError("Invalid token was accepted")


class _SessionForUser:
    def __init__(self, user):
        self.user = user

    def get(self, model, user_id):
        return self.user if user_id == self.user.id else None
