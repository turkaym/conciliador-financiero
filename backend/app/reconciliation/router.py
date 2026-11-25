import csv
import io
from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, aliased

from app.access.security import get_current_user
from app.database import get_db
from app.errors import ApiError
from app.models import BankMovement, DataSource, EventHistory, ImportBatch, ImportedRecord, Receipt, Reconciliation, ReconciliationProposal, User
from app.reconciliation.schemas import ConfirmationResponse, DecisionResponse, GeneratedProposalResponse, HistoryItem, HistoryList, ManualReconciliationRequest, ReconciliationAuditList, ReconciliationDetail, ReconciliationResponse, RejectionRequest, ReversalRequest, ReversalResponse
from app.proposals.matching import MANUAL_RULE_VERSION
from app.reconciliation.service import confirm_proposal, reconcile_manually, reject_proposal, reverse_reconciliation

router = APIRouter(tags=["reconciliation"])


def _owned_reconciliation(db: Session, reconciliation_id: int, user_id: int) -> Reconciliation | None:
    return db.scalar(
        select(Reconciliation).join(ImportedRecord, ImportedRecord.id == Reconciliation.movement_id).join(ImportBatch, ImportBatch.id == ImportedRecord.batch_id).where(Reconciliation.id == reconciliation_id, ImportBatch.user_id == user_id)
    )


def _reconciliation_detail(db: Session, reconciliation: Reconciliation) -> ReconciliationDetail:
    movement_record = db.get(ImportedRecord, reconciliation.movement_id)
    receipt_record = db.get(ImportedRecord, reconciliation.receipt_id)
    movement = db.get(BankMovement, reconciliation.movement_id)
    receipt = db.get(Receipt, reconciliation.receipt_id)
    movement_source = db.get(DataSource, movement_record.source_id)
    receipt_source = db.get(DataSource, receipt_record.source_id)
    return ReconciliationDetail(
        id=reconciliation.id,
        status=reconciliation.status,
        proposal_id=reconciliation.proposal_id,
        movement={
            "record_id": movement_record.id,
            "batch_id": movement_record.batch_id,
            "source_id": movement_source.id,
            "source_name": movement_source.name,
            "external_id": movement_record.external_id,
            "date": movement.date,
            "amount": str(movement.amount),
            "currency": movement.currency,
            "reference_original": movement_record.original_data.get("referencia"),
        },
        receipt={
            "record_id": receipt_record.id,
            "batch_id": receipt_record.batch_id,
            "source_id": receipt_source.id,
            "source_name": receipt_source.name,
            "external_id": receipt_record.external_id,
            "date": receipt.date,
            "amount": str(receipt.amount),
            "currency": receipt.currency,
            "reference_original": receipt_record.original_data.get("referencia"),
        },
        confirmed_by=reconciliation.confirmed_by,
        confirmed_at=reconciliation.confirmed_at,
        reversal=None
        if reconciliation.reversed_at is None
        else {
            "reason": reconciliation.reversal_reason,
            "actor": reconciliation.reversed_by,
            "occurred_at": reconciliation.reversed_at,
        },
    )


def _audit_query(
    user_id: int,
    *,
    status: str,
    confirmed_from: date | None,
    confirmed_to: date | None,
    movement_from: date | None,
    movement_to: date | None,
    receipt_from: date | None,
    receipt_to: date | None,
    movement_source_id: int | None,
    receipt_source_id: int | None,
    amount: Decimal | None,
    reference: str | None,
    batch_id: int | None,
    origin: str | None,
):
    movement_record = aliased(ImportedRecord)
    receipt_record = aliased(ImportedRecord)
    movement_batch = aliased(ImportBatch)
    receipt_batch = aliased(ImportBatch)
    query = (
        select(Reconciliation)
        .join(movement_record, movement_record.id == Reconciliation.movement_id)
        .join(receipt_record, receipt_record.id == Reconciliation.receipt_id)
        .join(movement_batch, movement_batch.id == movement_record.batch_id)
        .join(receipt_batch, receipt_batch.id == receipt_record.batch_id)
        .join(BankMovement, BankMovement.record_id == Reconciliation.movement_id)
        .join(Receipt, Receipt.record_id == Reconciliation.receipt_id)
        .join(ReconciliationProposal, ReconciliationProposal.id == Reconciliation.proposal_id)
        .where(
            movement_batch.user_id == user_id,
            receipt_batch.user_id == user_id,
            Reconciliation.status == status,
        )
    )
    if confirmed_from:
        query = query.where(func.date(Reconciliation.confirmed_at) >= confirmed_from)
    if confirmed_to:
        query = query.where(func.date(Reconciliation.confirmed_at) <= confirmed_to)
    if movement_from:
        query = query.where(BankMovement.date >= movement_from)
    if movement_to:
        query = query.where(BankMovement.date <= movement_to)
    if receipt_from:
        query = query.where(Receipt.date >= receipt_from)
    if receipt_to:
        query = query.where(Receipt.date <= receipt_to)
    if movement_source_id:
        query = query.where(movement_record.source_id == movement_source_id)
    if receipt_source_id:
        query = query.where(receipt_record.source_id == receipt_source_id)
    if amount is not None:
        query = query.where(or_(BankMovement.amount == amount, Receipt.amount == amount))
    if reference and reference.strip():
        pattern = f"%{reference.strip()}%"
        query = query.where(
            or_(
                movement_record.external_id.ilike(pattern),
                receipt_record.external_id.ilike(pattern),
                movement_record.original_data["referencia"].as_string().ilike(pattern),
                receipt_record.original_data["referencia"].as_string().ilike(pattern),
            )
        )
    if batch_id:
        query = query.where(
            or_(movement_record.batch_id == batch_id, receipt_record.batch_id == batch_id)
        )
    if origin == "MANUAL":
        query = query.where(ReconciliationProposal.rule_version == MANUAL_RULE_VERSION)
    elif origin == "AUTOMATICA":
        query = query.where(ReconciliationProposal.rule_version != MANUAL_RULE_VERSION)
    return query


def _validate_audit_filters(
    *,
    status: str,
    confirmed_from: date | None,
    confirmed_to: date | None,
    movement_from: date | None,
    movement_to: date | None,
    receipt_from: date | None,
    receipt_to: date | None,
    movement_source_id: int | None,
    receipt_source_id: int | None,
    amount: Decimal | None,
    batch_id: int | None,
    origin: str | None,
) -> None:
    if status not in {"ACTIVA", "REVERTIDA"}:
        raise ApiError(400, "INVALID_RECONCILIATION_STATUS", "Unsupported reconciliation status")
    for start, end in (
        (confirmed_from, confirmed_to),
        (movement_from, movement_to),
        (receipt_from, receipt_to),
    ):
        if start and end and start > end:
            raise ApiError(400, "INVALID_DATE_WINDOW", "The date window is invalid")
    if any(value is not None and value <= 0 for value in (movement_source_id, receipt_source_id, batch_id)):
        raise ApiError(400, "INVALID_AUDIT_FILTER", "Invalid audit filter")
    if amount is not None and amount <= 0:
        raise ApiError(400, "INVALID_AMOUNT_FILTER", "Invalid amount filter")
    if origin is not None and origin not in {"AUTOMATICA", "MANUAL"}:
        raise ApiError(400, "INVALID_RECONCILIATION_ORIGIN", "Unsupported reconciliation origin")


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


@router.post("/reconciliations/manual", response_model=ConfirmationResponse)
def confirm_manual_reconciliation(
    request: ManualReconciliationRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    proposal, reconciliation = reconcile_manually(
        db, request.movement_id, request.receipt_id, user.id
    )
    db.commit()
    return ConfirmationResponse(
        proposal=DecisionResponse(
            id=proposal.id,
            status=proposal.status,
            decided_by=proposal.decided_by,
            decided_at=proposal.decided_at,
        ),
        reconciliation=ReconciliationResponse(
            id=reconciliation.id, status=reconciliation.status
        ),
    )


@router.get("/reconciliations", response_model=ReconciliationAuditList)
def list_reconciliations(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    status: str = Query(default="ACTIVA"),
    page: int = Query(default=1),
    page_size: int = Query(default=25),
    confirmed_from: date | None = Query(default=None),
    confirmed_to: date | None = Query(default=None),
    movement_from: date | None = Query(default=None),
    movement_to: date | None = Query(default=None),
    receipt_from: date | None = Query(default=None),
    receipt_to: date | None = Query(default=None),
    movement_source_id: int | None = Query(default=None),
    receipt_source_id: int | None = Query(default=None),
    amount: Decimal | None = Query(default=None),
    reference: str | None = Query(default=None),
    batch_id: int | None = Query(default=None),
    origin: str | None = Query(default=None),
):
    if page < 1 or page_size < 1 or page_size > 100:
        raise ApiError(400, "INVALID_PAGINATION", "Invalid pagination values")
    _validate_audit_filters(
        status=status,
        confirmed_from=confirmed_from,
        confirmed_to=confirmed_to,
        movement_from=movement_from,
        movement_to=movement_to,
        receipt_from=receipt_from,
        receipt_to=receipt_to,
        movement_source_id=movement_source_id,
        receipt_source_id=receipt_source_id,
        amount=amount,
        batch_id=batch_id,
        origin=origin,
    )
    query = _audit_query(
        user.id,
        status=status,
        confirmed_from=confirmed_from,
        confirmed_to=confirmed_to,
        movement_from=movement_from,
        movement_to=movement_to,
        receipt_from=receipt_from,
        receipt_to=receipt_to,
        movement_source_id=movement_source_id,
        receipt_source_id=receipt_source_id,
        amount=amount,
        reference=reference,
        batch_id=batch_id,
        origin=origin,
    )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(Reconciliation.confirmed_at.desc(), Reconciliation.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return ReconciliationAuditList(
        page=page,
        page_size=page_size,
        total=total,
        items=[_reconciliation_detail(db, reconciliation) for reconciliation in rows],
    )


@router.get("/reconciliations/export.csv")
def export_reconciliations_csv(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    status: str = Query(default="ACTIVA"),
    confirmed_from: date | None = Query(default=None),
    confirmed_to: date | None = Query(default=None),
    movement_from: date | None = Query(default=None),
    movement_to: date | None = Query(default=None),
    receipt_from: date | None = Query(default=None),
    receipt_to: date | None = Query(default=None),
    movement_source_id: int | None = Query(default=None),
    receipt_source_id: int | None = Query(default=None),
    amount: Decimal | None = Query(default=None),
    reference: str | None = Query(default=None),
    batch_id: int | None = Query(default=None),
    origin: str | None = Query(default=None),
):
    _validate_audit_filters(
        status=status,
        confirmed_from=confirmed_from,
        confirmed_to=confirmed_to,
        movement_from=movement_from,
        movement_to=movement_to,
        receipt_from=receipt_from,
        receipt_to=receipt_to,
        movement_source_id=movement_source_id,
        receipt_source_id=receipt_source_id,
        amount=amount,
        batch_id=batch_id,
        origin=origin,
    )
    rows = db.scalars(
        _audit_query(
            user.id,
            status=status,
            confirmed_from=confirmed_from,
            confirmed_to=confirmed_to,
            movement_from=movement_from,
            movement_to=movement_to,
            receipt_from=receipt_from,
            receipt_to=receipt_to,
            movement_source_id=movement_source_id,
            receipt_source_id=receipt_source_id,
            amount=amount,
            reference=reference,
            batch_id=batch_id,
            origin=origin,
        ).order_by(Reconciliation.confirmed_at, Reconciliation.id)
    ).all()
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(
        [
            "conciliacion_id",
            "fecha_conciliacion",
            "origen",
            "usuario",
            "lado",
            "cuenta",
            "fecha_operacion",
            "referencia",
            "lote",
            "debe",
            "haber",
            "diferencia",
        ]
    )
    for reconciliation in rows:
        detail = _reconciliation_detail(db, reconciliation)
        proposal = db.get(ReconciliationProposal, reconciliation.proposal_id)
        actor = db.get(User, reconciliation.confirmed_by)
        origin_label = "MANUAL" if proposal.rule_version == MANUAL_RULE_VERSION else "AUTOMATICA"
        movement_amount = Decimal(str(detail.movement["amount"]))
        receipt_amount = Decimal(str(detail.receipt["amount"]))
        difference = movement_amount - receipt_amount
        common = [
            reconciliation.id,
            reconciliation.confirmed_at.isoformat(),
            origin_label,
            actor.email,
        ]
        writer.writerow(
            common
            + [
                "MOVIMIENTO",
                detail.movement["source_name"],
                detail.movement["date"],
                detail.movement["external_id"] or detail.movement["reference_original"] or "",
                detail.movement["batch_id"],
                f"{movement_amount:.2f}",
                "0.00",
                f"{difference:.2f}",
            ]
        )
        writer.writerow(
            common
            + [
                "COMPROBANTE",
                detail.receipt["source_name"],
                detail.receipt["date"],
                detail.receipt["external_id"] or detail.receipt["reference_original"] or "",
                detail.receipt["batch_id"],
                "0.00",
                f"{receipt_amount:.2f}",
                f"{difference:.2f}",
            ]
        )
    return Response(
        content="\ufeff" + output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="asiento-conciliaciones.csv"'},
    )


@router.get("/reconciliations/{reconciliation_id}", response_model=ReconciliationDetail)
def get_reconciliation(reconciliation_id: int, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]):
    reconciliation = _owned_reconciliation(db, reconciliation_id, user.id)
    if reconciliation is None:
        raise ApiError(404, "RECONCILIATION_NOT_FOUND", "Reconciliation not found")
    return _reconciliation_detail(db, reconciliation)


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
