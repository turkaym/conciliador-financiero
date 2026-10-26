import csv
import hashlib
import io
import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from app.import_catalogs.schemas import order_columns


@dataclass(frozen=True)
class RowError:
    field: str | None
    code: str
    message: str


@dataclass(frozen=True)
class ParsedRow:
    row_number: int
    original: dict[str, str]
    values: dict[str, object]
    errors: tuple[RowError, ...]
    duplicate_key: bytes


@dataclass(frozen=True)
class ParsedFile:
    rows: tuple[ParsedRow, ...]
    file_error: RowError | None = None


def _row_key(record_type: str, source_id: int, original: dict[str, str]) -> bytes:
    identity = original.get("id_externo", "").strip()
    if identity:
        values = [("id_externo", identity)]
    else:
        values = list(original.items())
    payload = json.dumps(
        {"source_id": source_id, "type": record_type, "values": values},
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).digest()


def parse_csv(content: bytes, record_type: str, source_id: int, columns: list[tuple[str, str, bool]]) -> ParsedFile:
    try:
        text = content.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(text, newline=""))
        header = next(reader)
    except (UnicodeDecodeError, csv.Error, StopIteration):
        return ParsedFile((), RowError(None, "CABECERA_INCOMPATIBLE", "The CSV header could not be read"))

    expected = order_columns(record_type, [column[0] for column in columns])
    columns_by_name = {column[0]: column for column in columns}
    columns = [columns_by_name[column] for column in expected]
    if header != expected:
        return ParsedFile((), RowError(None, "CABECERA_INCOMPATIBLE", "The CSV header does not match the selected template"))

    rows: list[ParsedRow] = []
    try:
        for row_number, values in enumerate(reader, start=2):
            if len(values) != len(expected):
                return ParsedFile((), RowError(None, "ESTRUCTURA_INVALIDA", "A CSV row has an unexpected number of columns"))
            original = dict(zip(expected, values, strict=True))
            errors: list[RowError] = []
            typed: dict[str, object] = {}
            if any(value.startswith(("=", "+", "-", "@")) for value in values):
                errors.append(RowError(None, "FORMULA_NO_ADMITIDA", "Formula-like values are not accepted"))
            for field, data_type, required in columns:
                value = original[field]
                if required and not value.strip():
                    errors.append(RowError(field, "CAMPO_REQUERIDO", "Required field is empty"))
                    continue
                if not value.strip():
                    typed[field] = None
                    continue
                if data_type == "FECHA":
                    try:
                        typed[field] = date.fromisoformat(value)
                    except ValueError:
                        errors.append(RowError(field, "FECHA_INVALIDA", "Date must use YYYY-MM-DD"))
                elif data_type == "DECIMAL":
                    try:
                        amount = Decimal(value)
                        if amount <= 0:
                            errors.append(RowError(field, "MONTO_NO_POSITIVO", "Amount must be greater than zero"))
                        elif amount.as_tuple().exponent < -2:
                            errors.append(RowError(field, "MONTO_INVALIDO", "Amount allows at most two decimal places"))
                        else:
                            typed[field] = amount
                    except InvalidOperation:
                        errors.append(RowError(field, "MONTO_INVALIDO", "Amount is not a valid decimal"))
                elif field == "moneda" and value != "ARS":
                    errors.append(RowError(field, "MONEDA_NO_ADMITIDA", "Only ARS is accepted"))
                elif field == "tipo_movimiento" and value != "CREDITO":
                    errors.append(RowError(field, "TIPO_MOVIMIENTO_NO_ADMITIDO", "Only CREDITO is accepted"))
                elif field == "clase" and value not in {"VENTA", "COBRO"}:
                    errors.append(RowError(field, "CLASE_NO_ADMITIDA", "Only VENTA or COBRO is accepted"))
                else:
                    typed[field] = value
            rows.append(ParsedRow(row_number, original, typed, tuple(errors), _row_key(record_type, source_id, original)))
    except csv.Error:
        return ParsedFile((), RowError(None, "ESTRUCTURA_INVALIDA", "The CSV contains malformed quoting"))
    return ParsedFile(tuple(rows))
