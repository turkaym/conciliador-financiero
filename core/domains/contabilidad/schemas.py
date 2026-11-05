from pydantic import BaseModel, ConfigDict
from typing import Optional

class PlanCuentasResponse(BaseModel):
    id: int
    codigo: str
    nombre: str
    tipo: str
    imputable: bool
    parent_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)