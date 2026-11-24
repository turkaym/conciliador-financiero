import base64
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.access.security import get_current_user
from app.database import get_db
from app.errors import ApiError
from app.models import BankMovement, ImportBatch, ImportedRecord, Receipt, ReconciliationProposal, User
from app.proposals.schemas import ProposalDetail, ProposalList, ProposalRanking, ProposalRecord, ProposalSummary

router = APIRouter(prefix="/proposals", tags=["proposals"])


def _owned_query(db: Session, user_id: int):
    return select(ReconciliationProposal).join(ImportedRecord, ImportedRecord.id == ReconciliationProposal.movement_id).join(ImportBatch, ImportBatch.id == ImportedRecord.batch_id).where(ImportBatch.user_id == user_id)


@router.get("", response_model=ProposalList)
def list_proposals(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    status: str | None = Query(default=None),
    batch_id: int | None = Query(default=None),
    page: int = Query(default=1),
    page_size: int = Query(default=25),
):
    if status is not None and status not in {"GENERADA", "CONFIRMADA", "RECHAZADA", "CADUCADA"}:
        raise ApiError(400, "INVALID_PROPOSAL_STATUS", "Unsupported proposal status")
    if page < 1 or page_size < 1 or page_size > 100 or (batch_id is not None and batch_id <= 0):
        raise ApiError(400, "INVALID_PROPOSAL_FILTER", "Invalid proposal filter")
    query = _owned_query(db, user.id)
    if status:
        query = query.where(ReconciliationProposal.status == status)
    if batch_id:
        query = query.where(ReconciliationProposal.origin_batch_id == batch_id)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(query.order_by(ReconciliationProposal.exact_match.desc(), ReconciliationProposal.reference_score.desc(), func.abs(ReconciliationProposal.day_difference), ReconciliationProposal.movement_id, ReconciliationProposal.receipt_id).offset((page - 1) * page_size).limit(page_size)).all()
    return ProposalList(page=page, page_size=page_size, total=total, items=[ProposalSummary(id=row.id, status=row.status, movement_id=row.movement_id, receipt_id=row.receipt_id, exact_match=row.exact_match, reference_score=row.reference_score, day_difference=row.day_difference, rule_version=row.rule_version, normalizer_version=row.normalizer_version) for row in rows])


@router.get("/{proposal_id}", response_model=ProposalDetail)
def get_proposal(proposal_id: int, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]):
    proposal = db.scalar(_owned_query(db, user.id).where(ReconciliationProposal.id == proposal_id))
    if proposal is None:
        raise ApiError(404, "PROPOSAL_NOT_FOUND", "Proposal not found")
    movement, receipt = db.get(BankMovement, proposal.movement_id), db.get(Receipt, proposal.receipt_id)
    movement_record, receipt_record = db.get(ImportedRecord, proposal.movement_id), db.get(ImportedRecord, proposal.receipt_id)
    movement_batch, receipt_batch = db.get(ImportBatch, movement_record.batch_id), db.get(ImportBatch, receipt_record.batch_id)
    details = proposal.explanation
    ranking = ProposalRanking(exact_match=proposal.exact_match, reference_score=proposal.reference_score, day_difference=proposal.day_difference, normalizer_version=proposal.normalizer_version, rule_version=proposal.rule_version, **details)
    decision = None if proposal.decided_at is None else {"decided_by": proposal.decided_by, "decided_at": proposal.decided_at, "reason": proposal.decision_reason}
    if receipt_batch.user_id != user.id:
        raise ApiError(404, "PROPOSAL_NOT_FOUND", "Proposal not found")
    return ProposalDetail(
        id=proposal.id, status=proposal.status, evaluation_fingerprint="sha256:" + base64.urlsafe_b64encode(proposal.evaluation_fingerprint).decode().rstrip("="),
        movement=ProposalRecord(record_id=movement_record.id, batch_id=movement_batch.id, date=movement.date, amount=movement.amount, currency=movement.currency, reference_original=movement_record.original_data.get("referencia")),
        receipt=ProposalRecord(record_id=receipt_record.id, batch_id=receipt_batch.id, date=receipt.date, amount=receipt.amount, currency=receipt.currency, reference_original=receipt_record.original_data.get("referencia")),
        ranking=ranking, origin={"type": "BATCH" if proposal.origin_type == "LOTE" else "REVERSAL", "batch_id": proposal.origin_batch_id, "reverted_reconciliation_id": proposal.reverted_reconciliation_id, "generated_at": proposal.created_at}, decision=decision, created_at=proposal.created_at,
    )
