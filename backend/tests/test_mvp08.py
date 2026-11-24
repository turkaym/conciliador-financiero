from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from pwdlib import PasswordHash
from sqlalchemy import create_engine, select
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
from app.proposals.matching import MatchInput, evaluation_fingerprint


def make_engine():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return engine


def seed_active_reconciliation(db: Session, owner_id: int = 1) -> None:
    db.add_all([
        User(id=owner_id, email=f"user{owner_id}@example.com", password_hash=PasswordHash.recommended().hash("secret"), active=True),
        DataSource(id=owner_id, source_type="BANCO", code=f"bank-{owner_id}", name="Bank", active=True),
        DataSource(id=owner_id + 10, source_type="COMPROBANTES", code=f"receipt-{owner_id}", name="Receipt", active=True),
        ImportBatch(id=owner_id, source_id=owner_id, user_id=owner_id, batch_type="MOVIMIENTO", file_name="m.csv", file_hash=bytes([owner_id]), file_content=b"m", status="PROCESADO", requested_template="1"),
        ImportBatch(id=owner_id + 10, source_id=owner_id + 10, user_id=owner_id, batch_type="COMPROBANTE", file_name="r.csv", file_hash=bytes([owner_id + 10]), file_content=b"r", status="PROCESADO", requested_template="2"),
        ImportedRecord(id=owner_id, batch_id=owner_id, source_id=owner_id, row_number=2, record_type="MOVIMIENTO", status="CONCILIADO", duplicate_key=bytes([owner_id]), original_data={"referencia": "invoice"}),
        ImportedRecord(id=owner_id + 10, batch_id=owner_id + 10, source_id=owner_id + 10, row_number=2, record_type="COMPROBANTE", status="CONCILIADO", duplicate_key=bytes([owner_id + 10]), original_data={"referencia": "invoice"}),
        BankMovement(record_id=owner_id, date=date(2026, 1, 1), amount=Decimal("100.00"), currency="ARS", is_credit=True),
        Receipt(record_id=owner_id + 10, date=date(2026, 1, 2), amount=Decimal("100.00"), currency="ARS", category="VENTA"),
        ReconciliationProposal(id=owner_id, movement_id=owner_id, receipt_id=owner_id + 10, status="CONFIRMADA", normalizer_version="ref-nfkd-v1", rule_version="match-v1", evaluation_fingerprint=evaluation_fingerprint(MatchInput(owner_id, date(2026, 1, 1), Decimal("100.00"), "ARS", "invoice", owner_id + 10, date(2026, 1, 2), Decimal("100.00"), "ARS", "invoice")), origin_type="LOTE", origin_batch_id=owner_id, reference_score=Decimal("1"), exact_match=True, day_difference=1, explanation={"movement_normalized": "INVOICE", "receipt_normalized": "INVOICE", "movement_tokens": ["INVOICE"], "receipt_tokens": ["INVOICE"]}, decided_by=owner_id),
        Reconciliation(id=owner_id, proposal_id=owner_id, movement_id=owner_id, receipt_id=owner_id + 10, status="ACTIVA", confirmed_by=owner_id),
    ])


def client_for(engine, user_id: int):
    def override_get_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    client.headers["Authorization"] = f"Bearer {create_access_token(user_id)}"
    return client


def close_engine(engine):
    app.dependency_overrides.clear()
    engine.dispose()


def test_reverse_is_atomic_releases_both_records_and_regenerates_deterministically():
    engine = make_engine()
    with Session(engine) as db:
        seed_active_reconciliation(db)
        db.add_all([
            ImportedRecord(id=20, batch_id=30, source_id=30, row_number=2, record_type="COMPROBANTE", status="PENDIENTE", duplicate_key=b"x" * 32, original_data={"referencia": "other"}),
            DataSource(id=30, source_type="COMPROBANTES", code="other-receipt", name="Other Receipt", active=True),
            ImportBatch(id=30, source_id=30, user_id=1, batch_type="COMPROBANTE", file_name="other.csv", file_hash=b"y" * 32, file_content=b"other", status="PROCESADO", requested_template="2"),
            Receipt(record_id=20, date=date(2026, 1, 3), amount=Decimal("100.00"), currency="ARS", category="VENTA"),
        ])
        db.commit()

    client = client_for(engine, 1)
    response = client.post("/api/v1/reconciliations/1/reverse", json={"reason": "Bank correction"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "REVERTIDA"
    assert body["reversal"]["reason"] == "Bank correction"
    assert body["generated_proposals"] == [{"id": 2, "origin": {"type": "REVERSAL", "reverted_reconciliation_id": 1}}]

    with Session(engine) as db:
        assert db.get(ImportedRecord, 1).status == "CON_PROPUESTAS"
        assert db.get(ImportedRecord, 11).status == "PENDIENTE"
        reconciliation = db.get(Reconciliation, 1)
        assert reconciliation.status == "REVERTIDA"
        assert reconciliation.reversal_reason == "Bank correction"
        assert db.scalar(select(ReconciliationProposal).where(ReconciliationProposal.id == 2)).origin_type == "REVERSION"
        events = db.scalars(select(EventHistory).order_by(EventHistory.id)).all()
        assert [event.event_type for event in events] == ["CONCILIACION_REVERTIDA"]

    detail = client.get("/api/v1/reconciliations/1")
    assert detail.status_code == 200
    assert detail.json()["status"] == "REVERTIDA"
    assert detail.json()["reversal"]["reason"] == "Bank correction"
    assert client.get("/api/v1/history", params={"event_type": "CONCILIACION_REVERTIDA"}).json()["total"] == 1
    close_engine(engine)


def test_reverse_rejects_duplicate_empty_reason_and_conflicting_state_without_mutation():
    engine = make_engine()
    with Session(engine) as db:
        seed_active_reconciliation(db)
        db.commit()
    client = client_for(engine, 1)
    assert client.post("/api/v1/reconciliations/1/reverse", json={"reason": "  "}).status_code == 422
    assert client.post("/api/v1/reconciliations/1/reverse", json={"reason": "Valid"}).status_code == 200
    assert client.post("/api/v1/reconciliations/1/reverse", json={"reason": "Again"}).status_code == 409
    with Session(engine) as db:
        assert db.get(Reconciliation, 1).reversal_reason == "Valid"
        assert db.scalar(select(EventHistory).where(EventHistory.event_type == "CONCILIACION_REVERTIDA")).reason == "Valid"

    close_engine(engine)


def test_reverse_is_owner_scoped_and_rejects_stale_endpoint_state():
    engine = make_engine()
    with Session(engine) as db:
        seed_active_reconciliation(db)
        db.add(User(id=2, email="user2@example.com", password_hash=PasswordHash.recommended().hash("secret"), active=True))
        db.get(ImportedRecord, 1).status = "PENDIENTE"
        db.commit()
    owner = client_for(engine, 1)
    assert owner.post("/api/v1/reconciliations/1/reverse", json={"reason": "Stale"}).status_code == 409
    other = client_for(engine, 2)
    assert other.post("/api/v1/reconciliations/1/reverse", json={"reason": "No access"}).status_code == 404
    with Session(engine) as db:
        assert db.get(Reconciliation, 1).status == "ACTIVA"
        assert db.scalar(select(EventHistory).where(EventHistory.event_type == "CONCILIACION_REVERTIDA")) is None
    close_engine(engine)
