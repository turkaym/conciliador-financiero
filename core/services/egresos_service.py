import uuid
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, OperationalError
from fastapi import HTTPException, status
from datetime import datetime, timezone, timedelta
from decimal import Decimal

# 🌟 FIX PEP 8: Centralización estricta de Modelos y Schemas
from core.database.models.pagos import ConceptoOperativo, OrdenPago, LotePago, LotePagoDetalle
from core.database.models_tenant import ContactoComercial, Comprobante
from core.database.models.tesoreria import CuentaTesoreria, MovimientoTesoreria
from core.schemas.pagos import OrdenPagoCreate, LotePagoCreate, OrdenPagoMultipleCreate
from core.schemas.tax_engine import ImpuestoCalculado
from core.schemas.banco import MovimientoBancarioCreate

# 🌟 FIX PEP 8: Centralización de Enums (Eliminación de Lazy Imports)
from core.utils.enums import (
    EstadoOrdenPago,
    EstadoLotePago,
    TipoComprobanteInterno,
    CondicionFiscalAFIP,
    ClaseDocumento,
    EstadoComprobante
)

# 🌟 FIX PEP 8: Centralización de Servicios
from core.services.trazabilidad_service import trazabilidad_service
from core.services.tax_engine_service import tax_engine_service
from core.services.banco_service import banco_service

class EgresosService:

    def __init__(self, db: Session, entidad_id: int):
        self.db = db
        self.entidad_id = entidad_id

    def buscar_ordenes(self, params):
        query = self.db.query(OrdenPago).filter(OrdenPago.entidad_id == self.entidad_id)

        inicio_dt = datetime.combine(params.fecha_inicio, datetime.min.time())
        fin_dt = datetime.combine(params.fecha_fin, datetime.max.time())
        query = query.filter(OrdenPago.created_at >= inicio_dt, OrdenPago.created_at <= fin_dt)

        if params.concepto_id:
            query = query.filter(OrdenPago.concepto_id == params.concepto_id)
        if params.codigo_trazabilidad:
            query = query.filter(OrdenPago.codigo_trazabilidad.ilike(f"%{params.codigo_trazabilidad}%"))
        if params.monto_min is not None:
            query = query.filter(OrdenPago.monto_estimado >= params.monto_min)
        if params.monto_max is not None:
            query = query.filter(OrdenPago.monto_estimado <= params.monto_max)

        if params.q:
            query = query.join(ContactoComercial, OrdenPago.proveedor_id == ContactoComercial.id)
            query = query.filter(
                (ContactoComercial.razon_social.ilike(f"%{params.q}%")) |
                (ContactoComercial.cuit.ilike(f"%{params.q}%"))
            )

        query = query.order_by(OrdenPago.created_at.desc())
        query = query.offset(params.offset).limit(params.limit)
        return query.all()

    def crear_orden_pago(
        self,
        data: OrdenPagoCreate,
        user_id: str = "SYSTEM",
        user_role: str = "operador",
        umbral_aprobacion: float = 0.0
    ) -> OrdenPago:
        now_utc = datetime.now(timezone.utc)
        today_local = now_utc.astimezone(timezone(timedelta(hours=-3))).date()

        proveedor_id_final = data.proveedor_id
        if not proveedor_id_final:
            prov_caja_chica = self.db.query(ContactoComercial).filter(
                ContactoComercial.entidad_id == self.entidad_id,
                ContactoComercial.cuit == "33693450239"
            ).first()

            if not prov_caja_chica:
                prov_caja_chica = ContactoComercial(
                    entidad_id=self.entidad_id, cuit="33693450239",
                    razon_social="Caja Chica / Gastos Menores", is_proveedor=True,
                    condicion_fiscal=CondicionFiscalAFIP.CONSUMIDOR_FINAL
                )
                self.db.add(prov_caja_chica)
                self.db.flush()
            proveedor_id_final = prov_caja_chica.id

        codigo_op = trazabilidad_service.generar_trace_id(
            db=self.db,
            tenant_id=self.entidad_id,
            tipo_cbte_interno=TipoComprobanteInterno.GASTO_MENOR,
            prefijo="GST"
        )

        excluir_fiscal = not data.requiere_comprobante_fiscal
        is_fast_track = getattr(data, 'fast_track_cuenta_id', None) is not None

        cuenta_origen = None
        if is_fast_track:
            cuenta_origen = self.db.query(CuentaTesoreria).filter(
                CuentaTesoreria.id == data.fast_track_cuenta_id,
                CuentaTesoreria.entidad_id == self.entidad_id,
                CuentaTesoreria.is_active == True
            ).with_for_update().first()

            if not cuenta_origen:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La cuenta bancaria de origen no existe en Tesorería.")

            saldo_disponible = Decimal(str(cuenta_origen.saldo_actual)) - Decimal(str(getattr(cuenta_origen, 'saldo_retenido', 0.0)))
            monto_requerido = Decimal(str(data.monto_estimado))
            moneda_cuenta = cuenta_origen.moneda.value if hasattr(cuenta_origen.moneda, 'value') else str(cuenta_origen.moneda)

            if monto_requerido > saldo_disponible:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Saldo insuficiente para Vía Rápida. Requerido: {monto_requerido} {moneda_cuenta}. Disponible: {saldo_disponible}."
                )

            estado_inicial = getattr(EstadoOrdenPago, 'AUTORIZADA', getattr(EstadoOrdenPago, 'FACTURA_ASIGNADA', list(EstadoOrdenPago)[-1]))
        else:
            estado_inicial = getattr(EstadoOrdenPago, 'BORRADOR', list(EstadoOrdenPago)[0])

        nueva_orden = OrdenPago(
            entidad_id=self.entidad_id,
            codigo_trazabilidad=codigo_op,
            concepto_id=data.concepto_id,
            proveedor_id=proveedor_id_final,
            monto_estimado=data.monto_estimado,
            moneda=data.moneda,
            tipo_cambio_estimado=data.tipo_cambio_estimado,
            requiere_comprobante_fiscal=data.requiere_comprobante_fiscal,
            excluir_reportes_fiscales=excluir_fiscal,
            comprobante_interno_url=data.comprobante_interno_url,
            estado_orden=estado_inicial,
            creado_por_id=user_id,
            actualizado_por_id=user_id
        )

        try:
            self.db.add(nueva_orden)
            self.db.flush()

            comprobante_id = None

            if hasattr(data, 'factura_id') and data.factura_id:
                 comprobante_existente = self.db.query(Comprobante).filter(
                     Comprobante.id == data.factura_id,
                     Comprobante.entidad_id == self.entidad_id
                 ).with_for_update().first()

                 if comprobante_existente:
                     comprobante_id = comprobante_existente.id
                     if is_fast_track:
                          comprobante_existente.estado = "PAGADA"
                          comprobante_existente.saldo_pendiente = Decimal("0.0")

            elif excluir_fiscal and data.comprobante_interno_url and getattr(data, 'numero_ticket', None):
                proveedor = self.db.query(ContactoComercial).filter(ContactoComercial.id == proveedor_id_final).first()
                cuit_prov = proveedor.cuit if proveedor else "00000000000"

                num_limpio = ''.join(filter(str.isdigit, data.numero_ticket))
                if num_limpio:
                    numero_cbte = int(num_limpio[-8:])
                else:
                    numero_cbte = int(now_utc.timestamp() % 100000000)

                nuevo_comprobante = Comprobante(
                    entidad_id=self.entidad_id,
                    cuenta_contable_id=data.cuenta_contable_id,
                    clase_documento=ClaseDocumento.FACTURA.name if hasattr(ClaseDocumento.FACTURA, 'name') else "FACTURA",
                    tipo_operacion="COMPRA",
                    estado="EMITIDO",
                    fecha_emision=today_local,
                    punto_venta=1,
                    numero=numero_cbte,
                    cuit_emisor=cuit_prov,
                    cuit_receptor="00000000000",
                    importe_neto_gravado=Decimal("0.0"),
                    importe_no_gravado=data.monto_estimado,
                    importe_exento=Decimal("0.0"),
                    importe_neto=Decimal("0.0"),
                    importe_iva=Decimal("0.0"),
                    importe_tributos=Decimal("0.0"),
                    importe_total=data.monto_estimado,
                    moneda=data.moneda.value if hasattr(data.moneda, 'value') else str(data.moneda)
                )
                self.db.add(nuevo_comprobante)
                self.db.flush()
                comprobante_id = nuevo_comprobante.id

                if is_fast_track:
                    nuevo_comprobante.estado = "PAGADA"
                    nuevo_comprobante.saldo_pendiente = Decimal("0.0")

            if is_fast_track:
                codigo_ml = trazabilidad_service.generar_trace_id(
                    db=self.db,
                    tenant_id=self.entidad_id,
                    tipo_cbte_interno=TipoComprobanteInterno.LOTE_PAGO,
                    prefijo="ML"
                )
                estado_lote_inicial = getattr(EstadoLotePago, 'AUTHORIZED_FOR_PAYMENT', list(EstadoLotePago)[-1])

                micro_lote = LotePago(
                    entidad_id=self.entidad_id,
                    codigo_lote=codigo_ml,
                    moneda_pago=data.moneda,
                    monto_total_lote=data.monto_estimado,
                    estado_lote=estado_lote_inicial,
                    cuenta_tesoreria_id=cuenta_origen.id,
                    aprobado_por_id=user_id,
                    fecha_autorizacion=now_utc,
                    creado_por_id=user_id,
                    actualizado_por_id=user_id
                )
                self.db.add(micro_lote)
                self.db.flush()

                detalle = LotePagoDetalle(
                    lote_id=micro_lote.id,
                    orden_pago_id=nueva_orden.id,
                    comprobante_id=comprobante_id,
                    monto_asignado_moneda_origen=data.monto_estimado,
                    monto_asignado_ars=data.monto_estimado,
                    tipo_cambio_aplicado=data.tipo_cambio_estimado or Decimal("1.0"),
                    creado_por_id=user_id,
                    actualizado_por_id=user_id
                )
                self.db.add(detalle)

                mov_in = MovimientoBancarioCreate(
                    entidad_id=self.entidad_id,
                    cuenta_id=cuenta_origen.id,
                    cuenta_contable_id=data.cuenta_contable_id or nueva_orden.concepto_id,
                    fecha=today_local,
                    monto=-abs(Decimal(str(data.monto_estimado))),
                    moneda=moneda_cuenta,
                    concepto_bancario_crudo=f"Liquidación Directa - Gasto {codigo_op}",
                    concepto_interno="Vía Rápida / Sifón Fiscal",
                    referencia_banco=codigo_ml
                )

                try:
                    banco_service.registrar_movimiento_con_saldo(
                        db=self.db,
                        mov_in=mov_in,
                        entidad_id=self.entidad_id,
                        user_id=user_id,
                        user_role=user_role,
                        umbral_aprobacion=umbral_aprobacion
                    )
                except Exception as trans_err:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Fallo en motor transaccional de tesorería: {str(trans_err)}"
                    )

            self.db.commit()
            self.db.refresh(nueva_orden)
            return nueva_orden

        except HTTPException as http_exc:
            raise http_exc
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Colisión de integridad al generar la Orden de Pago.")
        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error transaccional: {str(e)}")

    def crear_lote_draft(self, data: LotePagoCreate, user_id: str = "SYSTEM") -> LotePago:
        ordenes_ids = [det.orden_pago_id for det in data.detalles if det.orden_pago_id]

        if ordenes_ids:
            try:
                ordenes_db = self.db.query(OrdenPago).filter(
                    OrdenPago.id.in_(ordenes_ids),
                    OrdenPago.entidad_id == self.entidad_id
                ).with_for_update(nowait=True).all()
            except OperationalError:
                self.db.rollback()
                raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="Una o más facturas están siendo procesadas simultáneamente.")

            if len(ordenes_db) != len(ordenes_ids):
                self.db.rollback()
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Brecha de seguridad detectada: órdenes huérfanas.")

            estados_permitidos = []
            if hasattr(EstadoOrdenPago, 'BORRADOR'): estados_permitidos.append(EstadoOrdenPago.BORRADOR)
            if hasattr(EstadoOrdenPago, 'FACTURA_ASIGNADA'): estados_permitidos.append(EstadoOrdenPago.FACTURA_ASIGNADA)

            for op in ordenes_db:
                if op.estado_orden not in estados_permitidos:
                    self.db.rollback()
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Condición de carrera evitada. La orden {op.codigo_trazabilidad} ya no está disponible."
                    )

            if hasattr(EstadoOrdenPago, 'EN_LOTE'):
                nuevo_estado_op = EstadoOrdenPago.EN_LOTE
            elif hasattr(EstadoOrdenPago, 'PENDIENTE_AUTORIZACION'):
                nuevo_estado_op = EstadoOrdenPago.PENDIENTE_AUTORIZACION
            else:
                self.db.rollback()
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="El diccionario EstadoOrdenPago carece de un estado válido.")

            for op in ordenes_db:
                op.estado_orden = nuevo_estado_op
                op.actualizado_por_id = user_id

        codigo_lote = trazabilidad_service.generar_trace_id(
            db=self.db, tenant_id=self.entidad_id, tipo_cbte_interno=TipoComprobanteInterno.LOTE_PAGO, prefijo="LOT"
        )

        estado_lote_draft = getattr(EstadoLotePago, 'DRAFT', list(EstadoLotePago)[0])

        nuevo_lote = LotePago(
            entidad_id=self.entidad_id,
            codigo_lote=codigo_lote,
            moneda_pago=data.moneda_pago,
            monto_total_lote=data.monto_total_lote,
            estado_lote=estado_lote_draft,
            creado_por_id=user_id,
            actualizado_por_id=user_id
        )
        self.db.add(nuevo_lote)
        self.db.flush()

        suma_detalles_ars = Decimal("0.0")
        for det in data.detalles:
            detalle_db = LotePagoDetalle(
                lote_id=nuevo_lote.id,
                orden_pago_id=det.orden_pago_id,
                comprobante_id=det.comprobante_id,
                monto_asignado_moneda_origen=det.monto_asignado_moneda_origen,
                monto_asignado_ars=det.monto_asignado_ars,
                tipo_cambio_aplicado=det.tipo_cambio_aplicado,
                creado_por_id=user_id,
                actualizado_por_id=user_id
            )
            self.db.add(detalle_db)
            suma_detalles_ars += det.monto_asignado_ars

        if suma_detalles_ars != data.monto_total_lote:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Descuadre de liquidez en ensamblaje."
            )

        self.db.commit()
        self.db.refresh(nuevo_lote)
        return nuevo_lote

    def solicitar_autorizacion(self, lote_id: int, user_id: str = "SYSTEM") -> LotePago:
        try:
            lote = self.db.query(LotePago).filter(
                LotePago.id == lote_id,
                LotePago.entidad_id == self.entidad_id
            ).with_for_update(nowait=True).first()
        except OperationalError:
            self.db.rollback()
            raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="Recurso bloqueado por transacción activa.")

        if not lote:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lote no encontrado.")

        estado_lote_draft = getattr(EstadoLotePago, 'DRAFT', list(EstadoLotePago)[0])
        estado_lote_pending = getattr(EstadoLotePago, 'PENDING_APPROVAL', list(EstadoLotePago)[1])

        if lote.estado_lote != estado_lote_draft:
            self.db.rollback()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Transición rechazada.")

        lote.estado_lote = estado_lote_pending
        lote.actualizado_por_id = user_id

        self.db.commit()
        self.db.refresh(lote)
        return lote

    def autorizar_lote(self, lote_id: int, user_id: str, cuenta_bancaria_id: int) -> LotePago:
        try:
            lote = self.db.query(LotePago).filter(
                LotePago.id == lote_id,
                LotePago.entidad_id == self.entidad_id
            ).with_for_update(nowait=True).first()
        except OperationalError:
            self.db.rollback()
            raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="Recurso bloqueado por transacción activa.")

        if not lote:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lote no encontrado.")

        cuenta_valida = self.db.query(CuentaTesoreria).filter(
            CuentaTesoreria.id == cuenta_bancaria_id,
            CuentaTesoreria.entidad_id == self.entidad_id
        ).first()

        if not cuenta_valida:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La cuenta origen seleccionada no es válida o no pertenece a la Tesorería de esta entidad."
            )

        estado_lote_pending = getattr(EstadoLotePago, 'PENDING_APPROVAL', list(EstadoLotePago)[1])
        estado_lote_auth = getattr(EstadoLotePago, 'AUTHORIZED_FOR_PAYMENT', list(EstadoLotePago)[2])

        if lote.estado_lote != estado_lote_pending:
            self.db.rollback()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Transición denegada.")

        lote.estado_lote = estado_lote_auth
        lote.cuenta_tesoreria_id = cuenta_bancaria_id
        lote.aprobado_por_id = user_id
        lote.fecha_autorizacion = datetime.now(timezone.utc)
        lote.actualizado_por_id = user_id

        if hasattr(EstadoOrdenPago, 'AUTORIZADA'):
            nuevo_estado_op = EstadoOrdenPago.AUTORIZADA
        elif hasattr(EstadoOrdenPago, 'PENDIENTE_PAGO'):
            nuevo_estado_op = EstadoOrdenPago.PENDIENTE_PAGO
        else:
            nuevo_estado_op = list(EstadoOrdenPago)[-1]

        for detalle in lote.detalles:
            if detalle.orden_pago:
                detalle.orden_pago.estado_orden = nuevo_estado_op
                detalle.orden_pago.actualizado_por_id = user_id

        self.db.commit()
        self.db.refresh(lote)
        return lote

    def crear_orden_pago_multiple(
        self,
        data: OrdenPagoMultipleCreate,
        user_id: str = "SYSTEM",
        user_role: str = "operador",
        umbral_aprobacion: float = 0.0
    ):
        now_utc = datetime.now(timezone.utc)
        today_local = now_utc.astimezone(timezone(timedelta(hours=-3))).date()

        es_admin = user_role.lower() in ["admin", "dueño", "editor"]
        is_fast_track = getattr(data, 'cuenta_origen_id', None) is not None and data.cuenta_origen_id > 0

        if is_fast_track and not es_admin:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Violación de Seguridad: Los operadores solo pueden Encolar órdenes."
            )

        try:
            facturas = self.db.query(Comprobante).filter(
                Comprobante.id.in_(data.facturas_ids),
                Comprobante.entidad_id == self.entidad_id,
                Comprobante.is_active == True,
                Comprobante.saldo_pendiente > 0
            ).with_for_update(nowait=True).all()
        except OperationalError:
            self.db.rollback()
            raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="Condición de carrera detectada.")

        if len(facturas) != len(data.facturas_ids):
            self.db.rollback()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Facturas inexistentes o ya amortizadas.")

        saldo_total_facturas = sum(f.saldo_pendiente for f in facturas)
        if data.monto_bruto_abonar > saldo_total_facturas:
            self.db.rollback()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El monto supera la deuda consolidada.")

        total_retenciones_ars = sum(r.monto_impuesto for r in data.retenciones)

        if is_fast_track:
            cuenta_origen = self.db.query(CuentaTesoreria).filter(
                CuentaTesoreria.id == data.cuenta_origen_id,
                CuentaTesoreria.entidad_id == self.entidad_id
            ).with_for_update().first()
            if not cuenta_origen:
                self.db.rollback()
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cuenta de origen no encontrada.")
            moneda_cuenta = cuenta_origen.moneda.value if hasattr(cuenta_origen.moneda, 'value') else str(cuenta_origen.moneda)
            saldo_disponible = Decimal(str(cuenta_origen.saldo_actual)) - Decimal(str(getattr(cuenta_origen, 'saldo_retenido', 0.0)))
        else:
            moneda_cuenta = "ARS"
            saldo_disponible = Decimal("9999999999.0")

        if moneda_cuenta == "ARS":
            bruto_convertido = data.monto_bruto_abonar * Decimal(str(data.tipo_cambio))
            neto_a_transferir_moneda_cuenta = bruto_convertido - Decimal(str(total_retenciones_ars))
        else:
            retenciones_usd = Decimal(str(total_retenciones_ars)) / Decimal(str(data.tipo_cambio))
            neto_a_transferir_moneda_cuenta = data.monto_bruto_abonar - retenciones_usd

        neto_a_transferir_moneda_cuenta = round(neto_a_transferir_moneda_cuenta, 2)

        if is_fast_track and neto_a_transferir_moneda_cuenta > saldo_disponible:
            self.db.rollback()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Saldo insuficiente en Vía Rápida.")

        concepto = self.db.query(ConceptoOperativo).filter(ConceptoOperativo.entidad_id == self.entidad_id, ConceptoOperativo.nombre_descriptivo.ilike("%pago a proveedor%")).first()
        if not concepto:
            concepto = ConceptoOperativo(entidad_id=self.entidad_id, codigo="PAG-PROV", nombre_descriptivo="Pago a Proveedores")
            self.db.add(concepto)
            self.db.flush()

        if is_fast_track:
            estado_op = getattr(EstadoOrdenPago, 'AUTORIZADA', list(EstadoOrdenPago)[-1])
        else:
            estado_op = getattr(EstadoOrdenPago, 'FACTURA_ASIGNADA', list(EstadoOrdenPago)[2])

        ratio_neto = neto_a_transferir_moneda_cuenta / data.monto_bruto_abonar if data.monto_bruto_abonar > 0 else Decimal("1.0")
        ordenes_creadas = []
        monto_restante_bruto = data.monto_bruto_abonar
        facturas_ordenadas = sorted(facturas, key=lambda f: f.fecha_emision)

        for f in facturas_ordenadas:
            if monto_restante_bruto <= Decimal("0.0"): break

            pago_bruto_asignado = min(monto_restante_bruto, f.saldo_pendiente)
            pago_neto_asignado = round(pago_bruto_asignado * ratio_neto, 2)

            codigo_op = trazabilidad_service.generar_trace_id(db=self.db, tenant_id=self.entidad_id, tipo_cbte_interno=TipoComprobanteInterno.GASTO_MENOR, prefijo="OPM")

            nueva_orden = OrdenPago(
                entidad_id=self.entidad_id, codigo_trazabilidad=codigo_op, concepto_id=concepto.id,
                proveedor_id=data.proveedor_id, monto_estimado=pago_neto_asignado, moneda=moneda_cuenta,
                estado_orden=estado_op, requiere_comprobante_fiscal=False, excluir_reportes_fiscales=True,
                creado_por_id=user_id, actualizado_por_id=user_id
            )
            self.db.add(nueva_orden)
            self.db.flush()

            ordenes_creadas.append((nueva_orden, f.id, pago_bruto_asignado, pago_neto_asignado))

            f.saldo_pendiente -= pago_bruto_asignado

            # 🌟 FIX CÓDIGO BASURA: Eliminado el try/except ImportError crudo.
            if f.saldo_pendiente == Decimal("0.0"):
                f.estado = EstadoComprobante.PAGADA.value if is_fast_track else EstadoComprobante.EN_PAGO.value
            else:
                f.estado = EstadoComprobante.PARCIAL.value

            monto_restante_bruto -= pago_bruto_asignado

        proveedor = self.db.query(ContactoComercial).filter(ContactoComercial.id == data.proveedor_id).first()
        if data.retenciones and proveedor:
            impuestos_calc = [
                ImpuestoCalculado(tipo_impuesto=r.tipo_impuesto, jurisdiccion=r.jurisdiccion, base_imponible=data.monto_bruto_abonar, alicuota_aplicada=r.alicuota_aplicada, monto_impuesto=r.monto_impuesto, origen_alicuota="UI_CONFIRMATION", cuenta_contable_id=None) for r in data.retenciones
            ]
            tax_engine_service.consolidar_registros_tributarios(db=self.db, entidad_id=self.entidad_id, clase_tributo="RETENCION_EMITIDA", cuit_sujeto=proveedor.cuit, razon_social_sujeto=proveedor.razon_social, fecha_registro=today_local, impuestos_calculados=impuestos_calc, numero_comprobante_origen=ordenes_creadas[0][0].codigo_trazabilidad)

        nuevo_lote = None
        if is_fast_track:
            codigo_lote = trazabilidad_service.generar_trace_id(db=self.db, tenant_id=self.entidad_id, tipo_cbte_interno=TipoComprobanteInterno.LOTE_PAGO, prefijo="LOT")
            estado_lote_final = getattr(EstadoLotePago, 'AUTHORIZED_FOR_PAYMENT', list(EstadoLotePago)[2])

            nuevo_lote = LotePago(
                entidad_id=self.entidad_id, codigo_lote=codigo_lote, moneda_pago=moneda_cuenta,
                monto_total_lote=neto_a_transferir_moneda_cuenta, estado_lote=estado_lote_final,
                cuenta_tesoreria_id=cuenta_origen.id, aprobado_por_id=user_id,
                fecha_autorizacion=now_utc, creado_por_id=user_id, actualizado_por_id=user_id
            )
            self.db.add(nuevo_lote)
            self.db.flush()

        for orden, f_id, pago_bruto, pago_neto in ordenes_creadas:
            detalle = LotePagoDetalle(
                lote_id=nuevo_lote.id if nuevo_lote else None,
                orden_pago_id=orden.id, comprobante_id=f_id,
                monto_asignado_moneda_origen=pago_bruto, monto_asignado_ars=pago_bruto * Decimal(str(data.tipo_cambio)),
                tipo_cambio_aplicado=Decimal(str(data.tipo_cambio)), creado_por_id=user_id, actualizado_por_id=user_id
            )
            self.db.add(detalle)

        if is_fast_track:
            mov_in = MovimientoBancarioCreate(
                entidad_id=self.entidad_id, cuenta_id=cuenta_origen.id, cuenta_contable_id=concepto.id,
                fecha=today_local, monto=-abs(neto_a_transferir_moneda_cuenta), moneda=moneda_cuenta,
                concepto_bancario_crudo=f"Pago Directo Prov. - Lote {codigo_lote}",
                concepto_interno="Liquidación Vía Rápida", referencia_banco=codigo_lote
            )
            banco_service.registrar_movimiento_con_saldo(db=self.db, mov_in=mov_in, entidad_id=self.entidad_id, user_id=user_id, user_role=user_role, umbral_aprobacion=umbral_aprobacion)

        self.db.commit()

        return nuevo_lote if nuevo_lote else {"id": 0, "codigo_lote": "ENCOLADO", "monto_total_lote": data.monto_bruto_abonar, "estado_lote": "DRAFT", "detalles": []}