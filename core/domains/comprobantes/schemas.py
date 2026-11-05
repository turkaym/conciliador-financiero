from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator, computed_field
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional, List
from enum import Enum
import re

from core.utils.normalizer import normalizar_moneda, normalizar_cuit
from core.utils.enums import ClaseDocumento, AlicuotaIvaAFIP, TipoTributoAFIP, CondicionFiscalAFIP

# ==========================================
# ENUMS DOMINIO COMPROBANTES
# ==========================================
class MonedaEnum(str, Enum):
    ARS = "ARS"
    USD = "USD"

# ==========================================
# ESTRUCTURAS INTERNAS (JSONB)
# ==========================================
class SubtotalIva(BaseModel):
    id_alicuota_afip: AlicuotaIvaAFIP
    base_imponible: Decimal = Field(default=Decimal('0.0'), ge=0)
    importe: Decimal = Field(default=Decimal('0.0'), ge=0)

class OtroTributo(BaseModel):
    id_tributo_afip: TipoTributoAFIP
    descripcion: Optional[str] = None
    base_imponible: Decimal = Field(default=Decimal('0.0'), ge=0)
    alicuota: Decimal = Field(default=Decimal('0.0'), ge=0)
    importe: Decimal = Field(default=Decimal('0.0'), ge=0)

class ComprobanteAsociadoCreate(BaseModel):
    tipo_cbte_afip: int = Field(gt=0)
    punto_venta: int = Field(gt=0, le=99999)
    numero: int = Field(gt=0, le=99999999)
    cuit: str = Field(pattern=r'^\d{11}$')

    @field_validator('cuit', mode='before')
    @classmethod
    def normalize_cuits_asoc(cls, v):
        return normalizar_cuit(v)

# ==========================================
# ESQUEMA BASE (Soporte Amnistía Histórica / Lectura Tolerante)
# ==========================================
class ComprobanteBase(BaseModel):
    entidad_id: int
    cuenta_contable_id: Optional[int] = Field(default=None, description="ID de la imputación contable en el Plan de Cuentas")

    tipo_operacion: str = Field(default="VENTA")
    clase_documento: ClaseDocumento = Field(default=ClaseDocumento.FACTURA)
    tipo_cbte_afip: Optional[int] = None

    # 🌟 FIX ARQUITECTURA: Relajación de lectura para documentos internos (Espejos OPs, Anticipos)
    # ge=0 (Greater or Equal) permite que Punto de Venta y Número sean 0 en lectura.
    punto_venta: int = Field(ge=0)
    numero: int = Field(ge=0)

    fecha_emision: date
    cuit_emisor: str = Field(pattern=r'^\d{11}$')
    cuit_receptor: str = Field(pattern=r'^\d{11}$')

    importe_neto_gravado: Decimal = Field(default=Decimal('0.0'), ge=0)
    importe_no_gravado: Decimal = Field(default=Decimal('0.0'), ge=0)
    importe_exento: Decimal = Field(default=Decimal('0.0'), ge=0)
    importe_total: Decimal = Field(..., ge=0)

    moneda: MonedaEnum = MonedaEnum.ARS
    cotizacion: Decimal = Field(default=Decimal('1.0'), gt=0)

    cae: Optional[str] = Field(default=None, pattern=r'^\d{14}$')
    vencimiento_cae: Optional[date] = None
    estado: str = "BORRADOR"
    comprobante_origen_id: Optional[int] = None

    es_fiscal: bool = Field(default=True, exclude=True)

    @field_validator('moneda', mode='before')
    @classmethod
    def normalize_currency(cls, v):
        return normalizar_moneda(v)

    @field_validator('cuit_emisor', 'cuit_receptor', mode='before')
    @classmethod
    def normalize_cuits(cls, v):
        return normalizar_cuit(v)

    @field_validator('fecha_emision', 'vencimiento_cae', mode='before')
    @classmethod
    def strict_date_format(cls, v):
        if not v: return None
        if isinstance(v, str):
            if len(v) == 8 and v.isdigit():
                v = f"{v[:4]}-{v[4:6]}-{v[6:]}"
            elif 'T' in v or 'Z' in v:
                raise ValueError("¡ALERTA DE TIMEZONE! Formato estricto 'YYYY-MM-DD' requerido.")
        return v

# ==========================================
# INGESTA ESTRICTA (Mutaciones/Payloads)
# ==========================================
class ComprobanteCreate(ComprobanteBase):
    # 🌟 Aquí SÍ se aplica la regla estricta AFIP (gt=0) para evitar que un humano cree facturas corruptas
    punto_venta: int = Field(gt=0, le=99999, description="Máximo 5 dígitos (Regla AFIP)")
    numero: int = Field(gt=0, le=99999999, description="Máximo 8 dígitos (Regla AFIP)")

    cuenta_contable_id: int = Field(..., description="ID de la imputación contable (Obligatorio)")
    saldo_pendiente: Optional[Decimal] = Field(default=None, ge=0)
    subtotales_iva: List[SubtotalIva] = Field(default_factory=list)
    otros_tributos: List[OtroTributo] = Field(default_factory=list)
    comprobantes_asociados: List[ComprobanteAsociadoCreate] = Field(default_factory=list)

    condicion_fiscal_receptor: Optional[CondicionFiscalAFIP] = None
    razon_social_receptor: Optional[str] = Field(default=None, max_length=255, description="Nombre o Razón Social para agendamiento B2B")

    condicion_venta: str = Field(default="CUENTA_CORRIENTE", description="CONTADO o CUENTA_CORRIENTE")
    cuenta_tesoreria_id: Optional[int] = Field(default=None, description="Requerido si condicion_venta es CONTADO")
    nomenclatura_afip_sugerida: Optional[str] = Field(default=None, description="Ej: FC-A 0001-00000054")

    @model_validator(mode='after')
    def validate_strict_ingest_contract(self):
        if self.condicion_venta == "CONTADO" and not self.cuenta_tesoreria_id:
            raise ValueError("Operación bloqueada: Para facturar al CONTADO, debe seleccionar la Caja o Billetera de destino.")

        if self.saldo_pendiente is not None:
            if self.saldo_pendiente != self.importe_total:
                raise ValueError(f"Fallo de Ingesta: En la creación inicial, el saldo pendiente ({self.saldo_pendiente}) debe ser matemáticamente igual al importe total ({self.importe_total}).")
        else:
            self.saldo_pendiente = self.importe_total

        if self.es_fiscal and self.nomenclatura_afip_sugerida:
            patron_estricto = r'^(FC|ND|NC|REC)-(A|B|C|M)\s\d{4,5}-\d{8}$'
            if not re.match(patron_estricto, self.nomenclatura_afip_sugerida):
                raise ValueError(f"Nomenclatura Fiscal Inválida: '{self.nomenclatura_afip_sugerida}'. Se esperaba formato AFIP (Ej: FC-A 0005-00000546).")

        if not self.es_fiscal:
            return self

        if self.importe_total > 0 and self.importe_neto_gravado == 0 and self.importe_exento == 0 and self.importe_no_gravado == 0 and not self.subtotales_iva:
            self.importe_neto_gravado = self.importe_total

        # 🌟 FIX DEUDA TÉCNICA: Se eliminó el bloque duplicado idéntico que existía aquí
        tolerancia = Decimal('0.05')
        suma_iva = sum((item.importe for item in self.subtotales_iva), Decimal('0.0'))
        suma_tributos = sum((item.importe for item in self.otros_tributos), Decimal('0.0'))
        calculado = self.importe_neto_gravado + self.importe_no_gravado + self.importe_exento + suma_iva + suma_tributos

        diferencia = abs(self.importe_total - calculado)
        if diferencia > tolerancia:
            raise ValueError(f"Descuadre matemático E2E. Declarado: {self.importe_total}. Suma interna: {calculado}. Diferencia: {diferencia}")

        return self

# ==========================================
# COMUNICACIÓN ASÍNCRONA
# ==========================================
class SyncTaskResponse(BaseModel):
    task_id: str
    status: str
    message: str

# ==========================================
# SALIDA (Ecosistema de Lectura)
# ==========================================
class ComprobanteResponse(ComprobanteBase):
    id: int
    saldo_pendiente: Decimal
    es_saldo_a_favor: bool
    is_active: bool
    legacy_fiscal_data: bool

    subtotales_iva: Optional[List[SubtotalIva]] = None
    otros_tributos: Optional[List[OtroTributo]] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    @computed_field
    @property
    def numero_formateado(self) -> str:
        # 🌟 FIX VISUAL UI: Manejo polimórfico explícito para los espejos de OPs
        if self.tipo_operacion == "ORDEN_PAGO_MIRROR":
            return f"OP-{self.numero}"

        afip_mapping = {
            1: "FC-A", 2: "ND-A", 3: "NC-A", 15: "REC-A",
            6: "FC-B", 7: "ND-B", 8: "NC-B", 16: "REC-B",
            11: "FC-C", 12: "ND-C", 13: "NC-C", 17: "REC-C",
            51: "FC-M", 52: "ND-M", 53: "NC-M", 54: "REC-M"
        }

        prefix = "CB"
        if self.tipo_cbte_afip and self.tipo_cbte_afip in afip_mapping:
            prefix = afip_mapping[self.tipo_cbte_afip]
        elif self.clase_documento:
            prefix = str(self.clase_documento)[:3].upper()
        else:
            prefix = "DOC"

        return f"{prefix} {self.punto_venta:05d}-{self.numero:08d}"

    @field_validator('created_at', 'updated_at', mode='after')
    @classmethod
    def ensure_utc_output(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v