from pydantic import BaseModel, ConfigDict, Field
from decimal import Decimal
from typing import Optional

class ImpuestoCalculado(BaseModel):
    """DTO de salida del Motor de Retenciones. Inmutable y validado."""
    tipo_impuesto: str = Field(..., description="Ej: RETENCION_IIBB, PERCEPCION_IVA")
    jurisdiccion: str = Field(..., description="Ej: ARBA, AGIP, AFIP")
    codigo_regimen_afip: int = Field(default=217, description="Código de régimen asociado a la regla")

    # 🌟 FIX RESILIENCIA: Barreras matemáticas de límite inferior (ge=0)
    base_imponible: Decimal = Field(..., ge=0, description="Monto base sobre el cual se calcula el impuesto")
    alicuota_aplicada: Decimal = Field(..., ge=0, description="Porcentaje aplicado (Ej: 1.5)")
    monto_impuesto: Decimal = Field(..., ge=0, description="Monto final a retener/percibir")

    # 🌟 FIX DOCUMENTACIÓN Y FORENSE: Refleja la nueva lógica de contingencia
    origen_alicuota: str = Field(..., description="Traza de la regla: Ej: PADRON_ARBA, PADRON_AGIP_MES_ANTERIOR, REGLA_DEFECTO")
    cuenta_contable_id: Optional[int] = None
    id_regla_aplicada: Optional[int] = Field(None, description="ID de la regla original que disparó este impuesto (Snapshot Forense)")

    model_config = ConfigDict(from_attributes=True)

class ReglaImpuestoCreate(BaseModel):
    """Payload para configurar una nueva regla dinámica en la entidad."""
    tipo_impuesto: str
    jurisdiccion: str
    codigo_regimen_afip: int = Field(default=217, description="Código oficial del régimen (Ej: 217 para SICORE/SIRE)")
    alicuota_defecto: Decimal = Field(ge=0)
    monto_minimo_sujeto: Decimal = Field(ge=0)
    aplica_padron: bool = False
    cuenta_contable_id: Optional[int] = None

class ReglaImpuestoUpdate(BaseModel):
    """Payload para actualizar o desactivar reglas existentes (Arquitectura RESTful)."""
    codigo_regimen_afip: Optional[int] = None
    alicuota_defecto: Optional[Decimal] = Field(None, ge=0)
    monto_minimo_sujeto: Optional[Decimal] = Field(None, ge=0)
    aplica_padron: Optional[bool] = None
    is_active: Optional[bool] = None
    cuenta_contable_id: Optional[int] = None

class ReglaImpuestoResponse(ReglaImpuestoCreate):
    id: int
    entidad_id: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)

# ==========================================
# EXPORTACIÓN POSICIONAL (SIRE / ARCA)
# ==========================================
from core.utils.txt_exporter import FixedWidthModel

class LineaExportacionSIRE(FixedWidthModel):
    """
    Representación exacta de un registro de retención según el diseño
    de registro de ancho fijo provisto por ARCA / AFIP para el aplicativo SIRE.
    """
    tipo_registro: int = Field(1, json_schema_extra={"width": 1, "padding": "0", "alignment": ">"})
    fecha_retencion: str = Field(..., description="Formato DD/MM/YYYY", json_schema_extra={"width": 10, "padding": " "})
    tipo_comprobante_origen: str = Field(..., description="Código AFIP del documento", json_schema_extra={"width": 3, "padding": "0", "alignment": ">"})
    numero_comprobante_origen: str = Field(..., description="Número completo sin guiones", json_schema_extra={"width": 16, "padding": "0", "alignment": ">"})
    monto_comprobante_origen: Decimal = Field(..., json_schema_extra={"width": 16, "padding": "0", "alignment": ">"})
    codigo_regimen: int = Field(..., json_schema_extra={"width": 3, "padding": "0", "alignment": ">"})
    cuit_sujeto_retenido: str = Field(..., json_schema_extra={"width": 11, "padding": " "})
    base_imponible: Decimal = Field(..., json_schema_extra={"width": 14, "padding": "0", "alignment": ">"})
    monto_retencion: Decimal = Field(..., json_schema_extra={"width": 14, "padding": "0", "alignment": ">"})
    numero_certificado: str = Field(..., json_schema_extra={"width": 14, "padding": "0", "alignment": ">"})