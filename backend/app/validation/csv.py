import csv
import hashlib
import io
import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

@dataclass(frozen=True)
class RowError:
    field: str | None
    code: str
    message: str


@dataclass(frozen=True)
class ParsedRow:
    row_number: int
    original: dict[str, str]
    canonical: dict[str, str]
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


def _decode(content: bytes) -> str:
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return content.decode("cp1252")


def _parse_date(value: str, date_format: str | None) -> date:
    formats = {
        "DD/MM/YYYY": "%d/%m/%Y",
        "YYYY-MM-DD": "%Y-%m-%d",
        "DD-MM-YYYY": "%d-%m-%Y",
    }
    if date_format in formats:
        return datetime.strptime(value, formats[date_format]).date()
    if date_format == "ISO_DATETIME":
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    return date.fromisoformat(value)


def _parse_decimal(value: str, decimal_separator: str | None) -> Decimal:
    normalized = value.strip().replace("\u00a0", "").replace(" ", "")
    if decimal_separator == ",":
        normalized = normalized.replace(".", "").replace(",", ".")
    elif decimal_separator == ".":
        normalized = normalized.replace(",", "")
    return Decimal(normalized)


def parse_csv(
    content: bytes,
    record_type: str,
    source_id: int,
    columns: list[tuple[str, str, str, bool, str | None, str | None]],
) -> ParsedFile:
    try:
        text = _decode(content)
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
        reader = csv.reader(io.StringIO(text, newline=""), dialect)
        header = next(reader)
    except (UnicodeDecodeError, csv.Error, StopIteration):
        return ParsedFile((), RowError(None, "CABECERA_INCOMPATIBLE", "The CSV header could not be read"))

    expected = [column[0] for column in columns]
    missing = [column for column in expected if column not in header]
    if missing:
        return ParsedFile((), RowError(None, "CABECERA_INCOMPATIBLE", f"The CSV header does not match the selected source. Expected: {', '.join(expected)}"))

    rows: list[ParsedRow] = []
    try:
        for row_number, values in enumerate(reader, start=2):
            if len(values) != len(header):
                return ParsedFile((), RowError(None, "ESTRUCTURA_INVALIDA", "A CSV row has an unexpected number of columns"))
            original = dict(zip(header, values, strict=True))
            canonical = {
                canonical_field: original[source_column]
                for source_column, canonical_field, *_rest in columns
            }
            errors: list[RowError] = []
            typed: dict[str, object] = {}
            if any(value.startswith(("=", "+", "-", "@")) for value in values):
                errors.append(RowError(None, "FORMULA_NO_ADMITIDA", "Formula-like values are not accepted"))
            for field, canonical_field, data_type, required, date_format, decimal_separator in columns:
                value = original[field]
                if required and not value.strip():
                    errors.append(RowError(field, "CAMPO_REQUERIDO", "Required field is empty"))
                    continue
                if not value.strip():
                    typed[field] = None
                    continue
                if data_type == "FECHA":
                    try:
                        typed[canonical_field] = _parse_date(value, date_format)
                    except ValueError:
                        expected_format = date_format or "YYYY-MM-DD"
                        errors.append(RowError(field, "FECHA_INVALIDA", f"Date must use {expected_format}"))
                elif data_type == "DECIMAL":
                    try:
                        amount = _parse_decimal(value, decimal_separator)
                        if amount <= 0:
                            errors.append(RowError(field, "MONTO_NO_POSITIVO", "Amount must be greater than zero"))
                        elif amount.as_tuple().exponent < -2:
                            errors.append(RowError(field, "MONTO_INVALIDO", "Amount allows at most two decimal places"))
                        else:
                            typed[canonical_field] = amount
                    except InvalidOperation:
                        errors.append(RowError(field, "MONTO_INVALIDO", "Amount is not a valid decimal"))
                elif canonical_field == "moneda" and value != "ARS":
                    errors.append(RowError(field, "MONEDA_NO_ADMITIDA", "Only ARS is accepted"))
                elif canonical_field == "tipo_movimiento" and value != "CREDITO":
                    errors.append(RowError(field, "TIPO_MOVIMIENTO_NO_ADMITIDO", "Only CREDITO is accepted"))
                elif canonical_field == "clase" and value not in {"VENTA", "COBRO"}:
                    errors.append(RowError(field, "CLASE_NO_ADMITIDA", "Only VENTA or COBRO is accepted"))
                else:
                    typed[canonical_field] = value
            rows.append(ParsedRow(row_number, original, canonical, typed, tuple(errors), _row_key(record_type, source_id, canonical)))
    except csv.Error:
        return ParsedFile((), RowError(None, "ESTRUCTURA_INVALIDA", "The CSV contains malformed quoting"))
    return ParsedFile(tuple(rows))
