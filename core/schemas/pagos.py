from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from typing import List, Optional
from datetime import date, datetime
from decimal import Decimal
from core.utils.enums import EstadoOrdenPago, EstadoLotePago, MonedaISO, CondicionFiscalAFIP

# ==========================================
# UTILIDADES DE VALIDACIÓN (FAIL-FAST)
# ==========================================
def validar_cuit_mod11(cuit: str) -> str:
    """Valida matemáticamente un CUIT argentino usando Módulo 11."""
    if not cuit.isdigit() or len(cuit) != 11:
        raise ValueError("El CUIT debe contener exactamente 11 dígitos numéricos.")

    base = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    calc = sum(int(cuit[i]) * base[i] for i in range(10))
    resto = calc % 11
    digito_verificador = 0 if resto == 0 else (9 if resto == 1 else 11 - resto)

    if digito_verificador != int(cuit[10]):
        raise ValueError(f"CUIT Inválido. Falla matemática en dígito verificador.")
    return cuit

# ==========================================
# ESQUEMAS MAESTROS (TAXONOMÍA Y B2B)
# ==========================================
class ConceptoOperativoCreate(BaseModel):
    codigo: str = Field(..., max_length=12)
    nombre_descriptivo: str = Field(..., max_length=100)

class ConceptoResponse(BaseModel):
    id: int
    codigo: str
    nombre_descriptivo: str
    model_config = ConfigDict(from_attributes=True)

class ContactoComercialBase(BaseModel):
    razon_social: str = Field(..., max_length=255)
    cuit: str = Field(..., min_length=11, max_length=11)
    cbu: Optional[str] = Field(None, min_length=22, max_length=22)
    is_proveedor: bool = True
    is_cliente: bool = False
    is_entidad_financiera: bool = False

    condicion_fiscal: CondicionFiscalAFIP = Field(
        default=CondicionFiscalAFIP.NO_CATEGORIZADO,
        description="Requisito estricto para la inferencia de Letras en Facturación B2B."
    )

class ContactoComercialCreate(ContactoComercialBase):
    @field_validator('cuit')
    @classmethod
    def validar_cuit(cls, v: str):
        return validar_cuit_mod11(v)

    @field_validator('cbu')
    @classmethod
    def validar_cbu(cls, v: Optional[str]):
        if v is not None:
            if not v.isdigit():
                raise ValueError("El CBU/CVU debe ser estrictamente numérico.")
            if len(v) != 22:
                raise ValueError("El CBU/CVU debe tener exactamente 22 dígitos.")
        return v

class ContactoComercialResponse(ContactoComercialBase):
    id: int
    is_active: bool
    model_config = ConfigDict(from_attributes=True)

# ==========================================
# ESQUEMAS LOGÍSTICA: ORDEN DE PAGO
# ==========================================
class OrdenPagoCreate(BaseModel):
    concepto_id: int
    proveedor_id: Optional[int] = Field(None, description="Opcional para Sifón Fiscal.")
    cuenta_contable_id: int = Field(..., description="Imputación contable obligatoria")
    factura_id: Optional[int] = Field(None, description="ID del comprobante existente a cancelar (si aplica)")

    monto_estimado: Decimal = Field(..., gt=0, description="El importe debe ser mayor a 0")
    moneda: MonedaISO = MonedaISO.ARS
    tipo_cambio_estimado: Decimal = Field(default=Decimal("1.0"), gt=0)

    requiere_comprobante_fiscal: bool = True
    comprobante_interno_url: Optional[str] = None
    numero_ticket: Optional[str] = Field(None, max_length=50, description="Número de remito/ticket físico")
    fast_track_cuenta_id: Optional[int] = Field(None, description="ID de la cuenta bancaria para liquidación instantánea")

    @model_validator(mode='after')
    def validar_sifon_fiscal(self) -> 'OrdenPagoCreate':
        if not self.requiere_comprobante_fiscal:
            if not self.comprobante_interno_url:
                raise ValueError(
                    "Operación bloqueada: Para procesar un egreso sin esperar a AFIP, "
                    "es obligatorio adjuntar la fotografía del ticket de resguardo."
                )
            if not self.numero_ticket or self.numero_ticket.strip() == "":
                raise ValueError(
                    "Operación bloqueada: Debe ingresar el Número de Ticket impreso en el comprobante físico."
                )
        return self
class OrdenPagoResponse(BaseModel):
    id: int
    codigo_trazabilidad: str
    concepto_id: int
    proveedor_id: int
    monto_estimado: Decimal
    moneda: MonedaISO
    estado_orden: EstadoOrdenPago
    requiere_comprobante_fiscal: bool
    excluir_reportes_fiscales: bool
    comprobante_interno_url: Optional[str] = None
    created_at: datetime
    creado_por_id: Optional[str] = None
    actualizado_por_id: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

# ==========================================
# ESQUEMAS FINANCIEROS: LOTE DE PAGO
# ==========================================
class LotePagoDetalleCreate(BaseModel):
    orden_pago_id: Optional[int] = None
    comprobante_id: Optional[int] = None
    monto_asignado_moneda_origen: Decimal
    monto_asignado_ars: Decimal
    tipo_cambio_aplicado: Decimal = Field(default=Decimal("1.0"), gt=0)

    @model_validator(mode='after')
    def validar_origen_detalle(self) -> 'LotePagoDetalleCreate':
        if not self.orden_pago_id and not self.comprobante_id:
            raise ValueError("El detalle del lote debe estar vinculado a una Orden o a un Comprobante.")
        return self

class LotePagoCreate(BaseModel):
    moneda_pago: MonedaISO = MonedaISO.ARS
    monto_total_lote: Decimal = Field(..., gt=0)
    detalles: List[LotePagoDetalleCreate] = Field(..., min_length=1)

class LoteOrdenPagoMinResponse(BaseModel):
    id: int
    codigo_trazabilidad: str
    monto_estimado: Decimal
    creado_por_id: Optional[str] = None
    comprobante_interno_url: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class LotePagoDetalleResponse(BaseModel):
    id: int
    orden_pago_id: Optional[int] = None
    monto_asignado_ars: Decimal
    orden_pago: Optional[LoteOrdenPagoMinResponse] = None
    model_config = ConfigDict(from_attributes=True)

class LotePagoResponse(BaseModel):
    id: int
    codigo_lote: str
    monto_total_lote: Decimal
    estado_lote: EstadoLotePago
    fecha_autorizacion: Optional[datetime]
    cuenta_bancaria_id: Optional[int] = None
    detalles: List[LotePagoDetalleResponse] = []
    model_config = ConfigDict(from_attributes=True)

# ==========================================
# ESQUEMAS DE MOTOR DE BÚSQUEDA Y FILTRADO
# ==========================================
class BuscadorEgresosQueryParams(BaseModel):
    fecha_inicio: date
    fecha_fin: date
    concepto_id: Optional[int] = None
    codigo_trazabilidad: Optional[str] = None
    monto_min: Optional[Decimal] = None
    monto_max: Optional[Decimal] = None
    q: Optional[str] = Field(None, description="Búsqueda libre por CUIT o Razón Social")
    limit: int = Field(50, ge=1, le=100)
    offset: int = Field(0, ge=0)

    @model_validator(mode='after')
    def proteger_motor_bd(self) -> 'BuscadorEgresosQueryParams':
        if self.fecha_inicio > self.fecha_fin:
            raise ValueError("La fecha de inicio no puede ser mayor a la fecha de fin.")

        delta_dias = (self.fecha_fin - self.fecha_inicio).days
        if delta_dias > 180:
            raise ValueError(
                f"Protección de Motor Activa: El rango de búsqueda no puede superar los 180 días. Solicitado: {delta_dias}."
            )
        return self

class AutorizarLoteRequest(BaseModel):
    cuenta_bancaria_id: int = Field(..., description="ID de la cuenta/caja de origen de los fondos")

# ==========================================
# ESQUEMAS DEL SIFÓN FISCAL (SIMULACIÓN AUTOMÁTICA)
# ==========================================
class SimularRetencionRequest(BaseModel):
    proveedor_id: int = Field(..., description="ID del beneficiario para cruce de padrones")
    facturas_ids: List[int] = Field(..., min_length=1, description="Lista inequívoca de comprobantes a cancelar")
    monto_bruto_abonar: Decimal = Field(..., gt=0, description="Monto bruto propuesto para la liquidación")

    # 🌟 FIX BIMONETARISMO: Variables vitales para inferir retenciones correctamente
    moneda_pago: MonedaISO = Field(default=MonedaISO.ARS)
    tipo_cambio: Decimal = Field(default=Decimal("1.0"), gt=0)

    @model_validator(mode='after')
    def validar_fx_rate(self) -> 'SimularRetencionRequest':
        if self.moneda_pago == MonedaISO.ARS and self.tipo_cambio != Decimal("1.0"):
            raise ValueError("Para pagos en ARS, el tipo de cambio debe ser estrictamente 1.0")
        if self.moneda_pago != MonedaISO.ARS and self.tipo_cambio <= Decimal("1.0"):
            raise ValueError(f"Para pagos en moneda extranjera ({self.moneda_pago}), el tipo de cambio debe ser mayor a 1.0")
        return self


class RetencionDetalleResponse(BaseModel):
    tipo_impuesto: str = Field(..., description="Naturaleza jurídica")
    jurisdiccion: str = Field(..., description="Ámbito territorial")
    alicuota_aplicada: Decimal = Field(..., ge=0, description="Porcentaje impositivo determinado por el padrón")
    monto_impuesto: Decimal = Field(..., ge=0, description="Monto neto a detraer del pago")


class SimularRetencionResponse(BaseModel):
    monto_bruto: Decimal
    retenciones_sugeridas: List[RetencionDetalleResponse]
    total_retenciones: Decimal
    neto_a_transferir: Decimal

    @model_validator(mode='after')
    def verificar_cuadratura_fiscal(self) -> 'SimularRetencionResponse':
        if self.neto_a_transferir != (self.monto_bruto - self.total_retenciones):
            raise ValueError("Inconsistencia en el balance fiscal: El neto resultante no coincide con el bruto menos retenciones.")
        return self

# ==========================================
# CREACIÓN DE ORDEN DE PAGO MÚLTIPLE
# ==========================================
class OrdenPagoMultipleCreate(BaseModel):
    proveedor_id: int
    facturas_ids: List[int] = Field(..., min_length=1)
    monto_bruto_abonar: Decimal = Field(..., gt=0)

    # 🌟 FIX ARQUITECTURA: Ahora es Optional[int] y el default es None.
    # Si llega None, se asume que es una Orden Encolada para el Hub Interbanking Masivo.
    cuenta_origen_id: Optional[int] = Field(default=None, description="ID de la cuenta bancaria. Vacío para encolar en Loteo Masivo.")

    # 🌟 FIX BIMONETARISMO: Variables vitales para la conciliación cruzada (FX)
    moneda_pago: MonedaISO = Field(default=MonedaISO.ARS)
    tipo_cambio: Decimal = Field(default=Decimal("1.0"), gt=0)

    retenciones: List[RetencionDetalleResponse] = []

    @model_validator(mode='after')
    def validar_fx_rate_orden(self) -> 'OrdenPagoMultipleCreate':
        if self.moneda_pago == MonedaISO.ARS and self.tipo_cambio != Decimal("1.0"):
            raise ValueError("Para liquidaciones en ARS, el tipo de cambio debe ser estrictamente 1.0")
        if self.moneda_pago != MonedaISO.ARS and self.tipo_cambio <= Decimal("1.0"):
            raise ValueError(f"Para liquidaciones en moneda extranjera ({self.moneda_pago}), registre un tipo de cambio real mayor a 1.0")
        return self