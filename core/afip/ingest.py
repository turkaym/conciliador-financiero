import logging
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError

from core.database.session import tenant_session_ctx
from core.database.models_tenant import Comprobante, ComprobanteIva, ComprobanteTributo, ComprobanteAsociado, ColaMensajesMuertos
from core.domains.comprobantes.schemas import ComprobanteCreate
from .wsfe import BaseFiscalProvider

logger = logging.getLogger("INGEST_ENGINE")

class IngestManager:
    def __init__(self, client: BaseFiscalProvider, redis_client=None, tenant_id: str = "unknown"):
        self.afip = client
        self.redis = redis_client
        self.tenant_id = tenant_id
        self.env = getattr(client, 'environment', 'unknown')

    def _check_rate_limit(self) -> bool:
        if not self.redis:
            logger.warning("⚠️ [AFIP] Redis no inyectado. Rate Limit deshabilitado.")
            return True

        current_month = datetime.now(timezone.utc).strftime("%Y-%m")
        bucket_key = f"rate_limit:{self.tenant_id}:arca_requests:{current_month}"

        try:
            current_usage = int(self.redis.incr(bucket_key))
            if current_usage == 1:
                self.redis.expire(bucket_key, 31 * 86400)

            if current_usage > 1875:
                logger.warning(f"🛑 [AFIP] Rate Limit excedido para {self.tenant_id} ({current_usage} requests). Pausando ingesta.")
                return False
            return True
        except Exception as e:
            logger.error(f"❌ [AFIP] Fallo al validar Rate Limit en Redis: {e}")
            return True

    def sync_recent_invoices(self, entidad_id: int, punto_venta: int, tipo_cbte: int, chunk_size: int = 500) -> dict:
        logger.info(f"🚀 Ingesta: Entidad {entidad_id} | PV {punto_venta} | Tipo {tipo_cbte}")

        try:
            last_arca_nro = self.afip.get_last_voucher_number(punto_venta, tipo_cbte)

            with tenant_session_ctx(self.tenant_id) as db:
                last_local = db.query(Comprobante.numero)\
                    .filter(
                        Comprobante.entidad_id == entidad_id,
                        Comprobante.punto_venta == punto_venta,
                        Comprobante.tipo_cbte_afip == tipo_cbte
                    )\
                    .order_by(desc(Comprobante.numero))\
                    .first()

            last_local_nro = last_local[0] if last_local else 0

            if last_local_nro >= last_arca_nro:
                logger.info(f"✅ [AFIP] Sincronización al día. No hay nuevos comprobantes.")
                return {"new_records": 0, "has_more": False}

            target_nro = min(last_arca_nro, last_local_nro + chunk_size)
            rate_limited = False
            batch_data = []

            # 1. Bucle de extracción externa
            for nro in range(last_local_nro + 1, target_nro + 1):
                if not self._check_rate_limit():
                    rate_limited = True
                    break

                try:
                    invoice_data = self.afip.get_voucher_details(nro, punto_venta, tipo_cbte)
                    if invoice_data:
                        invoice_data['entidad_id'] = entidad_id
                        clean_invoice = self._validate_and_clean_invoice(invoice_data)
                        batch_data.append(clean_invoice)
                except Exception as inner_e:
                    logger.error(f"⚠️ [AFIP] Salto de comprobante {nro}: {inner_e}")
                    try:
                        with tenant_session_ctx(self.tenant_id) as dlq_db:
                            falla = ColaMensajesMuertos(
                                entidad_id=entidad_id, punto_venta=punto_venta,
                                tipo_cbte_afip=tipo_cbte, numero=nro,
                                error_msg=str(inner_e)[:500]
                            )
                            dlq_db.add(falla)
                            dlq_db.commit()
                    except Exception as dlq_e:
                        logger.error(f"💥 [DLQ] Fallo crítico al registrar mensaje muerto: {dlq_e}")
                    continue

            new_records = 0

            # 2. Transacción ORM Segura (Anti-TOCTOU y Anti-N+1)
            if batch_data:
                with tenant_session_ctx(self.tenant_id) as db:
                    numeros_en_lote = [d['numero'] for d in batch_data]
                    existentes_db = db.query(Comprobante.numero).filter(
                        Comprobante.cuit_emisor == batch_data[0]['cuit_emisor'],
                        Comprobante.tipo_cbte_afip == tipo_cbte,
                        Comprobante.punto_venta == punto_venta,
                        Comprobante.numero.in_(numeros_en_lote)
                    ).all()
                    set_existentes = {r[0] for r in existentes_db}

                    for data in batch_data:
                        if data['numero'] in set_existentes:
                            continue

                        iva_data = data.pop('detalles_iva', [])
                        trib_data = data.pop('detalles_tributos', [])
                        asoc_data = data.pop('comprobantes_asociados', [])

                        # 🌟 FIX: Aislamiento estricto por factura. Todo éxito o fallo ocurre atómicamente.
                        try:
                            with db.begin_nested():
                                nuevo_cbte = Comprobante(**data)

                                for iva in iva_data: nuevo_cbte.detalles_iva.append(ComprobanteIva(**iva))
                                for trib in trib_data: nuevo_cbte.detalles_tributos.append(ComprobanteTributo(**trib))
                                for asoc in asoc_data: nuevo_cbte.comprobantes_asociados.append(ComprobanteAsociado(**asoc))

                                db.add(nuevo_cbte)
                                db.flush() # Dispara la asignación de ID y validaciones de integridad BD

                                # 🌟 FIX RIESGO CONTABLE: Resolución Atómica de Notas de Crédito
                                if nuevo_cbte.clase_documento == "NOTA_CREDITO" and asoc_data:
                                    for asoc in asoc_data:
                                        # 🌟 ESCUDO ANTI-DOBLE-GASTO: Candado pesimista sobre la factura original
                                        factura_padre = db.query(Comprobante).filter(
                                            Comprobante.cuit_emisor == nuevo_cbte.cuit_emisor,
                                            Comprobante.tipo_cbte_afip == asoc['tipo_cbte_afip'],
                                            Comprobante.punto_venta == asoc['punto_venta'],
                                            Comprobante.numero == asoc['numero']
                                        ).with_for_update().first()

                                        if factura_padre:
                                            logger.info(f"🔗 [NC] Vinculando Nota Crédito {nuevo_cbte.numero} a Factura {factura_padre.numero}")
                                            nuevo_cbte.comprobante_origen_id = factura_padre.id

                                            # Conversión cruzada
                                            if factura_padre.moneda != nuevo_cbte.moneda:
                                                importe_nc_ars = Decimal(str(nuevo_cbte.importe_total)) * Decimal(str(nuevo_cbte.cotizacion))
                                                descuento_aplicable = importe_nc_ars / Decimal(str(factura_padre.cotizacion))
                                            else:
                                                descuento_aplicable = Decimal(str(nuevo_cbte.importe_total))

                                            # 🌟 INVERSIÓN INTELIGENTE DE SALDOS
                                            if factura_padre.saldo_pendiente >= descuento_aplicable:
                                                # La factura absorbe totalmente la NC
                                                factura_padre.saldo_pendiente -= descuento_aplicable
                                                nuevo_cbte.saldo_pendiente = Decimal('0.0')
                                            else:
                                                # La NC es mayor a lo que se debe. Queda un saldo a favor.
                                                sobrante = descuento_aplicable - factura_padre.saldo_pendiente
                                                factura_padre.saldo_pendiente = Decimal('0.0')

                                                if factura_padre.moneda != nuevo_cbte.moneda:
                                                    sobrante_nc_cur = sobrante * Decimal(str(factura_padre.cotizacion)) / Decimal(str(nuevo_cbte.cotizacion))
                                                    nuevo_cbte.saldo_pendiente = sobrante_nc_cur
                                                else:
                                                    nuevo_cbte.saldo_pendiente = sobrante

                                                nuevo_cbte.es_saldo_a_favor = True
                                                logger.info(f"💰 [NC] Se generó un saldo a favor de {nuevo_cbte.moneda} {nuevo_cbte.saldo_pendiente}")

                                new_records += 1
                        except IntegrityError:
                            # Al fallar, el `begin_nested()` hace rollback automático.
                            # La factura padre NUNCA es modificada si la NC falla.
                            logger.warning(f"⚠️ [TOCTOU] Comprobante {data['numero']} colisión concurrente. Ignorado.")
                            continue

                    db.commit() # Impacto total del lote validado

            has_more = not rate_limited and (target_nro < last_arca_nro)
            return {"new_records": new_records, "has_more": has_more, "rate_limited": rate_limited}

        except Exception as e:
            logger.error(f"💥 [AFIP] Fallo crítico orquestando sync: {e}", exc_info=True)
            raise RuntimeError(f"Fallo en motor de ingesta: {str(e)}")

    def _validate_and_clean_invoice(self, data: dict) -> dict:
        for field in ['fecha_emision', 'vencimiento_cae']:
            if data.get(field) and isinstance(data[field], str) and len(data[field]) == 8:
                try:
                    data[field] = datetime.strptime(data[field], '%Y%m%d').strftime('%Y-%m-%d')
                except ValueError:
                    pass

        try:
            comprobante_validado = ComprobanteCreate(**data)
            clean_data = comprobante_validado.model_dump(exclude_unset=True)
        except Exception as e:
            logger.error(f"❌ [ADUANA] Comprobante rechazado en validación: {e}")
            raise ValueError(f"Falla estructural en datos de AFIP: {e}")

        # Inicialmente, el saldo pendiente es el total del comprobante.
        # En el caso de NC, la lógica superior anulará este valor y lo volcará a 0 o al sobrante.
        clean_data['saldo_pendiente'] = clean_data['importe_total']
        return clean_data