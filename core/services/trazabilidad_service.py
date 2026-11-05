import logging
from decimal import Decimal
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from core.database.models_tenant import Comprobante, ComprobanteAsociado, SecuenciaFiscal

logger = logging.getLogger("SRV_TRAZABILIDAD")

class TrazabilidadService:
    TIPOS_NOTA_CREDITO = {3, 8, 13, 53, 112}
    TIPOS_NOTA_DEBITO = {2, 7, 12, 52, 111}

    def procesar_vinculos_y_saldos(self, db: Session, comprobante_hijo_id: int):
        hijo = db.query(Comprobante).filter(Comprobante.id == comprobante_hijo_id).first()
        if not hijo:
            return

        asociaciones_pendientes = db.query(ComprobanteAsociado).filter(
            ComprobanteAsociado.comprobante_id == hijo.id,
            ComprobanteAsociado.comprobante_vinculado_id == None
        ).all()

        for asoc in asociaciones_pendientes:
            padre = db.query(Comprobante).filter(
                Comprobante.entidad_id == hijo.entidad_id,
                Comprobante.cuit_emisor == hijo.cuit_emisor,
                Comprobante.tipo_cbte_afip == asoc.tipo_cbte_afip,
                Comprobante.punto_venta == asoc.punto_venta,
                Comprobante.numero == asoc.numero,
                Comprobante.is_active == True
            ).with_for_update().first()

            # 🌟 FIX SILENT FAILURE: Evitamos orfandad física abortando si el padre desapareció
            if not padre:
                logger.error(f"Falla Crítica de Trazabilidad: Cbte Padre {asoc.punto_venta}-{asoc.numero} no encontrado o inactivo.")
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El comprobante asociado original no existe o fue eliminado.")

            logger.info(f"🔗 Autodescubrimiento: Enlazando Cbte {hijo.id} con Padre {padre.id}")
            asoc.comprobante_vinculado_id = padre.id

            monto_hijo = Decimal(str(hijo.importe_total))

            if hijo.tipo_cbte_afip in self.TIPOS_NOTA_CREDITO:
                padre.saldo_pendiente -= monto_hijo
            elif hijo.tipo_cbte_afip in self.TIPOS_NOTA_DEBITO:
                padre.saldo_pendiente += monto_hijo

            if padre.saldo_pendiente < Decimal('0.0'):
                logger.warning(f"⚠️ Saldo negativo detectado en Cbte {padre.id} tras aplicación de NC. Ajustando a 0.00.")
                padre.saldo_pendiente = Decimal('0.0')

            db.add(padre)
            db.add(asoc)

        db.flush()

    # 🌟 FASE 13.1: Generador Atómico de Trace ID E2E (Usando Motor Fiscal Base)
    def generar_trace_id(self, db: Session, tenant_id: int, tipo_cbte_interno: int, prefijo: str) -> str:
        """
        Genera un ID único correlativo explotando el candado atómico de SecuenciaFiscal.
        Formato: PREFIJO-PV-NUMERO (Ej: MAN-0000-00000001)
        """
        punto_venta_virtual = 0 # Usamos PV 0 para distinguir claramente que no es AFIP

        try:
            # 1. Buscamos el correlativo con candado pesimista (Filtrando por entidad)
            secuencia = db.query(SecuenciaFiscal).filter(
                SecuenciaFiscal.entidad_id == tenant_id,
                SecuenciaFiscal.punto_venta == punto_venta_virtual,
                SecuenciaFiscal.tipo_cbte == tipo_cbte_interno
            ).with_for_update().first()

            if not secuencia:
                secuencia = SecuenciaFiscal(
                    entidad_id=tenant_id,
                    punto_venta=punto_venta_virtual,
                    tipo_cbte=tipo_cbte_interno,
                    ultimo_numero=0
                )
                db.add(secuencia)
                db.flush()

            # 2. Incrementamos el contador (PostgreSQL asegura que nadie más pise este valor)
            secuencia.ultimo_numero += 1
            numero_correlativo = secuencia.ultimo_numero

            # 3. Formateamos el ID final (Ej: MAN-0000-00000001)
            trace_id = f"{prefijo}-{punto_venta_virtual:04d}-{numero_correlativo:08d}"

            db.flush()
            return trace_id

        except SQLAlchemyError as e:
            logger.error(f"Falla crítica generando Trace ID interno: {e}", exc_info=True)
            raise ValueError("Colisión en base de datos al generar código de trazabilidad.")

trazabilidad_service = TrazabilidadService()