from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from pwdlib import PasswordHash
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.access.security import create_access_token
from app.database import get_db
from app.main import app
from app.models import (
    Base,
    BankMovement,
    DataSource,
    EventHistory,
    ImportBatch,
    ImportedRecord,
    Receipt,
    Reconciliation,
    ReconciliationProposal,
    User,
)


def make_engine():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return engine


def seed_proposal(db: Session, owner_id: int = 1, movement_status: str = "CON_PROPUESTAS") -> None:
    db.add_all([
        User(id=owner_id, email=f"user{owner_id}@example.com", password_hash=PasswordHash.recommended().hash("secret"), active=True),
        DataSource(id=owner_id, source_type="BANCO", code=f"bank-{owner_id}", name="Bank", active=True),
        DataSource(id=owner_id + 10, source_type="COMPROBANTES", code=f"receipt-{owner_id}", name="Receipt", active=True),
        ImportBatch(id=owner_id, source_id=owner_id, user_id=owner_id, batch_type="MOVIMIENTO", file_name="m.csv", file_hash=bytes([owner_id]), file_content=b"m", status="PROCESADO", requested_template="1"),
        ImportBatch(id=owner_id + 10, source_id=owner_id + 10, user_id=owner_id, batch_type="COMPROBANTE", file_name="r.csv", file_hash=bytes([owner_id + 10]), file_content=b"r", status="PROCESADO", requested_template="2"),
        ImportedRecord(id=owner_id, batch_id=owner_id, source_id=owner_id, row_number=2, record_type="MOVIMIENTO", status=movement_status, duplicate_key=bytes([owner_id]), original_data={"referencia": "invoice"}),
        ImportedRecord(id=owner_id + 10, batch_id=owner_id + 10, source_id=owner_id + 10, row_number=2, record_type="COMPROBANTE", status=movement_status, duplicate_key=bytes([owner_id + 10]), original_data={"referencia": "invoice"}),
        BankMovement(record_id=owner_id, date=date(2026, 1, 1), amount=Decimal("100.00"), currency="ARS", is_credit=True),
        Receipt(record_id=owner_id + 10, date=date(2026, 1, 2), amount=Decimal("100.00"), currency="ARS", category="VENTA"),
        ReconciliationProposal(id=owner_id, movement_id=owner_id, receipt_id=owner_id + 10, status="GENERADA", normalizer_version="ref-nfkd-v1", rule_version="match-v1", evaluation_fingerprint=bytes([owner_id]) * 32, origin_type="LOTE", origin_batch_id=owner_id, reference_score=Decimal("1"), exact_match=True, day_difference=1, explanation={"movement_normalized": "INVOICE", "receipt_normalized": "INVOICE", "movement_tokens": ["INVOICE"], "receipt_tokens": ["INVOICE"]}),
    ])


def client_for(engine, user_id: int):
    def override_get_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    client.headers["Authorization"] = f"Bearer {create_access_token(user_id)}"
    return client


def test_confirm_is_atomic_and_creates_history_and_detail():
    engine = make_engine()
    with Session(engine) as db:
        seed_proposal(db)
        db.commit()

    client = client_for(engine, 1)
    response = client.post("/api/v1/proposals/1/confirm", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["proposal"]["status"] == "CONFIRMADA"
    assert body["reconciliation"]["status"] == "ACTIVA"
    assert client.post("/api/v1/proposals/1/confirm", json={}).status_code == 409

    with Session(engine) as db:
        assert {row.status for row in db.scalars(select(ImportedRecord)).all()} == {"CONCILIADO"}
        assert db.scalar(select(Reconciliation).where(Reconciliation.id == 1)).status == "ACTIVA"
        assert db.scalar(select(EventHistory).where(EventHistory.event_type == "PROPUESTA_CONFIRMADA")) is not None
    detail = client.get("/api/v1/reconciliations/1")
    assert detail.status_code == 200
    assert detail.json()["proposal_id"] == 1
    history = client.get("/api/v1/history", params={"event_type": "PROPUESTA_CONFIRMADA"})
    assert history.status_code == 200
    assert history.json()["total"] == 1
    app.dependency_overrides.clear()
    engine.dispose()


def test_confirm_flushes_decision_before_postgresql_trigger_style_reconciliation_insert():
    engine = make_engine()
    with Session(engine) as db:
        seed_proposal(db)
        db.commit()
        db.execute(text("""
            CREATE TRIGGER preparar_conciliacion_activa
            BEFORE INSERT ON conciliacion
            WHEN NEW.estado = 'ACTIVA'
             AND NOT EXISTS (
                 SELECT 1
                 FROM propuesta_conciliacion
                 WHERE id = NEW.propuesta_id
                   AND movimiento_id = NEW.movimiento_id
                   AND comprobante_id = NEW.comprobante_id
                   AND estado = 'CONFIRMADA'
             )
            BEGIN
                SELECT RAISE(ABORT, 'conciliacion activa requiere propuesta confirmada para la misma pareja');
            END
        """))
        db.commit()

    client = client_for(engine, 1)
    response = client.post("/api/v1/proposals/1/confirm", json={})
    assert response.status_code == 200
    assert response.json()["reconciliation"]["status"] == "ACTIVA"
    with Session(engine) as db:
        assert db.get(ReconciliationProposal, 1).status == "CONFIRMADA"
        assert db.get(Reconciliation, 1).status == "ACTIVA"
    app.dependency_overrides.clear()
    engine.dispose()


def test_reject_requires_reason_preserves_pending_and_is_terminal():
    engine = make_engine()
    with Session(engine) as db:
        seed_proposal(db)
        db.commit()
    client = client_for(engine, 1)
    assert client.post("/api/v1/proposals/1/reject", json={"reason": "Not the same deposit"}).status_code == 200
    assert client.post("/api/v1/proposals/1/reject", json={"reason": "again"}).status_code == 409
    with Session(engine) as db:
        assert {row.status for row in db.scalars(select(ImportedRecord)).all()} == {"PENDIENTE"}
        proposal = db.get(ReconciliationProposal, 1)
        assert proposal.status == "RECHAZADA"
        assert proposal.decision_reason == "Not the same deposit"
        assert db.scalar(select(EventHistory).where(EventHistory.event_type == "PROPUESTA_RECHAZADA")).reason == "Not the same deposit"
    app.dependency_overrides.clear()
    engine.dispose()


def test_confirm_conflicts_when_an_endpoint_is_no_longer_pending_without_partial_mutation():
    engine = make_engine()
    with Session(engine) as db:
        seed_proposal(db, movement_status="CONCILIADO")
        db.commit()
    client = client_for(engine, 1)
    response = client.post("/api/v1/proposals/1/confirm", json={})
    assert response.status_code == 409
    with Session(engine) as db:
        proposal = db.get(ReconciliationProposal, 1)
        assert proposal.status == "GENERADA"
        assert db.scalar(select(Reconciliation)) is None
    app.dependency_overrides.clear()
    engine.dispose()


def test_proposal_and_history_are_owner_scoped():
    engine = make_engine()
    with Session(engine) as db:
        seed_proposal(db, owner_id=1)
        seed_proposal(db, owner_id=2)
        db.commit()
    owner = client_for(engine, 1)
    assert owner.post("/api/v1/proposals/1/reject", json={"reason": "Duplicate"}).status_code == 200
    assert TestClient(app).get("/api/v1/history").status_code == 401
    other = client_for(engine, 2)
    assert other.get("/api/v1/proposals/1").status_code == 404
    assert other.get("/api/v1/reconciliations/1").status_code == 404
    assert other.get("/api/v1/history").json()["total"] == 0
    assert other.post("/api/v1/proposals/1/confirm", json={}).status_code == 404
    app.dependency_overrides.clear()
    engine.dispose()
