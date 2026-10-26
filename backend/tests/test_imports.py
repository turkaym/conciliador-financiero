import pytest
from fastapi.testclient import TestClient
from pwdlib import PasswordHash
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.main import app
from app.access.security import create_access_token
from app.models import Base, DataSource, ImportTemplate, TemplateField, User


@pytest.fixture
def catalog_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all(
            [
                User(
                    id=1,
                    email="demo@conciliador.local",
                    password_hash=PasswordHash.recommended().hash("Demo1234!"),
                    active=True,
                ),
                User(
                    id=2,
                    email="other@conciliador.local",
                    password_hash=PasswordHash.recommended().hash("Other1234!"),
                    active=True,
                ),
                DataSource(id=1, source_type="BANCO", code="BANCO_DEMO", name="Banco demo", active=True),
                DataSource(
                    id=2,
                    source_type="COMPROBANTES",
                    code="COMPROBANTES_DEMO",
                    name="Comprobantes demo",
                    active=True,
                ),
                ImportTemplate(
                    id=1,
                    source_id=1,
                    name="movimientos",
                    template_type="MOVIMIENTO",
                    version=1,
                    active=True,
                ),
                ImportTemplate(
                    id=2,
                    source_id=2,
                    name="comprobantes",
                    template_type="COMPROBANTE",
                    version=1,
                    active=True,
                ),
            ]
        )
        session.add_all(
            [
                TemplateField(id=1, template_id=1, source_column="id_externo", canonical_field="id_externo"),
                TemplateField(id=2, template_id=1, source_column="fecha", canonical_field="fecha"),
                TemplateField(id=3, template_id=2, source_column="id_externo", canonical_field="id_externo"),
            ]
        )
        session.commit()

    def override_get_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    engine.dispose()


def _auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "demo@conciliador.local", "password": "Demo1234!"},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_authenticated_user_can_list_catalogs(catalog_client: TestClient):
    headers = _auth_headers(catalog_client)

    sources = catalog_client.get("/api/v1/catalog/sources?type=MOVIMIENTO", headers=headers)
    templates = catalog_client.get(
        "/api/v1/catalog/templates?source_id=1&type=MOVIMIENTO", headers=headers
    )

    assert sources.status_code == 200
    assert sources.json()["items"] == [
        {"id": 1, "code": "BANCO_DEMO", "name": "Banco demo", "type": "MOVIMIENTO"}
    ]
    assert templates.status_code == 200
    assert templates.json()["items"][0] == {
        "id": 1,
        "name": "movimientos",
        "type": "MOVIMIENTO",
        "version": 1,
        "columns": ["id_externo", "fecha"],
    }


@pytest.fixture
def approved_schema_catalog_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    User.__table__.create(engine)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE fuente_datos (
                    id BIGINT PRIMARY KEY,
                    tipo_origen VARCHAR(20) NOT NULL,
                    codigo VARCHAR(50) NOT NULL,
                    nombre VARCHAR(120) NOT NULL,
                    activa BOOLEAN NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO usuario (id, email, password_hash, activo)
                VALUES (1, 'demo@conciliador.local', :password_hash, TRUE)
                """
            ),
            {"password_hash": PasswordHash.recommended().hash("Demo1234!")},
        )
        connection.execute(
            text(
                """
                INSERT INTO fuente_datos (id, tipo_origen, codigo, nombre, activa)
                VALUES (1, 'BANCO', 'BANCO_DEMO', 'Banco demo', TRUE)
                """
            )
        )

    def override_get_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    engine.dispose()


def test_catalog_source_query_uses_approved_codigo_column(
    approved_schema_catalog_client: TestClient,
):
    headers = _auth_headers(approved_schema_catalog_client)

    response = approved_schema_catalog_client.get(
        "/api/v1/catalog/sources?type=MOVIMIENTO", headers=headers
    )

    assert response.status_code == 200
    assert response.json()["items"] == [
        {"id": 1, "code": "BANCO_DEMO", "name": "Banco demo", "type": "MOVIMIENTO"}
    ]


def test_batch_submission_is_processed_and_inspectable(catalog_client: TestClient):
    headers = _auth_headers(catalog_client)
    content = b"id_externo,unknown\nMOV-1,2026-05-01\n"

    submitted = catalog_client.post(
        "/api/v1/batches",
        headers=headers,
        data={"source_id": "1", "template_id": "1", "type": "MOVIMIENTO"},
        files={"file": ("movimientos.csv", content, "text/csv")},
    )

    assert submitted.status_code == 202
    body = submitted.json()
    assert body["status"] == "FALLIDO"
    assert body["file_name"] == "movimientos.csv"
    assert body["requested_template_id"] == 1
    assert body["totals"] == {"total_rows": 0, "valid_rows": 0, "invalid_rows": 0}

    inspected = catalog_client.get(f"/api/v1/batches/{body['id']}", headers=headers)
    assert inspected.status_code == 200
    assert inspected.json()["id"] == body["id"]
    assert inspected.json()["template"] == {"id": 1, "name": "movimientos", "version": 1}


def test_catalog_and_batch_endpoints_reject_unauthorized_or_malformed_requests(
    catalog_client: TestClient,
):
    assert catalog_client.get("/api/v1/catalog/sources").status_code == 401
    assert catalog_client.get("/api/v1/batches/1").status_code == 401

    headers = _auth_headers(catalog_client)
    invalid_type = catalog_client.get(
        "/api/v1/catalog/sources?type=UNKNOWN", headers=headers
    )
    missing_file = catalog_client.post(
        "/api/v1/batches",
        headers=headers,
        data={"source_id": "1", "template_id": "1", "type": "MOVIMIENTO"},
    )

    assert invalid_type.status_code == 400
    assert invalid_type.json()["code"] == "INVALID_SOURCE_TYPE"
    assert missing_file.status_code == 400


def test_batch_inspection_is_scoped_to_the_authenticated_owner(catalog_client: TestClient):
    headers = _auth_headers(catalog_client)
    submitted = catalog_client.post(
        "/api/v1/batches",
        headers=headers,
        data={"source_id": "1", "template_id": "1", "type": "MOVIMIENTO"},
        files={"file": ("owned.csv", b"id_externo\nMOV-1\n", "text/csv")},
    )
    batch_id = submitted.json()["id"]

    other_headers = {
        "Authorization": f"Bearer {create_access_token(2)}",
    }
    response = catalog_client.get(f"/api/v1/batches/{batch_id}", headers=other_headers)

    assert response.status_code == 404
    assert response.json()["code"] == "BATCH_NOT_FOUND"
