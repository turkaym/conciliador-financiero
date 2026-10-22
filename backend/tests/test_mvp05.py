import pytest
from fastapi.testclient import TestClient
from pwdlib import PasswordHash
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.access.security import create_access_token
from app.database import get_db
from app.main import app
from app.models import Base, DataSource, ImportTemplate, TemplateField, User


@pytest.fixture
def processing_client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all([
            User(id=1, email="demo@conciliador.local", password_hash=PasswordHash.recommended().hash("Demo1234!"), active=True),
            User(id=2, email="other@conciliador.local", password_hash=PasswordHash.recommended().hash("Other1234!"), active=True),
            DataSource(id=1, source_type="BANCO", code="BANCO_DEMO", name="Banco demo", active=True),
            DataSource(id=2, source_type="COMPROBANTES", code="COMPROBANTES_DEMO", name="Comprobantes demo", active=True),
            ImportTemplate(id=1, source_id=1, name="movimientos", template_type="MOVIMIENTO", version=1, active=True),
            ImportTemplate(id=2, source_id=2, name="comprobantes", template_type="COMPROBANTE", version=1, active=True),
        ])
        session.add_all([
            TemplateField(id=index, template_id=template_id, source_column=column, canonical_field=column)
            for template_id in (1, 2)
            for index, column in enumerate(("id_externo", "fecha", "monto", "moneda", "referencia", "clase"), template_id * 10)
        ])
        session.commit()

    def override_get_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client, engine
    app.dependency_overrides.clear()
    engine.dispose()


def _headers(user_id: int = 1) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


def _seed_pending(engine) -> None:
    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            INSERT INTO lote_carga
                (id, fuente_id, plantilla_id, plantilla_solicitada, usuario_id, tipo,
                 nombre_archivo, huella_archivo, contenido_archivo, estado, recibido_en)
            VALUES
                (1, 1, 1, '1', 1, 'MOVIMIENTO', 'bank.csv', X'01', X'01', 'PROCESADO', '2026-01-01 10:00:00'),
                (2, 2, 2, '2', 1, 'COMPROBANTE', 'receipts.csv', X'02', X'02', 'PROCESADO', '2026-01-01 10:00:00'),
                (3, 1, 1, '1', 2, 'MOVIMIENTO', 'other.csv', X'03', X'03', 'PROCESADO', '2026-01-01 10:00:00')
            """
        )
        connection.exec_driver_sql(
            """
            INSERT INTO registro_importado
                (id, lote_id, fuente_id, numero_fila, tipo, estado, id_externo,
                 clave_duplicado, datos_originales, creado_en)
            VALUES
                (1, 1, 1, 2, 'MOVIMIENTO', 'PENDIENTE', 'MOV-1', X'11', '{"referencia":"Alpha"}', '2026-01-02 10:00:00'),
                (2, 1, 1, 3, 'MOVIMIENTO', 'PENDIENTE', 'MOV-2', X'12', '{"referencia":"Beta"}', '2026-01-03 10:00:00'),
                (3, 2, 2, 2, 'COMPROBANTE', 'PENDIENTE', 'REC-1', X'13', '{"referencia":"Receipt"}', '2026-01-02 11:00:00'),
                (4, 3, 1, 2, 'MOVIMIENTO', 'PENDIENTE', 'OTHER-1', X'14', '{"referencia":"Private"}', '2026-01-02 12:00:00'),
                (5, 1, 1, 4, 'MOVIMIENTO', 'CONCILIADO', 'MOV-3', X'15', '{"referencia":"Matched"}', '2026-01-02 13:00:00'),
                (6, 2, 2, 3, 'COMPROBANTE', 'CONCILIADO', 'REC-2', X'16', '{"referencia":"Matched"}', '2026-01-02 14:00:00')
            """
        )
        connection.exec_driver_sql(
            """
            INSERT INTO movimiento_bancario
                (registro_id, date, amount, moneda, referencia_normalizada, es_credito)
            VALUES
                (1, '2026-01-10', 100.00, 'ARS', NULL, TRUE),
                (2, '2026-01-11', 200.00, 'ARS', NULL, TRUE),
                (4, '2026-01-12', 300.00, 'ARS', NULL, TRUE),
                (5, '2026-01-13', 400.00, 'ARS', NULL, TRUE)
            """
        )
        connection.exec_driver_sql(
            """
            INSERT INTO comprobante
                (registro_id, date, amount, moneda, referencia_normalizada, clase)
            VALUES
                (3, '2026-01-10', 100.00, 'ARS', NULL, 'VENTA'),
                (6, '2026-01-13', 400.00, 'ARS', NULL, 'VENTA')
            """
        )
        connection.exec_driver_sql(
            """
            INSERT INTO conciliacion
                (id, propuesta_id, movimiento_id, comprobante_id, estado, confirmada_por)
            VALUES (1, 1, 5, 6, 'ACTIVA', 1)
            """
        )


def test_pending_queries_filter_scope_date_and_page(processing_client):
    client, engine = processing_client
    _seed_pending(engine)

    response = client.get(
        "/api/v1/pending?type=MOVIMIENTO&from=2026-01-10&to=2026-01-11&page=1&page_size=1",
        headers=_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "page": 1,
        "page_size": 1,
        "total": 2,
        "items": [
            {
                "record_id": 1,
                "type": "MOVIMIENTO",
                "batch_id": 1,
                "external_id": "MOV-1",
                "date": "2026-01-10",
                "amount": "100.00",
                "currency": "ARS",
                "reference_original": "Alpha",
                "state": "PENDIENTE",
                "cause": "UNRECONCILED",
            }
        ],
    }

    second_page = client.get(
        "/api/v1/pending?type=MOVIMIENTO&page=2&page_size=1", headers=_headers()
    )
    assert second_page.json()["items"][0]["record_id"] == 2


def test_pending_queries_support_batch_source_state_and_empty_results(processing_client):
    client, engine = processing_client
    _seed_pending(engine)

    response = client.get(
        "/api/v1/pending?source_id=2&batch_id=2&state=PENDIENTE", headers=_headers()
    )
    assert response.status_code == 200
    assert [item["record_id"] for item in response.json()["items"]] == [3]
    assert client.get("/api/v1/pending?batch_id=3", headers=_headers()).status_code == 404

    empty = client.get("/api/v1/pending?from=2030-01-01", headers=_headers())
    assert empty.status_code == 200
    assert empty.json()["total"] == 0
    assert empty.json()["items"] == []


def test_pending_queries_reject_anonymous_and_hide_other_owner(processing_client):
    client, engine = processing_client
    _seed_pending(engine)

    assert client.get("/api/v1/pending").status_code == 401
    assert client.get("/api/v1/pending", headers=_headers()).json()["total"] == 3
    assert client.get("/api/v1/pending", headers=_headers(2)).json()["total"] == 1
