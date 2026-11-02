from pydantic import BaseModel, ConfigDict, Field, field_validator, AliasChoices
from datetime import date
from decimal import Decimal
from typing import Optional, List, Literal
from core.utils.normalizer import normalizar_moneda
from core.utils.enums import TipoCanalEnum, TipoCuentaEnum, MonedaEnum

# ==========================================
# ESQUEMAS BASE (Atributos Compartidos)
# ==========================================
class CuentaBancariaBase(BaseModel):
    banco: str = Field(..., min_length=2, max_length=50)
    tipo_canal: TipoCanalEnum = Field(default=TipoCanalEnum.BANCO)
    numero_cuenta: str = Field(..., min_length=5, max_length=50)
    cbu: Optional[str] = Field(None, min_length=22, max_length=22)
    alias: Optional[str] = None
    tipo_cuenta: TipoCuentaEnum
    moneda: MonedaEnum = MonedaEnum.ARS

    is_virtual_clearing: bool = Field(default=False, description="Habilita la auto-emisión fiscal de comisiones")
    proveedor_clearing_id: Optional[int] = Field(default=None, description="ID del proveedor de clearing en tabla de contactos")

    # 🌟 FIX ARQUITECTURA: Permitir que el frontend envíe explícitamente la cuenta contable
    cuenta_contable_id: Optional[int] = Field(default=None, description="ID de la imputación contable para partida doble")

    @field_validator('moneda', mode='before')
    @classmethod
    def apply_normalization(cls, v):
        return normalizar_moneda(v)

    model_config = ConfigDict(use_enum_values=True)

class MovimientoBancarioBase(BaseModel):
    cuenta_id: int
    cuenta_contable_id: Optional[int] = Field(default=None, description="ID de la imputación contable")
    fecha: date
    monto: Decimal = Field(..., max_digits=15, decimal_places=2)
    moneda: MonedaEnum = MonedaEnum.ARS

    # 🌟 FIX FASE 3.1: Pydantic leerá 'referencia_externa' de la DB automáticamente
    referencia_banco: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices('referencia_banco', 'referencia_externa')
    )

    usuario_resolutor_id: Optional[str] = None
    motivo_rechazo: Optional[str] = None

    @field_validator('monto')
    @classmethod
    def prevent_zero_amount(cls, v):
        if v == Decimal('0.00'):
            raise ValueError("[BUSINESS_LOGIC] Un movimiento bancario no puede ser de $0.00")
        return v

    model_config = ConfigDict(use_enum_values=True)

# ==========================================
# ESQUEMAS DE PETICIÓN (Frontend/Parsers -> API)
# ==========================================
class CuentaBancariaRequest(CuentaBancariaBase):
    saldo_actual: Decimal = Field(default=Decimal("0.00"), max_digits=15, decimal_places=2)

class MovimientoBancarioRequest(MovimientoBancarioBase):
    cuenta_contable_id: int = Field(..., description="ID de la imputación contable (Obligatorio)")
    concepto_bancario_crudo: str = Field(..., description="La leyenda exacta que arrojó el TXT/CSV del banco")
    concepto_interno: Optional[str] = Field(None, description="Leyenda agregada por el operador (Opcional)")

# ==========================================
# ESQUEMAS INTERNOS (API -> DB)
# ==========================================
class CuentaBancariaCreate(CuentaBancariaRequest):
    entidad_id: int

class MovimientoBancarioCreate(MovimientoBancarioRequest):
    entidad_id: int
    saldo_resultante: Optional[Decimal] = None
    estado: str = "APROBADO"

# ==========================================
# ESQUEMAS DE RESPUESTA (DB -> API -> Frontend)
# ==========================================
class CuentaBancariaResponse(CuentaBancariaBase):
    id: int
    tipo_canal: TipoCanalEnum
    saldo_actual: Decimal
    saldo_retenido: Decimal = Decimal("0.00")
    is_syncing: bool
    last_task_id: Optional[str] = None
    progress: Optional[int] = None
    status_msg: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

class MovimientoBancarioResponse(MovimientoBancarioBase):
    id: int
    tipo_registro: Literal["MOVIMIENTO", "SOLICITUD"] = "MOVIMIENTO"

    # 🌟 FIX FASE 3.1: Pydantic leerá 'concepto_crudo' de la DB automáticamente
    concepto_bancario_crudo: str = Field(
        validation_alias=AliasChoices('concepto_bancario_crudo', 'concepto_crudo')
    )

    concepto_interno: Optional[str] = None
    saldo_resultante: Optional[Decimal] = None
    conciliado: bool = Field(
        default=False,
        validation_alias=AliasChoices('conciliado', 'es_conciliado', 'is_conciliado')
    )
    estado: str = "APROBADO"
    usuario_creador_id: Optional[str] = None
    usuario_resolutor_id: Optional[str] = None
    motivo_rechazo: Optional[str] = None
    usuario_creador_nombre: Optional[str] = None
    usuario_resolutor_nombre: Optional[str] = None

    # populate_by_name=True es vital aquí para que los alias funcionen en ambas direcciones
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, use_enum_values=True)

class MovimientosPaginadosResponse(BaseModel):
    items: List[MovimientoBancarioResponse]
    total_count: int
    page: int
    has_more: bool