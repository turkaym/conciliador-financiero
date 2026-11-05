import logging
import uuid
from typing import Tuple, Optional
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

from core.domains.comprobantes.models import Comprobante
from core.domains.comprobantes.schemas import ComprobanteCreate
from core.domains.comprobantes.repository import comprobante_repository

from core.database.models_tenant import SecuenciaFiscal, RazonSocialPropia, ContactoComercial, PlanCuentas
from core.services.trazabilidad_service import trazabilidad_service
from core.utils.fiscal_engine import MotorInferenciaFiscal
from core.utils.enums import ClaseDocumento

logger = logging.getLogger("DOMAIN_COMPROBANTES")

class ComprobanteService:
    """
    Núcleo de Negocio del Dominio de Comprobantes.
    """

    def _validar_integridad_contable_estricta(self, db: Session, cuenta_contable_id: int):
        cuenta = db.query(PlanCuentas).filter(PlanCuentas.id == cuenta_contable_id).first()
        if not cuenta:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Fallo de Ingesta: La cuenta contable especificada (ID: {cuenta_contable_id}) no existe en este esquema."
            )
        if not cuenta.imputable:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Fallo de Ingesta: La cuenta '{cuenta.nombre}' es una cuenta consolidadora (no imputable). Debe seleccionar una cuenta de movimiento."
            )

    # 🌟 FIX B2B: Añadimos razon_social_tercero al motor de resolución
    def _resolver_y_registrar_perfil_fiscal(
        self, db: Session, entidad_id: int, cuit_tercero: str, condicion_fiscal_tercero: str,
        tipo_operacion: str, clase_documento: ClaseDocumento, razon_social_tercero: Optional[str] = None
    ) -> Tuple[ClaseDocumento, int]:

        emisor = db.query(RazonSocialPropia).filter(RazonSocialPropia.id == entidad_id).first()
        if not emisor:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No se encontró el perfil fiscal del Emisor.")

        receptor = db.query(ContactoComercial).filter(
            ContactoComercial.cuit == cuit_tercero,
            ContactoComercial.entidad_id == entidad_id
        ).with_for_update().first()

        if not receptor:
            if not condicion_fiscal_tercero:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="El CUIT no está registrado en su agenda. Seleccione la Condición Fiscal del tercero para registrarlo."
                )
            try:
                # 🌟 FIX B2B: Asignación dinámica de Razón Social con Fallback de seguridad
                nombre_entidad = razon_social_tercero if razon_social_tercero and razon_social_tercero.strip() else f"Tercero {cuit_tercero}"

                receptor = ContactoComercial(
                    entidad_id=entidad_id,
                    cuit=cuit_tercero,
                    razon_social=nombre_entidad,
                    condicion_fiscal=condicion_fiscal_tercero,
                    is_cliente=(tipo_operacion == "VENTA"),
                    is_proveedor=(tipo_operacion == "COMPRA")
                )
                db.add(receptor)
                db.flush()
            except IntegrityError:
                db.rollback()
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Colisión registrando el contacto. Intente nuevamente.")
        else:
            modificado = False

            # 🌟 FIX CRM B2B: Si el frontend envía un nombre real y el actual es un placeholder, lo sobrescribimos.
            if razon_social_tercero and razon_social_tercero.strip() and receptor.razon_social.startswith("Tercero "):
                receptor.razon_social = razon_social_tercero.strip()
                modificado = True

            if tipo_operacion == "VENTA" and not receptor.is_cliente:
                receptor.is_cliente = True
                modificado = True
            elif tipo_operacion == "COMPRA" and not receptor.is_proveedor:
                receptor.is_proveedor = True
                modificado = True

            if modificado:
                db.add(receptor)
                db.flush()

        cond_emisor = emisor.condicion_fiscal if tipo_operacion == "VENTA" else receptor.condicion_fiscal
        cond_receptor = receptor.condicion_fiscal if tipo_operacion == "VENTA" else emisor.condicion_fiscal

        return MotorInferenciaFiscal.deducir_tipo_comprobante(cond_emisor, cond_receptor, clase_documento)

    def emitir_y_guardar_comprobante(self, db: Session, afip_client, comprobante_in: ComprobanteCreate, tenant_id: int):
        if comprobante_in.entidad_id != tenant_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Violación de seguridad Multi-Tenant.")

        self._validar_integridad_contable_estricta(db, comprobante_in.cuenta_contable_id)

        try:
            cuit_tercero = comprobante_in.cuit_receptor if comprobante_in.tipo_operacion == "VENTA" else comprobante_in.cuit_emisor

            # 🌟 FIX B2B: Pasamos la razón social al motor
            clase_doc, tipo_cbte_deducido = self._resolver_y_registrar_perfil_fiscal(
                db,
                comprobante_in.entidad_id,
                cuit_tercero,
                getattr(comprobante_in, 'condicion_fiscal_receptor', None),
                comprobante_in.tipo_operacion,
                comprobante_in.clase_documento,
                getattr(comprobante_in, 'razon_social_receptor', None)
            )

            comprobante_dict = comprobante_in.model_dump(exclude_unset=True)
            comprobante_json_safe = comprobante_in.model_dump(exclude_unset=True, mode='json')

            if "subtotales_iva" in comprobante_dict:
                comprobante_dict["subtotales_iva"] = comprobante_json_safe["subtotales_iva"]
            if "otros_tributos" in comprobante_dict:
                comprobante_dict["otros_tributos"] = comprobante_json_safe["otros_tributos"]

            # 🌟 FIX B2B: Limpiamos los DTOs inyectados para evitar IntegrityError en el ORM de Comprobantes
            comprobante_dict.pop("condicion_fiscal_receptor", None)
            comprobante_dict.pop("razon_social_receptor", None)
            comprobante_dict.pop("es_fiscal", None)
            comprobante_dict.pop("condicion_venta", None)
            comprobante_dict.pop("cuenta_tesoreria_id", None)
            comprobante_dict.pop("nomenclatura_afip_sugerida", None)

            comprobante_dict["clase_documento"] = clase_doc
            comprobante_dict["tipo_cbte_afip"] = tipo_cbte_deducido
            comprobante_dict["estado"] = "PROCESANDO_AFIP" if clase_doc == ClaseDocumento.FACTURA else "BORRADOR"

            punto_venta = comprobante_in.punto_venta

            secuencia = db.query(SecuenciaFiscal).filter(
                SecuenciaFiscal.entidad_id == tenant_id, # 🌟 FIX Multi-Tenant: Aislamiento
                SecuenciaFiscal.punto_venta == punto_venta,
                SecuenciaFiscal.tipo_cbte == tipo_cbte_deducido
            ).with_for_update().first()

            if not secuencia:
                # 🌟 FIX Integridad: Inyección del campo obligatorio
                secuencia = SecuenciaFiscal(
                    entidad_id=tenant_id,
                    punto_venta=punto_venta,
                    tipo_cbte=tipo_cbte_deducido,
                    ultimo_numero=0
                )
                db.add(secuencia)
                db.flush()

            proximo_numero = secuencia.ultimo_numero + 1
            comprobante_dict["numero"] = proximo_numero
            secuencia.ultimo_numero = proximo_numero

            nuevo_comprobante = comprobante_repository.create(db, obj_in=comprobante_dict)
            db.flush()

            trazabilidad_service.procesar_vinculos_y_saldos(db, nuevo_comprobante.id)

            db.commit()
            db.refresh(nuevo_comprobante)

            if clase_doc != ClaseDocumento.REMITO and afip_client is not None:
                try:
                    ultimo_nro_afip = afip_client.get_last_voucher_number(punto_venta, tipo_cbte_deducido)
                except Exception as e:
                    logger.error(f"❌ AFIP Inaccesible. Comprobante {nuevo_comprobante.id} retenido de forma segura: {e}")
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail="Comprobante guardado localmente, pero AFIP no respondió. El proceso asíncrono resolverá el CAE."
                    )

            return nuevo_comprobante

        except Exception as e:
            db.rollback()
            logger.error(f"💥 Fallo en emisión de comprobante: {e}", exc_info=True)
            if isinstance(e, HTTPException): raise e
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno procesando emisión.")

    def crear_comprobante_con_vinculo(self, db: Session, comprobante_in: ComprobanteCreate, tenant_id: int, usuario_id: str):
        if comprobante_in.entidad_id != tenant_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Violación de seguridad Multi-Tenant.")

        self._validar_integridad_contable_estricta(db, comprobante_in.cuenta_contable_id)

        try:
            cuit_tercero = comprobante_in.cuit_receptor if comprobante_in.tipo_operacion == "VENTA" else comprobante_in.cuit_emisor

            # 🌟 FIX B2B: Pasamos la razón social al motor
            clase_doc, tipo_cbte_deducido = self._resolver_y_registrar_perfil_fiscal(
                db,
                comprobante_in.entidad_id,
                cuit_tercero,
                getattr(comprobante_in, 'condicion_fiscal_receptor', None),
                comprobante_in.tipo_operacion,
                comprobante_in.clase_documento,
                getattr(comprobante_in, 'razon_social_receptor', None)
            )

            origen_id = comprobante_in.comprobante_origen_id
            if origen_id:
                remito = db.query(Comprobante).filter(
                    Comprobante.id == origen_id,
                    Comprobante.entidad_id == tenant_id,
                    Comprobante.is_active == True
                ).with_for_update().first()

                if not remito:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El remito origen no existe.")
                if remito.estado == "FACTURADO":
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Este remito ya fue facturado.")

                remito.estado = "FACTURADO"
                db.add(remito)

            comprobante_dict = comprobante_in.model_dump(exclude_unset=True)
            comprobante_json_safe = comprobante_in.model_dump(exclude_unset=True, mode='json')

            if "subtotales_iva" in comprobante_dict:
                comprobante_dict["subtotales_iva"] = comprobante_json_safe["subtotales_iva"]
            if "otros_tributos" in comprobante_dict:
                comprobante_dict["otros_tributos"] = comprobante_json_safe["otros_tributos"]

            condicion_venta = comprobante_dict.pop("condicion_venta", "CUENTA_CORRIENTE")
            cuenta_tesoreria_id = comprobante_dict.pop("cuenta_tesoreria_id", None)

            # 🌟 FIX B2B: Purga defensiva de contratos inyectados
            comprobante_dict.pop("condicion_fiscal_receptor", None)
            comprobante_dict.pop("razon_social_receptor", None)
            comprobante_dict.pop("es_fiscal", None)
            comprobante_dict.pop("nomenclatura_afip_sugerida", None)

            comprobante_dict["clase_documento"] = clase_doc
            comprobante_dict["tipo_cbte_afip"] = tipo_cbte_deducido

            if clase_doc == ClaseDocumento.FACTURA:
                if condicion_venta == "CONTADO":
                    comprobante_dict["estado"] = "PAGADA"
                    comprobante_dict["saldo_pendiente"] = Decimal('0.00')
                else:
                    comprobante_dict["estado"] = "EMITIDO"
            else:
                comprobante_dict["estado"] = "BORRADOR"

            if comprobante_in.tipo_operacion == "VENTA":
                secuencia = db.query(SecuenciaFiscal).filter(
                    SecuenciaFiscal.entidad_id == tenant_id, # 🌟 FIX Multi-Tenant
                    SecuenciaFiscal.punto_venta == comprobante_in.punto_venta,
                    SecuenciaFiscal.tipo_cbte == tipo_cbte_deducido
                ).with_for_update().first()

                if not secuencia:
                    secuencia = SecuenciaFiscal(
                        entidad_id=tenant_id, # 🌟 FIX Integridad
                        punto_venta=comprobante_in.punto_venta,
                        tipo_cbte=tipo_cbte_deducido,
                        ultimo_numero=0
                    )
                    db.add(secuencia)
                    db.flush()

                proximo_numero = secuencia.ultimo_numero + 1
                comprobante_dict["numero"] = proximo_numero
                secuencia.ultimo_numero = proximo_numero
            else:
                comprobante_dict["numero"] = comprobante_in.numero

            nuevo = comprobante_repository.create(db, obj_in=comprobante_dict)
            db.flush()
            comprobante_id = nuevo.id

            if not comprobante_id:
                raise ValueError("Falla crítica de ORM: No se pudo obtener el ID secuencial.")

            if condicion_venta == "CONTADO" and cuenta_tesoreria_id:
                from core.database.models.tesoreria import CuentaTesoreria, MovimientoTesoreria
                from core.utils.enums import TipoComprobanteInterno

                tipo_movimiento = "INGRESO" if comprobante_in.tipo_operacion == "VENTA" else "EGRESO"
                etiqueta_concepto = "Cobro Contado" if tipo_movimiento == "INGRESO" else "Pago Contado"
                concepto_str = f"{etiqueta_concepto}: {clase_doc.value} N° {nuevo.numero}"

                trace_id_contado = trazabilidad_service.generar_trace_id(
                    db=db, tenant_id=tenant_id, tipo_cbte_interno=TipoComprobanteInterno.MOVIMIENTO_MANUAL, prefijo="MAN"
                )

                hash_tx = f"B2C-{comprobante_id}-{uuid.uuid4().hex[:8]}"

                cuenta_nueva = db.query(CuentaTesoreria).filter(
                    CuentaTesoreria.id == cuenta_tesoreria_id,
                    CuentaTesoreria.entidad_id == tenant_id,
                    CuentaTesoreria.is_active == True
                ).with_for_update().first()

                if cuenta_nueva:
                    if tipo_movimiento == "INGRESO":
                        cuenta_nueva.saldo_actual += Decimal(str(nuevo.importe_total))
                    else:
                        cuenta_nueva.saldo_actual -= Decimal(str(nuevo.importe_total))

                    movimiento = MovimientoTesoreria(
                        cuenta_id=cuenta_nueva.id,
                        tipo=tipo_movimiento,
                        fecha=nuevo.fecha_emision,
                        monto=nuevo.importe_total,
                        moneda=nuevo.moneda,
                        concepto_crudo=concepto_str,
                        hash_transaccional=hash_tx,
                        referencia_externa=trace_id_contado,
                        saldo_resultante=cuenta_nueva.saldo_actual,
                        comprobante_id=comprobante_id
                    )
                    db.add(movimiento)
                    db.add(cuenta_nueva)
                    db.flush()
                else:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caja destino inexistente o inactiva.")

            trazabilidad_service.procesar_vinculos_y_saldos(db, comprobante_id)
            db.commit()
            db.refresh(nuevo)
            return nuevo

        except IntegrityError as e:
            db.rollback()
            error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
            if "uix_comprobante_fiscal_unico_activo" in error_msg:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El número de comprobante ya está registrado.")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error de integridad: {error_msg}")

        except Exception as e:
            db.rollback()
            logger.error(f"Error procesando comprobante: {str(e)}", exc_info=True)
            if isinstance(e, HTTPException): raise e
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno procesando comprobante.")

    def anular_comprobante_seguro(self, db: Session, comprobante_id: int, tenant_id: int):
        comprobante = comprobante_repository.get_by_id(db, comprobante_id)

        if not comprobante or comprobante.entidad_id != tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comprobante no encontrado.")

        if comprobante.cae and str(comprobante.cae).strip() != "":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Comprobante posee CAE validado. Emita Nota de Crédito.")

        try:
            if comprobante.comprobante_origen_id:
                remito = db.query(Comprobante).filter(Comprobante.id == comprobante.comprobante_origen_id).with_for_update().first()
                if remito:
                    hermanos_vivos = db.query(Comprobante).filter(
                        Comprobante.comprobante_origen_id == remito.id,
                        Comprobante.id != comprobante_id,
                        Comprobante.estado != "ANULADO",
                        Comprobante.is_active == True
                    ).count()

                    remito.estado = "PARCIALMENTE_FACTURADO" if hermanos_vivos > 0 else "EMITIDO"
                    db.add(remito)

            from core.database.models.tesoreria import CuentaTesoreria, MovimientoTesoreria

            movs_tesoreria = db.query(MovimientoTesoreria).filter(MovimientoTesoreria.comprobante_id == comprobante_id).all()
            for mov in movs_tesoreria:
                cuenta = db.query(CuentaTesoreria).filter(CuentaTesoreria.id == mov.cuenta_id).with_for_update().first()
                if cuenta:
                    if mov.tipo == "INGRESO": cuenta.saldo_actual -= mov.monto
                    else: cuenta.saldo_actual += mov.monto
                    db.add(cuenta)

                mov.anulado = True
                mov.motivo_anulacion = "Anulación de comprobante asociado"
                db.add(mov)

            comprobante.estado = "ANULADO"
            comprobante_repository.soft_delete(db, comprobante)

            db.commit()
            return True

        except Exception as e:
            db.rollback()
            logger.error(f"Error anulando comprobante {comprobante_id}: {e}", exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Fallo al anular documento y revertir fondos.")

    def obtener_pendientes_proveedor(self, db: Session, entidad_id: int, proveedor_id: int):
        proveedor = db.query(ContactoComercial).filter(
            ContactoComercial.id == proveedor_id,
            ContactoComercial.entidad_id == entidad_id,
            ContactoComercial.is_active == True
        ).first()

        if not proveedor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proveedor no encontrado o inactivo."
            )

        pendientes = db.query(Comprobante).filter(
            Comprobante.entidad_id == entidad_id,
            Comprobante.cuit_emisor == proveedor.cuit,
            Comprobante.tipo_operacion == "COMPRA",
            Comprobante.saldo_pendiente > 0,
            Comprobante.is_active == True,
            Comprobante.estado.notin_(["ANULADO", "BORRADOR"])
        ).order_by(Comprobante.fecha_emision.asc()).limit(100).all()

        return pendientes

comprobante_service = ComprobanteService()