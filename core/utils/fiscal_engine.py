from core.utils.enums import CondicionFiscalAFIP, ClaseDocumento

class MotorInferenciaFiscal:
    """
    Cerebro de deducción tributaria.
    Cruza Emisor vs Receptor para erradicar la selección manual de comprobantes,
    previniendo rechazos (HTTP 400) por parte del Web Service de AFIP.
    """

    @staticmethod
    def deducir_tipo_comprobante(
        emisor: CondicionFiscalAFIP,
        receptor: CondicionFiscalAFIP,
        clase_documento: ClaseDocumento = ClaseDocumento.FACTURA
    ) -> tuple[ClaseDocumento, int]:
        """
        Retorna una tupla: (ClaseDocumento, tipo_cbte_afip)
        """

        # 🌟 BYPASS: Los documentos logísticos no requieren cruce fiscal de AFIP
        if clase_documento == ClaseDocumento.REMITO:
            return ClaseDocumento.REMITO, 91 # 91 = Remito R genérico según AFIP

        # 🌟 TOLERANCIA LEGACY: Si la empresa es vieja y no tiene categoría, la tratamos como Monotributista
        condicion_efectiva = CondicionFiscalAFIP.MONOTRIBUTO if emisor == CondicionFiscalAFIP.NO_CATEGORIZADO else emisor

        # 1. Escenario Monotributo, Exento o Consumidor Final (Gastos Genéricos / Caja Chica)
        # 🌟 FIX FISCAL: Permitimos el ingreso de tickets de Consumidor Final tratándolos como Comprobante C (11)
        if condicion_efectiva in [
            CondicionFiscalAFIP.MONOTRIBUTO,
            CondicionFiscalAFIP.EXENTO,
            CondicionFiscalAFIP.CONSUMIDOR_FINAL
        ]:
            return ClaseDocumento.FACTURA, 11  # 11 = Factura C / Ticket C

        # 2. Escenario Responsable Inscripto
        if condicion_efectiva == CondicionFiscalAFIP.RESPONSABLE_INSCRIPTO:
            if receptor == CondicionFiscalAFIP.RESPONSABLE_INSCRIPTO:
                return ClaseDocumento.FACTURA, 1  # 1 = Factura A
            else:
                return ClaseDocumento.FACTURA, 6  # 6 = Factura B

        # 3. Fallback de Seguridad
        raise ValueError(
            f"Vulnerabilidad Fiscal Detectada: No existen reglas de emisión configuradas "
            f"para Emisor '{condicion_efectiva}' hacia Receptor '{receptor}'."
        )