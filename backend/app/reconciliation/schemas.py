from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, field_serializer


class RejectionRequest(BaseModel):
    reason: str


class ReversalRequest(BaseModel):
    reason: str


class DecisionResponse(BaseModel):
    id: int
    status: str
    reason: str | None = None
    decided_by: int
    decided_at: datetime


class ReconciliationResponse(BaseModel):
    id: int
    status: str


class ConfirmationResponse(BaseModel):
    proposal: DecisionResponse
    reconciliation: ReconciliationResponse


class ReconciliationDetail(BaseModel):
    id: int
    status: str
    proposal_id: int
    movement: dict[str, object]
    receipt: dict[str, object]
    confirmed_by: int
    confirmed_at: datetime
    reversal: dict[str, object] | None = None


class GeneratedProposalResponse(BaseModel):
    id: int
    origin: dict[str, object]


class ReversalResponse(BaseModel):
    id: int
    status: str
    reversal: dict[str, object]
    generated_proposals: list[GeneratedProposalResponse]


class HistoryItem(BaseModel):
    id: int
    event_type: str
    target: dict[str, object]
    actor: int | None
    reason: str | None
    data: dict[str, object]
    occurred_at: datetime


class HistoryList(BaseModel):
    page: int
    page_size: int
    total: int
    items: list[HistoryItem]
