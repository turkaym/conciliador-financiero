from datetime import datetime

from pydantic import BaseModel


class BatchTemplate(BaseModel):
    id: int
    name: str
    version: int


class BatchTotals(BaseModel):
    total_rows: int = 0
    valid_rows: int = 0
    invalid_rows: int = 0


class BatchResponse(BaseModel):
    id: int
    source: dict[str, object]
    template: BatchTemplate | None
    requested_template_id: int
    type: str
    file_name: str
    status: str
    totals: BatchTotals
    received_at: datetime
    finished_at: datetime | None = None
    original_batch_id: int | None = None


class ValidationErrorResponse(BaseModel):
    id: int
    scope: str
    row_number: int | None = None
    field: str | None = None
    code: str
    message: str
    original_record_id: int | None = None
    created_at: datetime


class ValidationErrorList(BaseModel):
    total: int
    items: list[ValidationErrorResponse]
