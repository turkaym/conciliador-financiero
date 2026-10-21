import os

import pytest
from fastapi.testclient import TestClient
from pwdlib import PasswordHash

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")

from app.database import get_db
from app.main import app
from app.models import User


class FakeSession:
    def __init__(self, user: User | None) -> None:
        self.user = user

    def scalar(self, statement: object) -> User | None:
        return self.user


@pytest.fixture(scope="session")
def demo_user() -> User:
    return User(
        id=1,
        email="demo@conciliador.local",
        password_hash=PasswordHash.recommended().hash("Demo1234!"),
        active=True,
    )


@pytest.fixture
def client(demo_user: User):
    def override_get_db():
        yield FakeSession(demo_user)

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
