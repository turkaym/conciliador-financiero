from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, field_serializer


class ProposalRecord(BaseModel):
    record_id: int
    batch_id: int
    date: date
    amount: Decimal
    currency: str
    reference_original: str | None

    @field_serializer("amount")
    def serialize_amount(self, amount: Decimal) -> str:
        return f"{amount:.2f}"


class ProposalRanking(BaseModel):
    exact_match: bool
    reference_score: Decimal
    day_difference: int
    normalizer_version: str
    rule_version: str
    movement_normalized: str
    receipt_normalized: str
    movement_tokens: list[str]
    receipt_tokens: list[str]

    @field_serializer("reference_score")
    def serialize_score(self, score: Decimal) -> str:
        return f"{score:.4f}"


class ProposalSummary(BaseModel):
    id: int
    status: str
    movement_id: int
    receipt_id: int
    exact_match: bool
    reference_score: Decimal
    day_difference: int
    rule_version: str
    normalizer_version: str

    @field_serializer("reference_score")
    def serialize_score(self, score: Decimal) -> str:
        return f"{score:.4f}"


class ProposalList(BaseModel):
    page: int
    page_size: int
    total: int
    items: list[ProposalSummary]


class ProposalDetail(BaseModel):
    id: int
    status: str
    evaluation_fingerprint: str
    movement: ProposalRecord
    receipt: ProposalRecord
    ranking: ProposalRanking
    origin: dict[str, object]
    decision: dict[str, object] | None
    created_at: datetime
