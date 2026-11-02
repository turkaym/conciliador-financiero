from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional

class PeriodoBase(BaseModel):
    anio: int = Field(..., ge=2020, le=2100, description="Año fiscal (ej: 2026)")
    mes: int = Field(..., ge=1, le=12, description="Mes del 1 al 12")

class PeriodoCierreRequest(PeriodoBase):
    pass

class PeriodoResponse(PeriodoBase):
    id: int
    estado: str
    cerrado_por_id: Optional[int] = None # 🌟 FIX: Ajustado al modelo ORM
    cerrado_el: datetime # 🌟 FIX: Ajustado al modelo ORM

    model_config = ConfigDict(from_attributes=True)