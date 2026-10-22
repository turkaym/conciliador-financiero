from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.access.security import get_current_user
from app.database import get_db
from app.errors import ApiError
from app.models import BankMovement, ImportBatch, ImportedRecord, Receipt, Reconciliation, User
from app.queries.schemas import PendingItem, PendingList

router = APIRouter(tags=["queries"])


def _pending_query():
    active_reconciliation = select(Reconciliation.id).where(
        Reconciliation.status == "ACTIVA",
        or_(Reconciliation.movement_id == ImportedRecord.id, Reconciliation.receipt_id == ImportedRecord.id),
    ).exists()
    return (
        select(ImportedRecord, ImportBatch, BankMovement, Receipt)
        .join(ImportBatch, ImportBatch.id == ImportedRecord.batch_id)
        .outerjoin(BankMovement, BankMovement.record_id == ImportedRecord.id)
        .outerjoin(Receipt, Receipt.record_id == ImportedRecord.id)
        .where(ImportedRecord.status.in_(("PENDIENTE", "CON_PROPUESTAS")), ~active_reconciliation)
    )


def _item(record: ImportedRecord, batch: ImportBatch, movement: BankMovement | None, receipt: Receipt | None) -> PendingItem:
    transaction = movement or receipt
    return PendingItem(
        record_id=record.id,
        type=record.record_type,
        batch_id=batch.id,
        external_id=record.external_id,
        date=transaction.date,
        amount=transaction.amount,
        currency=transaction.currency,
        reference_original=record.original_data.get("referencia"),
        state=record.status,
        cause="UNRECONCILED",
    )


@router.get("/pending", response_model=PendingList)
def list_pending(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    type: str | None = Query(default=None),
    source_id: int | None = Query(default=None),
    batch_id: int | None = Query(default=None),
    state: str | None = Query(default=None),
    page: int = Query(default=1),
    page_size: int = Query(default=25),
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
):
    if type is not None and type not in {"MOVIMIENTO", "COMPROBANTE"}:
        raise ApiError(400, "INVALID_PENDING_TYPE", "Unsupported pending type")
    if state is not None and state not in {"PENDIENTE", "CON_PROPUESTAS"}:
        raise ApiError(400, "INVALID_PENDING_STATE", "Unsupported pending state")
    if page < 1 or page_size < 1 or page_size > 100:
        raise ApiError(400, "INVALID_PAGINATION", "Invalid pagination values")
    if (source_id is not None and source_id <= 0) or (batch_id is not None and batch_id <= 0):
        raise ApiError(400, "INVALID_PENDING_FILTER", "Invalid pending filter")
    if from_date and to_date and from_date > to_date:
        raise ApiError(400, "INVALID_DATE_WINDOW", "The date window is invalid")
    if batch_id is not None and db.scalar(
        select(ImportBatch.id).where(ImportBatch.id == batch_id, ImportBatch.user_id == user.id)
    ) is None:
        raise ApiError(404, "BATCH_NOT_FOUND", "Batch not found")

    query = _pending_query().where(ImportBatch.user_id == user.id)
    if type:
        query = query.where(ImportedRecord.record_type == type)
    if source_id:
        query = query.where(ImportedRecord.source_id == source_id)
    if batch_id:
        query = query.where(ImportedRecord.batch_id == batch_id)
    if state:
        query = query.where(ImportedRecord.status == state)
    if from_date:
        query = query.where(or_(BankMovement.date >= from_date, Receipt.date >= from_date))
    if to_date:
        query = query.where(or_(BankMovement.date <= to_date, Receipt.date <= to_date))

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.execute(query.order_by(ImportedRecord.created_at, ImportedRecord.id).offset((page - 1) * page_size).limit(page_size)).all()
    return PendingList(page=page, page_size=page_size, total=total, items=[_item(record, batch, movement, receipt) for record, batch, movement, receipt in rows])
