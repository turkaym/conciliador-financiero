from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.access.security import get_current_user
from app.database import get_db
from app.errors import ApiError
from app.models import BankMovement, EventHistory, ImportBatch, ImportedRecord, Receipt, Reconciliation, ReconciliationProposal, User
from app.reconciliation.schemas import ConfirmationResponse, DecisionResponse, GeneratedProposalResponse, HistoryItem, HistoryList, ReconciliationDetail, ReconciliationResponse, RejectionRequest, ReversalRequest, ReversalResponse
from app.reconciliation.service import confirm_proposal, owned_proposal, reject_proposal, reverse_reconciliation

router = APIRouter(tags=["reconciliation"])


def _owned_reconciliation(db: Session, reconciliation_id: int, user_id: int) -> Reconciliation | None:
    return db.scalar(
        select(Reconciliation).join(ImportedRecord, ImportedRecord.id == Reconciliation.movement_id).join(ImportBatch, ImportBatch.id == ImportedRecord.batch_id).where(Reconciliation.id == reconciliation_id, ImportBatch.user_id == user_id)
    )


@router.post("/proposals/{proposal_id}/confirm", response_model=ConfirmationResponse)
def confirm(proposal_id: int, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]):
    proposal, reconciliation = confirm_proposal(db, proposal_id, user.id)
    db.commit()
    return ConfirmationResponse(
        proposal=DecisionResponse(id=proposal.id, status=proposal.status, decided_by=proposal.decided_by, decided_at=proposal.decided_at),
        reconciliation=ReconciliationResponse(id=reconciliation.id, status=reconciliation.status),
    )


@router.post("/proposals/{proposal_id}/reject", response_model=DecisionResponse)
def reject(proposal_id: int, request: RejectionRequest, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]):
    proposal = reject_proposal(db, proposal_id, user.id, request.reason)
    db.commit()
    return DecisionResponse(id=proposal.id, status=proposal.status, reason=proposal.decision_reason, decided_by=proposal.decided_by, decided_at=proposal.decided_at)


@router.get("/reconciliations/{reconciliation_id}", response_model=ReconciliationDetail)
def get_reconciliation(reconciliation_id: int, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]):
    reconciliation = _owned_reconciliation(db, reconciliation_id, user.id)
    if reconciliation is None:
        raise ApiError(404, "RECONCILIATION_NOT_FOUND", "Reconciliation not found")
    proposal = db.get(ReconciliationProposal, reconciliation.proposal_id)
    movement = db.get(BankMovement, reconciliation.movement_id)
    receipt = db.get(Receipt, reconciliation.receipt_id)
    return ReconciliationDetail(
        id=reconciliation.id, status=reconciliation.status, proposal_id=reconciliation.proposal_id,
        movement={"record_id": reconciliation.movement_id, "date": movement.date, "amount": str(movement.amount), "currency": movement.currency},
        receipt={"record_id": reconciliation.receipt_id, "date": receipt.date, "amount": str(receipt.amount), "currency": receipt.currency},
        confirmed_by=reconciliation.confirmed_by, confirmed_at=reconciliation.confirmed_at,
        reversal=None if reconciliation.reversed_at is None else {"reason": reconciliation.reversal_reason, "actor": reconciliation.reversed_by, "occurred_at": reconciliation.reversed_at},
    )


@router.post("/reconciliations/{reconciliation_id}/reverse", response_model=ReversalResponse)
def reverse(reconciliation_id: int, request: ReversalRequest, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]):
    reconciliation, proposals = reverse_reconciliation(db, reconciliation_id, user.id, request.reason)
    db.commit()
    return ReversalResponse(
        id=reconciliation.id,
        status=reconciliation.status,
        reversal={"reason": reconciliation.reversal_reason, "actor": reconciliation.reversed_by, "occurred_at": reconciliation.reversed_at},
        generated_proposals=[GeneratedProposalResponse(id=proposal.id, origin={"type": "REVERSAL", "reverted_reconciliation_id": reconciliation.id}) for proposal in proposals],
    )


def _history_owner_filter(user_id: int):
    return or_(
        EventHistory.proposal_id.in_(select(EventHistory.proposal_id).join(ReconciliationProposal, ReconciliationProposal.id == EventHistory.proposal_id).join(ImportedRecord, ImportedRecord.id == ReconciliationProposal.movement_id).join(ImportBatch, ImportBatch.id == ImportedRecord.batch_id).where(ImportBatch.user_id == user_id)),
        EventHistory.reconciliation_id.in_(select(Reconciliation.id).join(ImportedRecord, ImportedRecord.id == Reconciliation.movement_id).join(ImportBatch, ImportBatch.id == ImportedRecord.batch_id).where(ImportBatch.user_id == user_id)),
    )


@router.get("/history", response_model=HistoryList)
def history(db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(get_current_user)], event_type: str | None = Query(default=None), page: int = Query(default=1), page_size: int = Query(default=25)):
    if page < 1 or page_size < 1 or page_size > 100:
        raise ApiError(400, "INVALID_PAGINATION", "Invalid pagination values")
    query = select(EventHistory).where(_history_owner_filter(user.id))
    if event_type:
        query = query.where(EventHistory.event_type == event_type)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(query.order_by(EventHistory.occurred_at.desc(), EventHistory.id.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return HistoryList(page=page, page_size=page_size, total=total, items=[HistoryItem(id=row.id, event_type=row.event_type, target={"type": "PROPOSAL", "id": row.proposal_id} if row.proposal_id is not None else {"type": "RECONCILIATION", "id": row.reconciliation_id}, actor=row.user_id, reason=row.reason, data=row.data, occurred_at=row.occurred_at) for row in rows])
