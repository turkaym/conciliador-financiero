from datetime import date
from decimal import Decimal

from pydantic import BaseModel, field_serializer


class PendingItem(BaseModel):
    record_id: int
    type: str
    batch_id: int
    external_id: str | None
    date: date
    amount: Decimal
    currency: str
    reference_original: str | None
    state: str
    cause: str

    @field_serializer("amount")
    def serialize_amount(self, amount: Decimal) -> str:
        return f"{amount:.2f}"


class PendingList(BaseModel):
    page: int
    page_size: int
    total: int
    items: list[PendingItem]


class ConsolidatedSource(BaseModel):
    id: int
    code: str
    name: str


class ConsolidatedItem(BaseModel):
    record_id: int
    type: str
    source: ConsolidatedSource
    batch_id: int
    external_id: str | None
    date: date
    amount: Decimal
    currency: str
    description: str | None
    state: str
    reconciled: bool

    @field_serializer("amount")
    def serialize_amount(self, amount: Decimal) -> str:
        return f"{amount:.2f}"


class ConsolidatedList(BaseModel):
    page: int
    page_size: int
    total: int
    items: list[ConsolidatedItem]
