from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.errors import ApiError
from app.models import EventHistory, ImportBatch, ImportedRecord, Reconciliation, ReconciliationProposal


def owned_proposal(db: Session, proposal_id: int, user_id: int) -> ReconciliationProposal | None:
    return db.scalar(
        select(ReconciliationProposal)
        .join(ImportedRecord, ImportedRecord.id == ReconciliationProposal.movement_id)
        .join(ImportBatch, ImportBatch.id == ImportedRecord.batch_id)
        .where(ReconciliationProposal.id == proposal_id, ImportBatch.user_id == user_id)
    )


def _lock_records(db: Session, ids: tuple[int, int]) -> list[ImportedRecord]:
    return db.scalars(
        select(ImportedRecord).where(ImportedRecord.id.in_(ids)).order_by(ImportedRecord.id).with_for_update()
    ).all()


def _active_reconciliation(db: Session, record_id: int) -> bool:
    return db.scalar(
        select(Reconciliation.id).where(
            Reconciliation.status == "ACTIVA",
            or_(Reconciliation.movement_id == record_id, Reconciliation.receipt_id == record_id),
        )
    ) is not None


def _event(db: Session, *, user_id: int, proposal_id: int | None = None, reconciliation_id: int | None = None, event_type: str, reason: str | None = None) -> None:
    db.add(EventHistory(user_id=user_id, proposal_id=proposal_id, reconciliation_id=reconciliation_id, event_type=event_type, reason=reason, data={}))


def confirm_proposal(db: Session, proposal_id: int, user_id: int) -> tuple[ReconciliationProposal, Reconciliation]:
    proposal = owned_proposal(db, proposal_id, user_id)
    if proposal is None:
        raise ApiError(404, "PROPOSAL_NOT_FOUND", "Proposal not found")

    ids = (proposal.movement_id, proposal.receipt_id)
    records = _lock_records(db, ids)
    locked = {record.id: record for record in records}
    proposal = db.scalar(select(ReconciliationProposal).where(ReconciliationProposal.id == proposal_id).with_for_update())
    if proposal is None or proposal.status != "GENERADA":
        raise ApiError(409, "PROPOSAL_NOT_PENDING", "Proposal is already decided")
    if len(records) != 2 or any(locked[record_id].status not in {"PENDIENTE", "CON_PROPUESTAS"} for record_id in ids) or any(_active_reconciliation(db, record_id) for record_id in ids):
        raise ApiError(409, "RECORD_NOT_PENDING", "One or more records are no longer pending")

    now = datetime.now(timezone.utc)
    proposal.status = "CONFIRMADA"
    proposal.decided_by = user_id
    proposal.decided_at = now
    locked[proposal.movement_id].status = "CONCILIADO"
    locked[proposal.receipt_id].status = "CONCILIADO"
    reconciliation = Reconciliation(
        proposal_id=proposal.id,
        movement_id=proposal.movement_id,
        receipt_id=proposal.receipt_id,
        status="ACTIVA",
        confirmed_by=user_id,
        confirmed_at=now,
    )
    db.add(reconciliation)
    db.flush()
    for other in db.scalars(
        select(ReconciliationProposal).where(
            ReconciliationProposal.status == "GENERADA",
            ReconciliationProposal.id != proposal.id,
            or_(ReconciliationProposal.movement_id.in_(ids), ReconciliationProposal.receipt_id.in_(ids)),
        )
    ).all():
        other.status = "CADUCADA"
        other.decided_at = now
    _event(db, user_id=user_id, proposal_id=proposal.id, event_type="PROPUESTA_CONFIRMADA")
    db.flush()
    return proposal, reconciliation


def reject_proposal(db: Session, proposal_id: int, user_id: int, reason: str) -> ReconciliationProposal:
    proposal = owned_proposal(db, proposal_id, user_id)
    if proposal is None:
        raise ApiError(404, "PROPOSAL_NOT_FOUND", "Proposal not found")
    if not reason.strip():
        raise ApiError(422, "INVALID_REJECTION_REASON", "A rejection reason is required")
    proposal = db.scalar(select(ReconciliationProposal).where(ReconciliationProposal.id == proposal_id).with_for_update())
    if proposal is None or proposal.status != "GENERADA":
        raise ApiError(409, "PROPOSAL_NOT_PENDING", "Proposal is already decided")
    now = datetime.now(timezone.utc)
    proposal.status = "RECHAZADA"
    proposal.decision_reason = reason.strip()
    proposal.decided_by = user_id
    proposal.decided_at = now
    for record_id in (proposal.movement_id, proposal.receipt_id):
        record = db.get(ImportedRecord, record_id)
        generated = db.scalar(
            select(ReconciliationProposal.id).where(
                ReconciliationProposal.status == "GENERADA",
                ReconciliationProposal.id != proposal.id,
                or_(ReconciliationProposal.movement_id == record_id, ReconciliationProposal.receipt_id == record_id),
            )
        )
        if record is not None and generated is None and record.status == "CON_PROPUESTAS":
            record.status = "PENDIENTE"
    _event(db, user_id=user_id, proposal_id=proposal.id, event_type="PROPUESTA_RECHAZADA", reason=proposal.decision_reason)
    db.flush()
    return proposal
