import uuid
import os
import hashlib
from urllib.parse import urlparse
from datetime import timedelta, date, datetime, timezone
from typing import Annotated, List, Optional
from pydantic import BaseModel, Field
from decimal import Decimal

from fastapi import APIRouter, Depends, Header, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from minio import Minio

from config.config import settings
from core.api.deps import get_current_user, CachedUser, get_tenant_db_session, EntityRoleChecker, redis_client
from core.database.models_tenant import LotePago, ConceptoOperativo, ContactoComercial, LotePagoDetalle, OrdenPago, CuentaTesoreria
from core.utils.enums import EstadoLotePago, CondicionFiscalAFIP, EstadoOrdenPago
from core.bank_adapters.export_strategy import InterbankingAdapter
from core.services.egresos_service import EgresosService
from core.services.reversiones_service import reversiones_service
from core.storage.minio_client import minio_client
from core.schemas.pagos import (
    OrdenPagoCreate, OrdenPagoResponse, ContactoComercialResponse,
    BuscadorEgresosQueryParams, ConceptoOperativoCreate, ConceptoResponse,
    ContactoComercialCreate, LotePagoCreate, LotePagoResponse, AutorizarLoteRequest, OrdenPagoMultipleCreate)

router = APIRouter(
    dependencies=[Depends(EntityRoleChecker(["admin", "dueño", "operador", "visor", "editor"]))]
)

def _get_tenant_threshold_and_role(current_user):
    user_role = getattr(current_user, "role", "operador")
    umbral_aprobacion = 0.0
    if hasattr(current_user, "tenant") and current_user.tenant and hasattr(current_user.tenant, "features") and isinstance(current_user.tenant.features, dict):
        umbral_aprobacion = float(current_user.tenant.features.get("umbral_aprobacion", 0.0))

    if umbral_aprobacion == 0.0:
        umbral_aprobacion = 10000.00

    return user_role, umbral_aprobacion

# ==========================================
# 🌟 FASE 5: ORÁCULO CAMBIARIO ANTIFRAUDE (READ-THROUGH)
# ==========================================
def validar_tolerancia_cambiaria(db: Session, moneda: str, tipo_cambio_ingresado: Decimal, fecha_operacion: date):
    if moneda == "ARS":
        return

    from core.services.cotizacion_service import cotizacion_service

    try:
        # Obtenemos la cotización segura (Local o Fetch JIT)
        tc_oficial = cotizacion_service.obtener_cotizacion_oficial_segura(db, moneda, fecha_operacion)
    except ValueError as e:
        # FAIL-CLOSED: Si no hay cotización, no hay pago.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Operación bloqueada. {str(e)}"
        )

    tc_ingresado = Decimal(str(tipo_cambio_ingresado))

    # Tolerancia del 20% para absorber Spread Bancario, MEP, CCL
    limite_superior = tc_oficial * Decimal("1.20")
    limite_inferior = tc_oficial * Decimal("0.80")

    if tc_ingresado < limite_inferior or tc_ingresado > limite_superior:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bloqueo Antifraude: El tipo de cambio ingresado (${tc_ingresado:.2f}) se desvía más de un 20% de la cotización oficial (${tc_oficial:.2f})."
        )

# ==========================================
# ENDPOINTS B2B Y MAESTROS
# ==========================================

class ProveedorUpdate(BaseModel):
    razon_social: Optional[str] = None
    cbu: Optional[str] = Field(None, min_length=22, max_length=22)
    condicion_fiscal: Optional[CondicionFiscalAFIP] = None

@router.get("/conceptos", response_model=List[ConceptoResponse])
def listar_conceptos(
    x_entity_id: Annotated[int, Header(description="ID de la Razón Social Activa")],
    db: Session = Depends(get_tenant_db_session),
    current_user = Depends(get_current_user)
):
    return db.query(ConceptoOperativo).filter(
        ConceptoOperativo.entidad_id == x_entity_id,
        ConceptoOperativo.is_active == True
    ).all()

@router.post("/conceptos", response_model=ConceptoResponse, status_code=status.HTTP_201_CREATED)
def crear_concepto(
    payload: ConceptoOperativoCreate,
    x_entity_id: Annotated[int, Header(description="ID de la Razón Social Activa")],
    db: Session = Depends(get_tenant_db_session),
    current_user = Depends(get_current_user)
):
    nuevo = ConceptoOperativo(entidad_id=x_entity_id, **payload.model_dump())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo

@router.get("/proveedores", response_model=List[ContactoComercialResponse])
def listar_proveedores(
    x_entity_id: Annotated[int, Header(description="ID de la Razón Social Activa")],
    db: Session = Depends(get_tenant_db_session),
    current_user = Depends(get_current_user)
):
    proveedores = db.query(ContactoComercial).filter(
        ContactoComercial.entidad_id == x_entity_id,
        ContactoComercial.is_active == True
    ).all()

    if not proveedores:
        p1 = ContactoComercial(
            entidad_id=x_entity_id,
            cuit="33693450239",
            razon_social="Caja Chica / Gastos Menores",
            cbu="0000000000000000000000",
            is_proveedor=True,
            condicion_fiscal=CondicionFiscalAFIP.CONSUMIDOR_FINAL
        )
        db.add(p1)
        db.commit()
        db.refresh(p1)
        return [p1]

    proveedores_validos = [p for p in proveedores if p.cuit != "20123456789"]
    return proveedores_validos

@router.get("/acreedores-activos", response_model=List[ContactoComercialResponse])
def listar_acreedores_activos(
    x_entity_id: Annotated[int, Header(description="ID de la Razón Social Activa")],
    db: Session = Depends(get_tenant_db_session),
    current_user = Depends(get_current_user)
):
    from core.domains.comprobantes.models import Comprobante
    acreedores = db.query(ContactoComercial).join(
        Comprobante,
        (ContactoComercial.cuit == Comprobante.cuit_emisor) &
        (Comprobante.entidad_id == x_entity_id)
    ).filter(
        ContactoComercial.entidad_id == x_entity_id,
        ContactoComercial.is_active == True,
        Comprobante.tipo_operacion == "COMPRA",
        Comprobante.saldo_pendiente > 0,
        Comprobante.estado.notin_(["ANULADO", "BORRADOR"])
    ).distinct().all()

    return acreedores

@router.post("/proveedores", response_model=ContactoComercialResponse, status_code=status.HTTP_201_CREATED)
def crear_proveedor(
    payload: ContactoComercialCreate,
    x_entity_id: Annotated[int, Header(description="ID de la Razón Social Activa")],
    db: Session = Depends(get_tenant_db_session),
    current_user = Depends(get_current_user)
):
    nuevo = ContactoComercial(entidad_id=x_entity_id, **payload.model_dump())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo

@router.patch("/proveedores/{proveedor_id}", response_model=ContactoComercialResponse)
def actualizar_proveedor(
    proveedor_id: int,
    payload: ProveedorUpdate,
    x_entity_id: Annotated[int, Header(description="ID de la Razón Social Activa")],
    db: Session = Depends(get_tenant_db_session),
    current_user = Depends(get_current_user)
):
    proveedor = db.query(ContactoComercial).filter(
        ContactoComercial.id == proveedor_id,
        ContactoComercial.entidad_id == x_entity_id
    ).first()

    if not proveedor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado.")

    if payload.razon_social is not None:
        proveedor.razon_social = payload.razon_social
    if payload.cbu is not None:
        proveedor.cbu = payload.cbu
    if payload.condicion_fiscal is not None:
        proveedor.condicion_fiscal = payload.condicion_fiscal

    db.commit()
    db.refresh(proveedor)
    return proveedor

@router.get("/adjuntos/presigned")
def obtener_presigned_url(
    x_entity_id: Annotated[int, Header(description="ID de la Razón Social Activa")],
    filename: str = Query(..., description="Nombre del archivo original"),
    content_type: str = Query("image/webp", description="MIME type del archivo comprimido"),
    db: Session = Depends(get_tenant_db_session),
    current_user = Depends(get_current_user)
):
    safe_filename = f"tickets_gastos/{uuid.uuid4().hex}_{filename}"
    schema_name = current_user.tenant.schema_name

    put_url_interna = minio_client.generate_presigned_put_url(
        tenant_schema=schema_name,
        object_name=safe_filename,
        expiry_minutes=15
    )

    external_host = os.getenv("MINIO_EXTERNAL_URL", "http://localhost:9000")
    if not external_host.startswith("http"):
        external_host = f"http://{external_host}"

    bucket = minio_client._get_tenant_vault(schema_name)
    url_publica = f"{external_host}/{bucket}/{safe_filename}"

    parsed_url = urlparse(put_url_interna)
    put_url_externa = put_url_interna.replace(f"{parsed_url.scheme}://{parsed_url.netloc}", external_host)

    return {
        "upload_url": put_url_externa,
        "final_url": url_publica
    }

# ==========================================
# EMISIÓN DE PAGOS Y LOGÍSTICA (CON IDEMPOTENCIA)
# ==========================================

@router.get("/ordenes", response_model=List[OrdenPagoResponse])
def listar_ordenes_pago(
    x_entity_id: Annotated[int, Header(description="ID de la Razón Social Activa")],
    params: BuscadorEgresosQueryParams = Depends(),
    db: Session = Depends(get_tenant_db_session),
    current_user = Depends(get_current_user)
):
    servicio = EgresosService(db=db, entidad_id=x_entity_id)
    return servicio.buscar_ordenes(params)

@router.post("/ordenes", response_model=OrdenPagoResponse, status_code=status.HTTP_201_CREATED)
def crear_orden_pago(
    payload: OrdenPagoCreate,
    x_entity_id: Annotated[int, Header(description="ID de la Razón Social Activa")],
    idempotency_key: str = Header(..., alias="Idempotency-Key", description="Llave única anti-ráfagas"),
    db: Session = Depends(get_tenant_db_session),
    current_user = Depends(get_current_user)
):
    # 🌟 FASE 6: ESCUDO DE IDEMPOTENCIA
    lock_key = f"idempotency:ordenes:{current_user.tenant.schema_name}:{idempotency_key}"
    if redis_client:
        if redis_client.get(lock_key) == "resolved":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Esta orden ya fue generada exitosamente.")
        if not redis_client.set(lock_key, "processing", nx=True, ex=30):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La orden está en proceso. Aguarde.")

    try:
        # 🌟 FASE 5: ORÁCULO CAMBIARIO
        if hasattr(payload, 'moneda') and hasattr(payload, 'tipo_cambio_estimado'):
            moneda_iso = payload.moneda.value if hasattr(payload.moneda, 'value') else str(payload.moneda)
            validar_tolerancia_cambiaria(db, moneda_iso, payload.tipo_cambio_estimado, datetime.now(timezone.utc).date())

        servicio = EgresosService(db=db, entidad_id=x_entity_id)
        user_role, umbral_aprobacion = _get_tenant_threshold_and_role(current_user)

        nueva_orden = servicio.crear_orden_pago(
            data=payload,
            user_id=str(current_user.id),
            user_role=user_role,
            umbral_aprobacion=umbral_aprobacion
        )

        if redis_client: redis_client.setex(lock_key, 86400, "resolved")
        return nueva_orden

    except Exception as e:
        if redis_client: redis_client.delete(lock_key)
        raise e

@router.post("/ordenes/pago-multiple", response_model=LotePagoResponse, status_code=status.HTTP_201_CREATED)
def procesar_pago_multiple(
    payload: OrdenPagoMultipleCreate,
    # 🌟 FIX ARQUITECTÓNICO: Los alias deben coincidir con el estándar HTTP (minúsculas)
    x_entity_id: int = Header(..., alias="x-entity-id", description="ID de la Razón Social Activa"),
    idempotency_key: str = Header(..., alias="idempotency-key", description="Llave única anti-ráfagas"),
    db: Session = Depends(get_tenant_db_session),
    current_user = Depends(get_current_user)
):
    # 🌟 FASE 6: ESCUDO DE IDEMPOTENCIA
    lock_key = f"idempotency:pago_multiple:{current_user.tenant.schema_name}:{idempotency_key}"
    if redis_client:
        if redis_client.get(lock_key) == "resolved":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Esta operación masiva ya fue procesada exitosamente.")
        if not redis_client.set(lock_key, "processing", nx=True, ex=30):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Operación en proceso. Aguarde.")

    try:
        # 🌟 FASE 5: ORÁCULO CAMBIARIO
        if hasattr(payload, 'moneda_pago') and hasattr(payload, 'tipo_cambio'):
            moneda_iso = payload.moneda_pago.value if hasattr(payload.moneda_pago, 'value') else str(payload.moneda_pago)
            validar_tolerancia_cambiaria(db, moneda_iso, payload.tipo_cambio, datetime.now(timezone.utc).date())

        servicio = EgresosService(db=db, entidad_id=x_entity_id)
        user_role, umbral_aprobacion = _get_tenant_threshold_and_role(current_user)

        nuevo_lote = servicio.crear_orden_pago_multiple(
            data=payload,
            user_id=str(current_user.id),
            user_role=user_role,
            umbral_aprobacion=umbral_aprobacion
        )

        if redis_client: redis_client.setex(lock_key, 86400, "resolved")

        if getattr(nuevo_lote, "id", 0) == 0:
            return {
                "id": 0,
                "codigo_lote": "ENCOLADO_MASIVO",
                "monto_total_lote": nuevo_lote.monto_total_lote if hasattr(nuevo_lote, 'monto_total_lote') else payload.monto_bruto_abonar,
                "estado_lote": getattr(EstadoLotePago, 'DRAFT', list(EstadoLotePago)[0]),
                "fecha_autorizacion": None,
                "cuenta_bancaria_id": None,
                "detalles": []
            }

        return db.query(LotePago).options(
            joinedload(LotePago.detalles).joinedload(LotePagoDetalle.orden_pago)
        ).filter(LotePago.id == nuevo_lote.id).first()

    except Exception as e:
        if redis_client: redis_client.delete(lock_key)
        raise e

class LiquidacionIndividualRequest(BaseModel):
    cuenta_tesoreria_id: int

@router.post(
    "/ordenes/{orden_id}/liquidar-individual",
    response_model=OrdenPagoResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(EntityRoleChecker(["admin", "dueño"]))]
)
def liquidar_orden_individual(
    orden_id: int,
    payload: LiquidacionIndividualRequest,
    x_entity_id: Annotated[int, Header(description="ID de la Razón Social Activa")],
    idempotency_key: str = Header(..., alias="Idempotency-Key", description="Llave única anti-ráfagas"),
    db: Session = Depends(get_tenant_db_session),
    current_user: CachedUser = Depends(get_current_user)
):
    # 🌟 FASE 6: ESCUDO DE IDEMPOTENCIA
    lock_key = f"idempotency:liquidar_indiv:{current_user.tenant.schema_name}:{idempotency_key}"
    if redis_client:
        if redis_client.get(lock_key) == "resolved":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Esta orden ya fue liquidada.")
        if not redis_client.set(lock_key, "processing", nx=True, ex=30):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Liquidación en proceso. Aguarde.")

    try:
        from core.services.banco_service import banco_service
        from core.schemas.banco import MovimientoBancarioCreate

        from core.database.models.tesoreria import CuentaTesoreria
        from core.database.models.pagos import OrdenPago, LotePago, LotePagoDetalle
        from core.utils.enums import EstadoOrdenPago, EstadoLotePago, EstadoComprobante, TipoComprobanteInterno
        from core.domains.comprobantes.models import Comprobante
        from core.services.trazabilidad_service import trazabilidad_service

        orden = db.query(OrdenPago).filter(
            OrdenPago.id == orden_id,
            OrdenPago.entidad_id == x_entity_id
        ).with_for_update().first()

        if not orden:
            raise HTTPException(status_code=404, detail="Orden de Pago no encontrada.")

        estado_actual = getattr(orden.estado_orden, 'name', str(orden.estado_orden))
        if estado_actual not in ["BORRADOR", "PENDIENTE_AUTORIZACION", "EN_LOTE", "FACTURA_ASIGNADA"]:
            raise HTTPException(status_code=400, detail=f"La orden no puede liquidarse. Estado actual: {estado_actual}")

        cuenta_origen = db.query(CuentaTesoreria).filter(
            CuentaTesoreria.id == payload.cuenta_tesoreria_id,
            CuentaTesoreria.entidad_id == x_entity_id,
            CuentaTesoreria.is_active == True
        ).with_for_update().first()

        if not cuenta_origen:
            raise HTTPException(status_code=404, detail="Cuenta bancaria de origen no válida.")

        moneda_cuenta = getattr(cuenta_origen.moneda, 'value', str(cuenta_origen.moneda))
        moneda_orden = getattr(orden.moneda, 'value', str(orden.moneda))

        if moneda_cuenta != moneda_orden:
            raise HTTPException(status_code=400, detail="La moneda de la cuenta bancaria no coincide con la moneda de la orden.")

        saldo_disponible = Decimal(str(cuenta_origen.saldo_actual)) - Decimal(str(getattr(cuenta_origen, 'saldo_retenido', 0.0)))
        if orden.monto_estimado > saldo_disponible:
            raise HTTPException(status_code=400, detail=f"Saldo operativo insuficiente. Disponible: ${saldo_disponible}")

        today_local = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=-3))).date()

        detalles = db.query(LotePagoDetalle).filter(LotePagoDetalle.orden_pago_id == orden.id).with_for_update().all()

        referencia_lote_banco = orden.codigo_trazabilidad
        if detalles and not detalles[0].lote_id:
            codigo_lote = trazabilidad_service.generar_trace_id(db=db, tenant_id=x_entity_id, tipo_cbte_interno=TipoComprobanteInterno.LOTE_PAGO, prefijo="LOT")
            nuevo_lote = LotePago(
                entidad_id=x_entity_id,
                codigo_lote=codigo_lote,
                moneda_pago=moneda_cuenta,
                monto_total_lote=orden.monto_estimado,
                estado_lote=getattr(EstadoLotePago, 'AUTHORIZED_FOR_PAYMENT', list(EstadoLotePago)[2]),
                cuenta_tesoreria_id=cuenta_origen.id,
                aprobado_por_id=str(current_user.id),
                fecha_autorizacion=datetime.now(timezone.utc),
                creado_por_id=str(current_user.id),
                actualizado_por_id=str(current_user.id)
            )
            db.add(nuevo_lote)
            db.flush()

            for det in detalles:
                det.lote_id = nuevo_lote.id

            referencia_lote_banco = codigo_lote
        elif detalles and detalles[0].lote_id:
            lote_existente = db.query(LotePago).filter(LotePago.id == detalles[0].lote_id).with_for_update().first()
            if lote_existente:
                lote_existente.cuenta_tesoreria_id = cuenta_origen.id
                lote_existente.estado_lote = getattr(EstadoLotePago, 'AUTHORIZED_FOR_PAYMENT', list(EstadoLotePago)[2])
                lote_existente.actualizado_por_id = str(current_user.id)
                referencia_lote_banco = lote_existente.codigo_lote

        mov_in = MovimientoBancarioCreate(
            entidad_id=x_entity_id,
            cuenta_id=cuenta_origen.id,
            cuenta_contable_id=orden.concepto_id,
            fecha=today_local,
            monto=-abs(Decimal(str(orden.monto_estimado))),
            moneda=moneda_cuenta,
            concepto_bancario_crudo=f"Pago Individual - OP {orden.codigo_trazabilidad}",
            concepto_interno="Liquidación Directa por Interfaz",
            referencia_banco=referencia_lote_banco
        )

        banco_service.registrar_movimiento_con_saldo(
            db=db, mov_in=mov_in, entidad_id=x_entity_id,
            user_id=str(current_user.id), user_role=getattr(current_user, "role", "admin"),
            umbral_aprobacion=0.0
        )

        if detalles:
            comprobantes_ids = sorted(list(set(det.comprobante_id for det in detalles if det.comprobante_id)))
            if comprobantes_ids:
                facturas = db.query(Comprobante).filter(Comprobante.id.in_(comprobantes_ids)).with_for_update().all()
                estado_en_pago = getattr(EstadoComprobante, 'EN_PAGO', 'EN_PAGO')
                estado_pagada = getattr(EstadoComprobante, 'PAGADA', 'PAGADA')

                for factura in facturas:
                    if factura.estado == estado_en_pago:
                        factura.estado = estado_pagada

        orden.estado_orden = getattr(EstadoOrdenPago, 'AUTORIZADA', getattr(EstadoOrdenPago, 'CERRADA', list(EstadoOrdenPago)[-1]))
        orden.actualizado_por_id = str(current_user.id)

        db.commit()
        db.refresh(orden)

        if redis_client: redis_client.setex(lock_key, 86400, "resolved")
        return orden

    except Exception as e:
        if redis_client: redis_client.delete(lock_key)
        raise e

class EnsamblajeBancarioRequest(BaseModel):
    cuenta_tesoreria_id: int
    ordenes_ids: List[int]

@router.post(
    "/lotes/ensamblaje-bancario",
    response_model=LotePagoResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(EntityRoleChecker(["admin", "dueño"]))]
)
def ensamblar_lote_bancario(
    payload: EnsamblajeBancarioRequest,
    x_entity_id: Annotated[int, Header(description="ID de la Razón Social Activa")],
    idempotency_key: str = Header(..., alias="Idempotency-Key", description="Llave única anti-ráfagas"),
    db: Session = Depends(get_tenant_db_session),
    current_user: CachedUser = Depends(get_current_user)
):
    # 🌟 FASE 6: ESCUDO DE IDEMPOTENCIA
    lock_key = f"idempotency:ensamblaje:{current_user.tenant.schema_name}:{idempotency_key}"
    if redis_client:
        if redis_client.get(lock_key) == "resolved":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Este ensamblaje ya fue procesado.")
        if not redis_client.set(lock_key, "processing", nx=True, ex=30):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ensamblaje en proceso. Aguarde.")

    try:
        ordenes = db.query(OrdenPago).filter(
            OrdenPago.id.in_(payload.ordenes_ids),
            OrdenPago.entidad_id == x_entity_id
        ).with_for_update().all()

        if not ordenes:
            raise HTTPException(status_code=400, detail="No se encontraron las órdenes solicitadas o ya fueron procesadas.")

        monto_total = sum(op.monto_estimado for op in ordenes)

        import uuid
        codigo_lote = f"IBK-{x_entity_id}-{uuid.uuid4().hex[:6].upper()}"

        nuevo_lote = LotePago(
            entidad_id=x_entity_id,
            cuenta_tesoreria_id=payload.cuenta_tesoreria_id,
            creado_por_id=str(current_user.id),
            codigo_lote=codigo_lote,
            moneda_pago=ordenes[0].moneda,
            monto_total_lote=monto_total,
            estado_lote=EstadoLotePago.AUTHORIZED_FOR_PAYMENT,
            aprobado_por_id=str(current_user.id),
            fecha_autorizacion=datetime.now(timezone.utc)
        )
        db.add(nuevo_lote)
        db.flush()

        estado_cerrado = getattr(EstadoOrdenPago, 'AUTORIZADA', list(EstadoOrdenPago)[-1])
        if hasattr(EstadoOrdenPago, 'EN_LOTE'):
            estado_cerrado = EstadoOrdenPago.EN_LOTE
        elif hasattr(EstadoOrdenPago, 'PENDIENTE_PAGO'):
            estado_cerrado = EstadoOrdenPago.PENDIENTE_PAGO

        for op in ordenes:
            detalle = LotePagoDetalle(
                lote_id=nuevo_lote.id,
                orden_pago_id=op.id,
                creado_por_id=str(current_user.id),
                monto_asignado_moneda_origen=op.monto_estimado,
                monto_asignado_ars=op.monto_estimado,
                tipo_cambio_aplicado=op.tipo_cambio_estimado
            )
            db.add(detalle)

            op.estado_orden = estado_cerrado
            op.actualizado_por_id = str(current_user.id)
            db.add(op)

        db.commit()

        if redis_client: redis_client.setex(lock_key, 86400, "resolved")

        return db.query(LotePago).options(
            joinedload(LotePago.detalles).joinedload(LotePagoDetalle.orden_pago)
        ).filter(LotePago.id == nuevo_lote.id).first()

    except Exception as e:
        if redis_client: redis_client.delete(lock_key)
        raise e

# ==========================================
# RUTAS RESTANTES DE LOTES (Consultas y transiciones menores)
# ==========================================

@router.get("/lotes", response_model=List[LotePagoResponse])
def listar_lotes_pago(
    x_entity_id: Annotated[int, Header(description="ID de la Razón Social Activa")],
    db: Session = Depends(get_tenant_db_session),
    current_user = Depends(get_current_user)
):
    lotes = db.query(LotePago).options(
        joinedload(LotePago.detalles).joinedload(LotePagoDetalle.orden_pago)
    ).filter(LotePago.entidad_id == x_entity_id).order_by(LotePago.created_at.desc()).limit(100).all()
    return lotes

@router.post("/lotes", response_model=LotePagoResponse, status_code=status.HTTP_201_CREATED)
def crear_lote_pago(
    payload: LotePagoCreate,
    x_entity_id: Annotated[int, Header(description="ID de la Razón Social Activa")],
    db: Session = Depends(get_tenant_db_session),
    current_user = Depends(get_current_user)
):
    servicio = EgresosService(db=db, entidad_id=x_entity_id)
    nuevo_lote = servicio.crear_lote_draft(data=payload, user_id=str(current_user.id))

    lote_hidratado = db.query(LotePago).options(
        joinedload(LotePago.detalles).joinedload(LotePagoDetalle.orden_pago)
    ).filter(LotePago.id == nuevo_lote.id).first()

    return lote_hidratado

@router.patch("/lotes/{lote_id}/solicitar-autorizacion", response_model=LotePagoResponse)
def solicitar_autorizacion_lote(
    lote_id: int,
    x_entity_id: Annotated[int, Header(description="ID de la Razón Social Activa")],
    db: Session = Depends(get_tenant_db_session),
    current_user = Depends(get_current_user)
):
    servicio = EgresosService(db=db, entidad_id=x_entity_id)
    lote_actualizado = servicio.solicitar_autorizacion(lote_id=lote_id, user_id=str(current_user.id))

    return db.query(LotePago).options(
        joinedload(LotePago.detalles).joinedload(LotePagoDetalle.orden_pago)
    ).filter(LotePago.id == lote_actualizado.id).first()

@router.patch("/lotes/{lote_id}/autorizar", response_model=LotePagoResponse, dependencies=[Depends(EntityRoleChecker(["admin", "dueño"]))])
def autorizar_lote_pago(
    lote_id: int,
    payload: AutorizarLoteRequest,
    x_entity_id: Annotated[int, Header(description="ID de la Razón Social Activa")],
    db: Session = Depends(get_tenant_db_session),
    current_user = Depends(get_current_user)
):
    servicio = EgresosService(db=db, entidad_id=x_entity_id)

    lote_actualizado = servicio.autorizar_lote(
        lote_id=lote_id,
        user_id=str(current_user.id),
        cuenta_bancaria_id=payload.cuenta_bancaria_id
    )

    return db.query(LotePago).options(
        joinedload(LotePago.detalles).joinedload(LotePagoDetalle.orden_pago)
    ).filter(LotePago.id == lote_actualizado.id).first()

@router.get("/lotes/{lote_id}/exportar-interbanking")
def exportar_lote_interbanking(
    lote_id: int,
    x_entity_id: Annotated[int, Header(description="ID de la Razón Social Activa")],
    db: Session = Depends(get_tenant_db_session),
    current_user = Depends(get_current_user)
):
    lote = db.query(LotePago).options(
        joinedload(LotePago.detalles).joinedload(LotePagoDetalle.orden_pago).joinedload(OrdenPago.proveedor)
    ).filter(
        LotePago.id == lote_id,
        LotePago.entidad_id == x_entity_id
    ).first()

    if not lote:
        raise HTTPException(status_code=404, detail="Lote no encontrado o fuera del alcance de la entidad activa.")

    if lote.estado_lote != EstadoLotePago.AUTHORIZED_FOR_PAYMENT:
        raise HTTPException(
            status_code=400,
            detail=f"Exportación denegada. El lote debe estar Autorizado. Estado: {lote.estado_lote}"
        )

    adaptador = InterbankingAdapter()
    buffer = adaptador.generar_archivo(lote, lote.detalles)

    headers = {
        "Content-Disposition": f"attachment; filename=interbanking_{lote.codigo_lote}.txt"
    }

    return StreamingResponse(buffer, media_type="text/plain", headers=headers)

@router.post(
    "/ordenes/{orden_id}/anular",
    response_model=OrdenPagoResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(EntityRoleChecker(["admin", "dueño"]))]
)
def anular_orden_pago(
    orden_id: int,
    x_entity_id: Annotated[int, Header(alias="X-Entity-ID", description="ID de la Razón Social Activa")],
    idempotency_key: str = Header(None, alias="Idempotency-Key", description="Opcional. Llave del frontend para prevenir doble click."),
    db: Session = Depends(get_tenant_db_session),
    current_user: CachedUser = Depends(get_current_user)
):
    """
    Anulación transaccional de Orden de Pago.
    Genera contra-asientos y revierte efectos impositivos de forma atómica.
    """
    # 🌟 FIX FASE 3.2: Candado Distribuido en Memoria (Redis)
    # Generamos una firma única usando el tenant, la OP y el usuario.
    base_signature = f"{x_entity_id}:{orden_id}:{current_user.id}"
    lock_hash = hashlib.sha256(base_signature.encode()).hexdigest()
    lock_key = f"idempotency:pagos:anular:{lock_hash}"

    if idempotency_key:
        lock_key += f":{idempotency_key}"

    if redis_client:
        # Intentamos adquirir el candado atómicamente con 30s de TTL
        lock_adquirido = redis_client.set(lock_key, "processing", nx=True, ex=30)
        if not lock_adquirido:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La orden ya está siendo procesada. Por favor, aguarde."
            )

    try:
        user_role, umbral_aprobacion = _get_tenant_threshold_and_role(current_user)

        resultado = reversiones_service.anular_orden_pago(
            db=db,
            entidad_id=x_entity_id,
            orden_id=orden_id,
            user_id=str(current_user.id),
            user_role=user_role,
            umbral_aprobacion=umbral_aprobacion
        )

        # 🌟 Lápida de Idempotencia: Si fue un éxito, bloqueamos futuros intentos idénticos por 1 minuto
        if redis_client:
            redis_client.setex(lock_key, 60, "resolved")

        return resultado

    except HTTPException as http_exc:
        # Liberamos el candado si hubo un error validado (ej. no encontrada) para permitir reintentos
        if redis_client:
            redis_client.delete(lock_key)
        raise http_exc
    except Exception as e:
        # Liberamos el candado ante errores internos no controlados
        if redis_client:
            redis_client.delete(lock_key)
        raise e