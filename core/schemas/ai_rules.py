from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RuleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tipo_regla: Literal["concepto_cuit"]
    patron_concepto: str = Field(min_length=2, max_length=255)
    cuit_asociado: str
    tipo_cbte_asociado: Optional[int] = Field(default=None, ge=1, le=999)

    @field_validator("patron_concepto")
    @classmethod
    def normalize_pattern(cls, value: str) -> str:
        return " ".join(value.upper().split())

    @field_validator("cuit_asociado")
    @classmethod
    def normalize_cuit(cls, value: str) -> str:
        normalized = value.replace("-", "").replace(" ", "")
        if len(normalized) != 11 or not normalized.isdigit():
            raise ValueError("invalid CUIT")
        return normalized


class RuleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    activa: bool
    expected_updated_at: datetime


class RuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tipo_regla: Literal["concepto_cuit"] = "concepto_cuit"
    entidad_id: int
    patron_concepto: str
    cuit_asociado: Optional[str]
    tipo_cbte_asociado: Optional[int]
    frecuencia_uso: int
    activa: bool
    created_at: datetime
    updated_at: datetime


class RuleList(BaseModel):
    items: list[RuleResponse]
    total: int
    limit: int
    offset: int
