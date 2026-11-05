from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from core.utils.enums import CondicionFiscalAFIP

class TenantCreate(BaseModel):
    name: str = Field(..., description="Nombre comercial o Razón Social del inquilino")
    cuit: str = Field(..., min_length=11, max_length=11, description="CUIT sin guiones")

    # 🌟 FIX FASE 11: Inyección estricta de Condición Fiscal en la creación del Tenant
    condicion_fiscal: CondicionFiscalAFIP = Field(
        ...,
        description="Condición fiscal inmutable ante AFIP (Determina la letra de facturación E2E)"
    )

    schema_name: Optional[str] = Field(None, description="Opcional. Si se omite, se autogenera.")

class TenantResponse(BaseModel):
    id: int
    name: str
    cuit: str
    schema_name: str
    is_active: bool
    condicion_fiscal: CondicionFiscalAFIP

    # use_enum_values=True garantiza que el JSON exponga el String legible (Ej: "RESPONSABLE_INSCRIPTO")
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)