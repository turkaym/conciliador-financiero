from typing import Generic, TypeVar

from pydantic import BaseModel


CANONICAL_COLUMN_ORDER = {
    "MOVIMIENTO": ("id_externo", "fecha", "monto", "moneda", "referencia", "tipo_movimiento"),
    "COMPROBANTE": ("id_externo", "fecha", "monto", "moneda", "referencia", "clase"),
}


def order_columns(record_type: str, columns: list[str]) -> list[str]:
    """Return approved columns first and unknown columns in stable order."""
    approved = CANONICAL_COLUMN_ORDER.get(record_type, ())
    ranks = {column: index for index, column in enumerate(approved)}
    return sorted(columns, key=lambda column: (ranks.get(column, len(approved)), column))


class CatalogItem(BaseModel):
    id: int
    code: str
    name: str
    type: str


class TemplateItem(BaseModel):
    id: int
    name: str
    type: str
    version: int
    columns: list[str]


Item = TypeVar("Item")


class CatalogList(BaseModel, Generic[Item]):
    page: int = 1
    page_size: int = 25
    total: int
    items: list[Item]
