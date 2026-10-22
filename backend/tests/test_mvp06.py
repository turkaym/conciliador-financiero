from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from pwdlib import PasswordHash

from app.models import Base, BankMovement, DataSource, ImportBatch, ImportedRecord, ImportTemplate, Receipt, ReconciliationProposal, User
from app.access.security import create_access_token
from app.database import get_db
from app.main import app
from app.proposals.matching import MatchInput, evaluate_pair, normalize_reference, rank_matches
from app.proposals.service import generate_for_batch


def pair(**overrides) -> MatchInput:
    values = dict(
        movement_id=1, movement_date=date(2026, 1, 10), movement_amount=Decimal("100.00"), movement_currency="ARS", movement_reference="Factura Á-100",
        receipt_id=2, receipt_date=date(2026, 1, 13), receipt_amount=Decimal("100.00"), receipt_currency="ARS", receipt_reference="FACTURA 100",
    )
    values.update(overrides)
    return MatchInput(**values)


def test_eligibility_requires_ars_exact_amount_and_inclusive_three_day_window():
    assert evaluate_pair(pair()) is not None
    assert evaluate_pair(pair(movement_currency="USD")) is None
    assert evaluate_pair(pair(receipt_amount=Decimal("100.01"))) is None
    assert evaluate_pair(pair(receipt_date=date(2026, 1, 14))) is None
    assert evaluate_pair(pair(receipt_date=date(2026, 1, 7))) is not None
    assert evaluate_pair(pair(receipt_date=date(2026, 1, 6))) is None


def test_reference_nfkd_and_jaccard_rank_only_eligible_candidates():
    normalized, tokens = normalize_reference(" factura-á, FACTURA 100 ")
    assert normalized == "FACTURA A FACTURA 100"
    assert tokens == ("100", "A", "FACTURA")
    exact = evaluate_pair(pair(receipt_id=3, receipt_reference="FACTURA 100"))
    partial = evaluate_pair(pair(receipt_id=4, receipt_reference="FACTURA 200"))
    assert exact and partial
    assert [item.receipt_id for item in rank_matches([partial, exact])] == [3, 4]
    assert evaluate_pair(pair(receipt_reference="FACTURA 100", receipt_date=date(2026, 1, 20))) is None


def test_reference_ties_use_stable_ids_and_empty_references_are_not_exact():
    left = evaluate_pair(pair(movement_id=2, receipt_id=4, movement_reference="", receipt_reference="x"))
    right = evaluate_pair(pair(movement_id=1, receipt_id=5, movement_reference="", receipt_reference="x"))
    assert left and right and not left.exact_match
    assert [item.movement_id for item in rank_matches([left, right])] == [1, 2]


def test_generation_is_one_to_one_persisted_and_idempotent():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([
            User(id=1, email="demo@example.com", password_hash="hash", active=True),
            DataSource(id=1, source_type="BANCO", code="bank", name="Bank", active=True),
            DataSource(id=2, source_type="COMPROBANTES", code="receipt", name="Receipt", active=True),
            ImportTemplate(id=1, source_id=1, name="bank", template_type="MOVIMIENTO", version=1, active=True),
            ImportTemplate(id=2, source_id=2, name="receipt", template_type="COMPROBANTE", version=1, active=True),
            ImportBatch(id=1, source_id=1, template_id=1, requested_template="1", user_id=1, batch_type="MOVIMIENTO", file_name="bank.csv", file_hash=b"a", file_content=b"a", status="PROCESADO"),
            ImportBatch(id=2, source_id=2, template_id=2, requested_template="2", user_id=1, batch_type="COMPROBANTE", file_name="receipt.csv", file_hash=b"b", file_content=b"b", status="PROCESADO"),
        ])
        db.flush()
        db.add_all([
            ImportedRecord(id=1, batch_id=1, source_id=1, row_number=2, record_type="MOVIMIENTO", status="PENDIENTE", duplicate_key=b"1", original_data={"referencia": "Factura 100"}),
            ImportedRecord(id=2, batch_id=2, source_id=2, row_number=2, record_type="COMPROBANTE", status="PENDIENTE", duplicate_key=b"2", original_data={"referencia": "Factura 100"}),
            BankMovement(record_id=1, date=date(2026, 1, 10), amount=Decimal("100.00"), currency="ARS", is_credit=True),
            Receipt(record_id=2, date=date(2026, 1, 12), amount=Decimal("100.00"), currency="ARS", category="VENTA"),
        ])
        db.commit()
        first = generate_for_batch(db, 1, 1)
        db.commit()
        second = generate_for_batch(db, 1, 1)
        assert len(first) == 1
        assert second == []
        assert db.scalar(select(ReconciliationProposal).where(ReconciliationProposal.id == first[0].id)).status == "GENERADA"


def test_proposal_api_requires_authentication_and_hides_other_owner():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([
            User(id=1, email="one@example.com", password_hash=PasswordHash.recommended().hash("secret"), active=True),
            User(id=2, email="two@example.com", password_hash=PasswordHash.recommended().hash("secret"), active=True),
            DataSource(id=1, source_type="BANCO", code="bank", name="Bank", active=True),
            DataSource(id=2, source_type="COMPROBANTES", code="receipt", name="Receipt", active=True),
            ImportBatch(id=1, source_id=1, user_id=2, batch_type="MOVIMIENTO", file_name="m.csv", file_hash=b"a", file_content=b"a", status="PROCESADO", requested_template="1"),
            ImportBatch(id=2, source_id=2, user_id=2, batch_type="COMPROBANTE", file_name="r.csv", file_hash=b"b", file_content=b"b", status="PROCESADO", requested_template="2"),
            ImportedRecord(id=1, batch_id=1, source_id=1, row_number=2, record_type="MOVIMIENTO", status="CON_PROPUESTAS", duplicate_key=b"1", original_data={"referencia": "x"}),
            ImportedRecord(id=2, batch_id=2, source_id=2, row_number=2, record_type="COMPROBANTE", status="CON_PROPUESTAS", duplicate_key=b"2", original_data={"referencia": "x"}),
            BankMovement(record_id=1, date=date(2026, 1, 1), amount=Decimal("1.00"), currency="ARS", is_credit=True),
            Receipt(record_id=2, date=date(2026, 1, 1), amount=Decimal("1.00"), currency="ARS", category="VENTA"),
            ReconciliationProposal(id=1, movement_id=1, receipt_id=2, status="GENERADA", normalizer_version="ref-nfkd-v1", rule_version="match-v1", evaluation_fingerprint=b"x", origin_type="LOTE", origin_batch_id=1, reference_score=Decimal("1"), exact_match=True, day_difference=0, explanation={"movement_normalized": "x", "receipt_normalized": "x", "movement_tokens": ["X"], "receipt_tokens": ["X"]}),
        ])
        db.commit()

    def override_get_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        assert client.get("/api/v1/proposals").status_code == 401
        assert client.get("/api/v1/proposals", headers={"Authorization": f"Bearer {create_access_token(1)}"}).json()["total"] == 0
        assert client.get("/api/v1/proposals", headers={"Authorization": f"Bearer {create_access_token(2)}"}).json()["total"] == 1
    app.dependency_overrides.clear()
    engine.dispose()
