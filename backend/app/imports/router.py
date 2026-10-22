import hashlib
from datetime import datetime, timezone
from typing import Annotated

from email import policy
from email.parser import BytesParser

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.access.security import get_current_user
from app.database import get_db
from app.errors import ApiError
from app.import_catalogs.router import _api_type
from app.imports.schemas import BatchResponse, BatchTemplate, BatchTotals, ValidationErrorList, ValidationErrorResponse
from app.models import (
    BankMovement,
    DataSource,
    ImportedRecord,
    ImportBatch,
    ImportTemplate,
    Receipt,
    TemplateField,
    User,
    ValidationError,
)
from app.validation.csv import ParsedFile, RowError, parse_csv

router = APIRouter(prefix="/batches", tags=["batches"])


def _response(batch: ImportBatch, source: DataSource, template: ImportTemplate | None) -> BatchResponse:
    total_rows = 0
    valid_rows = 0
    invalid_rows = 0
    # The response helper is also used before processing in older callers.
    if hasattr(batch, "_totals"):
        total_rows, valid_rows, invalid_rows = batch._totals
    return BatchResponse(
        id=batch.id,
        source={"id": source.id, "code": source.code, "name": source.name, "type": _api_type(source.source_type)},
        template=(BatchTemplate(id=template.id, name=template.name, version=template.version) if template else None),
        requested_template_id=int(batch.requested_template),
        type=batch.batch_type,
        file_name=batch.file_name,
        status=batch.status,
        totals=BatchTotals(total_rows=total_rows, valid_rows=valid_rows, invalid_rows=invalid_rows),
        received_at=batch.received_at,
        finished_at=batch.finished_at,
        original_batch_id=batch.original_batch_id,
    )


def _template_columns(db: Session, template: ImportTemplate) -> list[tuple[str, str, bool]]:
    fields = db.scalars(select(TemplateField).where(TemplateField.template_id == template.id).order_by(TemplateField.id)).all()
    defaults = {
        "id_externo": ("TEXTO", False), "fecha": ("FECHA", True), "monto": ("DECIMAL", True),
        "moneda": ("MONEDA", True), "referencia": ("TEXTO", False), "tipo_movimiento": ("CATEGORIA", True),
        "clase": ("CATEGORIA", True),
    }
    return [(field.source_column, field.data_type or defaults.get(field.canonical_field, ("TEXTO", True))[0], field.required if field.required is not None else defaults.get(field.canonical_field, ("TEXTO", True))[1]) for field in fields]


def _set_totals(db: Session, batch: ImportBatch) -> None:
    total = db.scalar(select(func.count()).select_from(ImportedRecord).where(ImportedRecord.batch_id == batch.id)) or 0
    invalid = db.scalar(select(func.count()).select_from(ImportedRecord).where(ImportedRecord.batch_id == batch.id, ImportedRecord.status == "INVALIDO")) or 0
    batch._totals = (total, total - invalid, invalid)


def _process_batch(db: Session, batch: ImportBatch, template: ImportTemplate) -> None:
    batch.status = "EN_VALIDACION"
    parsed: ParsedFile = parse_csv(batch.file_content, batch.batch_type, batch.source_id, _template_columns(db, template))
    if parsed.file_error:
        db.add(ValidationError(batch_id=batch.id, scope="LOTE", code=parsed.file_error.code, message=parsed.file_error.message))
        batch.status = "FALLIDO"
        batch.finished_at = datetime.now(timezone.utc)
        return
    seen: dict[bytes, ImportedRecord] = {}
    for row in parsed.rows:
        duplicate = seen.get(row.duplicate_key)
        errors = list(row.errors)
        if duplicate is not None:
            errors.append(RowError(None, "ID_EXTERNO_DUPLICADO" if row.original.get("id_externo", "").strip() else "HUELLA_FILA_DUPLICADA", "The row duplicates an earlier row in this batch"))
        record = ImportedRecord(
            batch_id=batch.id, source_id=batch.source_id, row_number=row.row_number, record_type=batch.batch_type,
            status="INVALIDO" if errors else "PENDIENTE", external_id=row.original.get("id_externo", "").strip() or None,
            duplicate_key=row.duplicate_key, original_record_id=duplicate.id if duplicate and errors else None,
            original_data=row.original,
        )
        db.add(record)
        db.flush()
        if not errors:
            if batch.batch_type == "MOVIMIENTO":
                db.add(BankMovement(record_id=record.id, date=row.values["fecha"], amount=row.values["monto"], currency=row.values["moneda"], normalized_reference=None, is_credit=True))
            else:
                db.add(Receipt(record_id=record.id, date=row.values["fecha"], amount=row.values["monto"], currency=row.values["moneda"], normalized_reference=None, category=row.values["clase"]))
            seen[row.duplicate_key] = record
        for error in errors:
            db.add(ValidationError(batch_id=batch.id, record_id=record.id, scope="FILA", field=error.field, code=error.code, message=error.message, original_record_id=duplicate.id if duplicate else None))
    total = len(parsed.rows)
    invalid = sum(bool(row.errors) or row.duplicate_key in {r.duplicate_key for r in parsed.rows[:i]} for i, row in enumerate(parsed.rows))
    batch.status = "PROCESADO_SIN_VALIDOS" if invalid == total else ("PROCESADO_CON_ERRORES" if invalid else "PROCESADO")
    batch.finished_at = datetime.now(timezone.utc)


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

    file_hash = hashlib.sha256(content).digest()
    original = db.scalar(select(ImportBatch).where(ImportBatch.source_id == source_id, ImportBatch.batch_type == type, ImportBatch.file_hash == file_hash, ImportBatch.status != "FALLIDO"))
    batch = ImportBatch(
        source_id=source_id,
        template_id=template_id,
        requested_template=str(template_id),
        user_id=user.id,
        batch_type=type,
        file_name=file_name,
        file_hash=file_hash,
        file_content=content,
        status="RECIBIDO",
        received_at=datetime.now(timezone.utc),
    )
    if original is not None:
        batch.status = "DUPLICADO"
        batch.original_batch_id = original.id
        batch.finished_at = datetime.now(timezone.utc)
        db.add(batch)
        db.commit()
        db.refresh(batch)
        batch._totals = (0, 0, 0)
        return _response(batch, source, template)
    try:
        db.add(batch)
        db.flush()
        _process_batch(db, batch, template)
        db.commit()
        db.refresh(batch)
    except IntegrityError:
        db.rollback()
        raise ApiError(409, "DUPLICATE_BATCH", "The same file was already submitted") from None
    _set_totals(db, batch)
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
    _set_totals(db, batch)
    return _response(batch, source, template)


@router.get("/{batch_id}/errors", response_model=ValidationErrorList)
def list_batch_errors(
    batch_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    batch = db.scalar(select(ImportBatch).where(ImportBatch.id == batch_id, ImportBatch.user_id == user.id))
    if batch is None:
        raise ApiError(404, "BATCH_NOT_FOUND", "Batch not found")
    errors = db.scalars(select(ValidationError).where(ValidationError.batch_id == batch_id).order_by(ValidationError.id)).all()
    row_numbers = {record.id: record.row_number for record in db.scalars(select(ImportedRecord).where(ImportedRecord.batch_id == batch_id)).all()}
    return ValidationErrorList(total=len(errors), items=[ValidationErrorResponse(id=error.id, scope=error.scope, row_number=row_numbers.get(error.record_id), field=error.field, code=error.code, message=error.message, original_record_id=error.original_record_id, created_at=error.created_at) for error in errors])
