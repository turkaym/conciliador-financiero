from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.errors import ApiError
from app.models import EventHistory, ImportBatch, ImportedRecord, Reconciliation, ReconciliationProposal
from app.proposals.service import generate_for_reversal


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


def _lock_record_ids(db: Session, ids: set[int]) -> list[ImportedRecord]:
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


def _active_reconciliation_exists(record_id: int):
    return select(Reconciliation.id).where(
        Reconciliation.status == "ACTIVA",
        or_(Reconciliation.movement_id == record_id, Reconciliation.receipt_id == record_id),
    ).exists()


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


def reverse_reconciliation(db: Session, reconciliation_id: int, user_id: int, reason: str) -> tuple[Reconciliation, list[ReconciliationProposal]]:
    if not reason.strip():
        raise ApiError(422, "INVALID_REVERSAL_REASON", "A reversal reason is required")

    owned = db.scalar(
        select(Reconciliation)
        .join(ImportedRecord, ImportedRecord.id == Reconciliation.movement_id)
        .join(ImportBatch, ImportBatch.id == ImportedRecord.batch_id)
        .where(Reconciliation.id == reconciliation_id, ImportBatch.user_id == user_id)
    )
    if owned is None:
        raise ApiError(404, "RECONCILIATION_NOT_FOUND", "Reconciliation not found")

    endpoint_ids = {owned.movement_id, owned.receipt_id}
    candidate_ids = set(db.scalars(
        select(ImportedRecord.id)
        .join(ImportBatch, ImportBatch.id == ImportedRecord.batch_id)
        .where(
            ImportBatch.user_id == user_id,
            ImportedRecord.status.in_(('PENDIENTE', 'CON_PROPUESTAS')),
            ~_active_reconciliation_exists(ImportedRecord.id),
        )
    ).all())
    locked_records = _lock_record_ids(db, endpoint_ids | candidate_ids)
    locked = {record.id: record for record in locked_records}

    reconciliation = db.scalar(
        select(Reconciliation).where(Reconciliation.id == reconciliation_id).with_for_update()
    )
    if reconciliation is None or reconciliation.status != "ACTIVA":
        raise ApiError(409, "RECONCILIATION_NOT_ACTIVE", "Reconciliation is already reversed")
    if len(locked_records) < len(endpoint_ids) or any(
        locked[record_id].status != "CONCILIADO" for record_id in endpoint_ids
    ):
        raise ApiError(409, "RECORD_NOT_RECONCILED", "One or more records are no longer reconciled")

    now = datetime.now(timezone.utc)
    reconciliation.status = "REVERTIDA"
    reconciliation.reversed_by = user_id
    reconciliation.reversed_at = now
    reconciliation.reversal_reason = reason.strip()
    for record_id in endpoint_ids:
        locked[record_id].status = "PENDIENTE"
    db.flush()

    proposals = generate_for_reversal(db, reconciliation, user_id, set(locked))
    _event(
        db,
        user_id=user_id,
        reconciliation_id=reconciliation.id,
        event_type="CONCILIACION_REVERTIDA",
        reason=reconciliation.reversal_reason,
    )
    db.flush()
    return reconciliation, proposals
