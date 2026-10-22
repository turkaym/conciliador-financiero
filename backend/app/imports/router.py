import hashlib
from datetime import datetime, timezone
from typing import Annotated

from email import policy
from email.parser import BytesParser

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.access.security import get_current_user
from app.database import get_db
from app.errors import ApiError
from app.import_catalogs.router import _api_type
from app.imports.schemas import BatchResponse, BatchTemplate, BatchTotals
from app.models import DataSource, ImportBatch, ImportTemplate, User

router = APIRouter(prefix="/batches", tags=["batches"])


def _response(batch: ImportBatch, source: DataSource, template: ImportTemplate | None) -> BatchResponse:
    return BatchResponse(
        id=batch.id,
        source={"id": source.id, "code": source.code, "name": source.name, "type": _api_type(source.source_type)},
        template=(BatchTemplate(id=template.id, name=template.name, version=template.version) if template else None),
        requested_template_id=int(batch.requested_template),
        type=batch.batch_type,
        file_name=batch.file_name,
        status=batch.status,
        totals=BatchTotals(),
        received_at=batch.received_at,
        finished_at=batch.finished_at,
    )


@router.post("", response_model=BatchResponse, status_code=202)
async def submit_batch(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    content_type = request.headers.get("content-type", "")
    if not content_type.startswith("multipart/form-data"):
        raise ApiError(400, "INVALID_MULTIPART", "Expected multipart/form-data")
    body = await request.body()
    message = BytesParser(policy=policy.default).parsebytes(
        f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode() + body
    )
    fields: dict[str, str] = {}
    file_name: str | None = None
    file_content: bytes | None = None
    if not message.is_multipart():
        raise ApiError(400, "INVALID_MULTIPART", "Malformed multipart request")
    for part in message.iter_parts():
        field_name = part.get_param("name", header="content-disposition")
        if not field_name or field_name in fields or (field_name == "file" and file_content is not None):
            raise ApiError(400, "INVALID_MULTIPART", "Malformed multipart request")
        filename = part.get_param("filename", header="content-disposition")
        value = part.get_payload(decode=True) or b""
        if filename is not None:
            if field_name != "file":
                raise ApiError(400, "INVALID_MULTIPART", "Unexpected file field")
            file_name = filename
            file_content = value
        else:
            fields[field_name] = value.decode("utf-8", errors="strict")
    try:
        source_id = int(fields["source_id"])
        template_id = int(fields["template_id"])
        type = fields["type"]
    except (KeyError, ValueError, UnicodeDecodeError):
        raise ApiError(422, "INVALID_BATCH_REQUEST", "Missing or invalid batch fields") from None
    if source_id <= 0 or template_id <= 0 or file_name is None or file_content is None:
        raise ApiError(422, "INVALID_BATCH_REQUEST", "Missing or invalid batch fields")
    if type not in {"MOVIMIENTO", "COMPROBANTE"}:
        raise ApiError(422, "INVALID_BATCH_TYPE", "Unsupported batch type")
    if not file_name.lower().endswith(".csv"):
        raise ApiError(422, "INVALID_FILE_TYPE", "The uploaded file must be a CSV")
    content = file_content
    if not content:
        raise ApiError(422, "EMPTY_FILE", "The uploaded file is empty")
    source = db.scalar(select(DataSource).where(DataSource.id == source_id, DataSource.active.is_(True)))
    if source is None:
        raise ApiError(404, "SOURCE_NOT_FOUND", "Source not found")
    template = db.scalar(
        select(ImportTemplate).where(
            ImportTemplate.id == template_id,
            ImportTemplate.source_id == source_id,
            ImportTemplate.template_type == type,
            ImportTemplate.active.is_(True),
        )
    )
    if template is None:
        raise ApiError(404, "TEMPLATE_NOT_FOUND", "Template not found")

    batch = ImportBatch(
        source_id=source_id,
        template_id=template_id,
        requested_template=str(template_id),
        user_id=user.id,
        batch_type=type,
        file_name=file_name,
        file_hash=hashlib.sha256(content).digest(),
        file_content=content,
        status="RECIBIDO",
        received_at=datetime.now(timezone.utc),
    )
    try:
        db.add(batch)
        db.commit()
        db.refresh(batch)
    except IntegrityError:
        db.rollback()
        raise ApiError(409, "DUPLICATE_BATCH", "The same file was already submitted") from None
    return _response(batch, source, template)


@router.get("/{batch_id}", response_model=BatchResponse)
def inspect_batch(
    batch_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    batch = db.scalar(select(ImportBatch).where(ImportBatch.id == batch_id, ImportBatch.user_id == user.id))
    if batch is None:
        raise ApiError(404, "BATCH_NOT_FOUND", "Batch not found")
    source = db.get(DataSource, batch.source_id)
    template = db.get(ImportTemplate, batch.template_id) if batch.template_id else None
    return _response(batch, source, template)
