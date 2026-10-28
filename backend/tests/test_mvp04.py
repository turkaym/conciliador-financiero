from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pwdlib import PasswordHash
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.access.security import create_access_token
from app.database import get_db
from app.main import app
from app.models import Base, DataSource, ImportTemplate, ImportedRecord, TemplateField, User, BankMovement, Receipt


FIXTURES = Path(__file__).parents[2] / "docs" / "segunda-entrega" / "csv" / "fixtures"


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
        movement_columns = [("id_externo", "TEXTO", False), ("fecha", "FECHA", True), ("monto", "DECIMAL", True), ("moneda", "MONEDA", True), ("referencia", "TEXTO", False), ("tipo_movimiento", "CATEGORIA", True)]
        receipt_columns = [("id_externo", "TEXTO", False), ("fecha", "FECHA", True), ("monto", "DECIMAL", True), ("moneda", "MONEDA", True), ("referencia", "TEXTO", False), ("clase", "CATEGORIA", True)]
        session.add_all([
            TemplateField(id=index, template_id=1, source_column=column, canonical_field=column, data_type=data_type, required=required)
            for index, (column, data_type, required) in enumerate(reversed(movement_columns), 1)
        ] + [
            TemplateField(id=index + 10, template_id=2, source_column=column, canonical_field=column, data_type=data_type, required=required)
            for index, (column, data_type, required) in enumerate(reversed(receipt_columns), 1)
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


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(1)}"}


def _submit(client: TestClient, template_id: int, batch_type: str, name: str) -> dict:
    content = (FIXTURES / name).read_bytes()
    response = client.post("/api/v1/batches", headers=_headers(), data={"source_id": str(template_id), "template_id": str(template_id), "type": batch_type}, files={"file": (name, content, "text/csv")})
    assert response.status_code == 202
    return response.json()


def test_valid_movement_and_receipt_rows_persist(processing_client):
    client, engine = processing_client
    catalog = client.get("/api/v1/catalog/templates?source_id=1&type=MOVIMIENTO", headers=_headers())
    receipt_catalog = client.get("/api/v1/catalog/templates?source_id=2&type=COMPROBANTE", headers=_headers())
    movement = _submit(client, 1, "MOVIMIENTO", "movimientos-validos.csv")
    receipt = _submit(client, 2, "COMPROBANTE", "comprobantes-validos.csv")
    assert catalog.json()["items"][0]["columns"] == [
        "id_externo", "fecha", "monto", "moneda", "referencia", "tipo_movimiento"
    ]
    assert receipt_catalog.json()["items"][0]["columns"] == [
        "id_externo", "fecha", "monto", "moneda", "referencia", "clase"
    ]
    assert movement["status"] == "PROCESADO"
    assert movement["totals"] == {"total_rows": 3, "valid_rows": 3, "invalid_rows": 0}
    assert receipt["status"] == "PROCESADO"
    with Session(engine) as session:
        assert len(session.scalars(select(BankMovement)).all()) == 3
        assert len(session.scalars(select(Receipt)).all()) == 3
        assert len(session.scalars(select(ImportedRecord)).all()) == 6


@pytest.mark.parametrize("batch_type,template_id,name,codes", [
    ("MOVIMIENTO", 1, "movimientos-invalidos.csv", ["FECHA_INVALIDA", "MONTO_NO_POSITIVO", "MONEDA_NO_ADMITIDA", "TIPO_MOVIMIENTO_NO_ADMITIDO"]),
    ("COMPROBANTE", 2, "comprobantes-invalidos.csv", ["FECHA_INVALIDA", "MONTO_NO_POSITIVO", "MONEDA_NO_ADMITIDA", "CLASE_NO_ADMITIDA"]),
])
def test_invalid_rows_are_reported_in_deterministic_order(processing_client, batch_type, template_id, name, codes):
    client, engine = processing_client
    batch = _submit(client, template_id, batch_type, name)
    assert batch["status"] == "PROCESADO_SIN_VALIDOS"
    assert batch["totals"] == {"total_rows": 3, "valid_rows": 0, "invalid_rows": 3}
    errors = client.get(f"/api/v1/batches/{batch['id']}/errors", headers=_headers())
    assert [item["code"] for item in errors.json()["items"]] == codes
    with Session(engine) as session:
        assert session.scalars(select(BankMovement if batch_type == "MOVIMIENTO" else Receipt)).all() == []


@pytest.mark.parametrize("batch_type,template_id,name", [
    ("MOVIMIENTO", 1, "movimientos-estructura-invalida.csv"),
    ("COMPROBANTE", 2, "comprobantes-estructura-invalida.csv"),
])
def test_incompatible_headers_fail_without_rows(processing_client, batch_type, template_id, name):
    client, engine = processing_client
    batch = _submit(client, template_id, batch_type, name)
    assert batch["status"] == "FALLIDO"
    errors = client.get(f"/api/v1/batches/{batch['id']}/errors", headers=_headers()).json()
    assert errors["items"][0]["code"] == "CABECERA_INCOMPATIBLE"
    with Session(engine) as session:
        assert session.scalars(select(ImportedRecord)).all() == []


def test_duplicate_rows_and_owner_safe_errors(processing_client):
    client, _engine = processing_client
    batch = _submit(client, 1, "MOVIMIENTO", "movimientos-duplicados.csv")
    assert batch["status"] == "PROCESADO_CON_ERRORES"
    assert batch["totals"] == {"total_rows": 4, "valid_rows": 2, "invalid_rows": 2}
    errors = client.get(f"/api/v1/batches/{batch['id']}/errors", headers=_headers()).json()
    assert [item["code"] for item in errors["items"]] == ["ID_EXTERNO_DUPLICADO", "HUELLA_FILA_DUPLICADA"]
    other = {"Authorization": f"Bearer {create_access_token(2)}"}
    assert client.get(f"/api/v1/batches/{batch['id']}/errors", headers=other).status_code == 404
