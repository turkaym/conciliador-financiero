from datetime import datetime, timezone

import jwt

from app.config import settings


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
