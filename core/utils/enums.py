from enum import Enum

# ==========================================
# ENUMS CENTRALIZADOS (Migrados de schemas/banco.py)
# ==========================================
class TipoCanalEnum(str, Enum):
    BANCO = "BANCO"
    PASARELA = "PASARELA"

class TipoCuentaEnum(str, Enum):
    CC_ARS = "CC_ARS"
    CA_ARS = "CA_ARS"
    CC_USD = "CC_USD"
    CA_USD = "CA_USD"
    EFECTIVO = "EFECTIVO"
    BANCO = "BANCO"
    BILLETERA_VIRTUAL = "BILLETERA_VIRTUAL"
    CLEARING_VIRTUAL = "CLEARING_VIRTUAL"

class MonedaEnum(str, Enum):
    ARS = "ARS"
    USD = "USD"
    EUR = "EUR"

# ==========================================
# RESTO DEL CATÁLOGO ORIGINAL
# ==========================================
class CondicionFiscalAFIP(str, Enum):
    RESPONSABLE_INSCRIPTO = "RESPONSABLE_INSCRIPTO"
    MONOTRIBUTO = "MONOTRIBUTO"
    EXENTO = "EXENTO"
    CONSUMIDOR_FINAL = "CONSUMIDOR_FINAL"
    NO_CATEGORIZADO = "NO_CATEGORIZADO"

class RolUsuario(str, Enum):
    VISOR = "VISOR"
    EDITOR = "EDITOR"
    OPERADOR = "OPERADOR"
    DUEÑO = "DUEÑO"

class MonedaISO(str, Enum):
    ARS = "ARS"
    USD = "USD"
    EUR = "EUR"

class ClaseDocumento(str, Enum):
    FACTURA = "FACTURA"
    NOTA_CREDITO = "NOTA_CREDITO"
    NOTA_DEBITO = "NOTA_DEBITO"
    RECIBO = "RECIBO"
    REMITO = "REMITO"

class EstadoComprobante(str, Enum):
    BORRADOR = "BORRADOR"
    EMITIDO = "EMITIDO"
    PARCIAL = "PARCIAL"
    EN_PAGO = "EN_PAGO"
    PAGADA = "PAGADA"
    ANULADA = "ANULADA"

class TipoComprobanteAFIP(int, Enum):
    FACTURA_A = 1
    NOTA_DEBITO_A = 2
    NOTA_CREDITO_A = 3
    FACTURA_B = 6
    NOTA_DEBITO_B = 7
    NOTA_CREDITO_B = 8
    FACTURA_C = 11
    NOTA_DEBITO_C = 12
    NOTA_CREDITO_C = 13
    FACTURA_M = 51
    NOTA_DEBITO_M = 52
    NOTA_CREDITO_M = 53
    FACTURA_E = 19
    NOTA_DEBITO_E = 20
    NOTA_CREDITO_E = 21

    FCE_A = 201
    ND_FCE_A = 202
    NC_FCE_A = 203
    FCE_B = 206
    ND_FCE_B = 207
    NC_FCE_B = 208
    FCE_C = 211
    ND_FCE_C = 212
    NC_FCE_C = 213

    @classmethod
    def get_clase(cls, tipo: int) -> ClaseDocumento:
        if tipo in [1, 6, 11, 19, 51, 201, 206, 211]:
            return ClaseDocumento.FACTURA
        if tipo in [3, 8, 13, 21, 53, 203, 208, 213]:
            return ClaseDocumento.NOTA_CREDITO
        if tipo in [2, 7, 12, 20, 52, 202, 207, 212]:
            return ClaseDocumento.NOTA_DEBITO
        return ClaseDocumento.FACTURA

class AlicuotaIvaAFIP(int, Enum):
    CERO = 3
    DIEZ_COMA_CINCO = 4
    VEINTIUNO = 5
    VEINTISIETE = 6
    CINCO = 8
    DOS_COMA_CINCO = 9

class TipoTributoAFIP(int, Enum):
    IMPUESTOS_NACIONALES = 1
    IMPUESTOS_PROVINCIALES = 2
    IMPUESTOS_MUNICIPALES = 3
    IMPUESTOS_INTERNOS = 4
    OTRO = 99

class EstadoOrdenPago(str, Enum):
    BORRADOR = "BORRADOR"
    ESPERANDO_FACTURA = "ESPERANDO_FACTURA"
    FACTURA_ASIGNADA = "FACTURA_ASIGNADA"
    EN_LOTE = "EN_LOTE"
    PENDIENTE_AUTORIZACION = "PENDIENTE_AUTORIZACION"
    AUTORIZADA = "AUTORIZADA"
    PAGADA = "PAGADA"
    ANULADA = "ANULADA"

class EstadoLotePago(str, Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    AUTHORIZED_FOR_PAYMENT = "AUTHORIZED_FOR_PAYMENT"
    ESPERANDO_REINTENTO = "ESPERANDO_REINTENTO"
    PAID = "PAID"
    VOIDED = "VOIDED"

class TipoCuentaTesoreria(str, Enum):
    EFECTIVO = "EFECTIVO"
    BANCO = "BANCO"
    BILLETERA_VIRTUAL = "BILLETERA_VIRTUAL"
    CLEARING_VIRTUAL = "CLEARING_VIRTUAL"

class TipoMovimientoTesoreria(str, Enum):
    INGRESO = "INGRESO"
    EGRESO = "EGRESO"

class TipoComprobanteInterno(int, Enum):
    MOVIMIENTO_MANUAL = 9001
    GASTO_MENOR = 9002
    LOTE_PAGO = 9003

class NomenclaturaFiscal:
    @classmethod
    def get_nomenclatura(cls, tipo_cbte_afip, clase_documento, punto_venta: int, numero: int) -> str:
        afip_mapping = {
            1: "FC-A", 2: "ND-A", 3: "NC-A", 15: "REC-A",
            6: "FC-B", 7: "ND-B", 8: "NC-B", 16: "REC-B",
            11: "FC-C", 12: "ND-C", 13: "NC-C", 17: "REC-C",
            51: "FC-M", 52: "ND-M", 53: "NC-M", 54: "REC-M"
        }

        prefix = "CB"
        if tipo_cbte_afip and tipo_cbte_afip in afip_mapping:
            prefix = afip_mapping[tipo_cbte_afip]
        elif clase_documento:
            doc_str = str(getattr(clase_documento, 'value', clase_documento))
            prefix = doc_str[:3].upper()
        else:
            prefix = "DOC"

        return f"{prefix} {punto_venta:05d}-{numero:08d}"