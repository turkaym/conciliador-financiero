import logging
from typing import List, Optional, Any
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Query, Header, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc
from sqlalchemy.sql import func
from pydantic import BaseModel, Field

# 🌟 FIX FASE A: Importaciones de Infraestructura y Seguridad (Se mantienen globales)
from core.api.deps import get_tenant_db_session, get_current_user, CachedUser, EntityRoleChecker, get_afip_client
from core.tasks.afip_tasks import sync_arca_comprobantes
from core.utils.enums import ClaseDocumento
from core.database.models_tenant import ColaMensajesMuertos, RazonSocialPropia

# 🌟 FIX FASE A: Importaciones Orientadas a Dominio (DDD)
from core.domains.comprobantes.models import Comprobante
from core.domains.comprobantes.schemas import ComprobanteCreate, ComprobanteResponse, SyncTaskResponse
from core.domains.comprobantes.service import comprobante_service

logger = logging.getLogger("DOMAIN_COMPROBANTES_API")

# 🌟 FIX ARQUITECTURA: El Router se apropia de su prefijo
router = APIRouter(prefix="/v1/comprobantes", tags=["Comprobantes"])

class SyncAfipPayload(BaseModel):
    punto_venta: int = Field(..., ge=1, le=99999, description="Punto de venta oficial")
    tipo_cbte: int = Field(..., ge=1, le=999, description="Código de comprobante AFIP")

@router.get("/", response_model=List[ComprobanteResponse], dependencies=[Depends(EntityRoleChecker(["admin", "dueño", "editor", "operador"]))])
def list_comprobantes(
    entidad_id: int = Header(..., alias="X-Entity-ID", description="ID de la empresa activa"),
    clase_documento: Optional[ClaseDocumento] = Query(None, description="Filtrar por clase lógica"),
    cuit_receptor: Optional[str] = Query(None, description="Filtrar por CUIT"),
    tipo_operacion: Optional[str] = Query(None, description="Filtrar por VENTA o COMPRA"),
    estado: Optional[str] = Query(None, description="Filtrar por estado operativo"),
    fecha_desde: Optional[datetime] = Query(None, description="Fecha de inicio (ISO 8601)"),
    fecha_hasta: Optional[datetime] = Query(None, description="Fecha de fin (ISO 8601)"),
    db: Session = Depends(get_tenant_db_session),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    hasta = fecha_hasta or datetime.now(timezone.utc)
    desde = fecha_desde or (hasta - timedelta(days=30))

    if (hasta - desde).days > 180:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El rango de búsqueda no puede superar los 180 días por políticas de rendimiento OLAP."
        )

    # 🌟 FIX ARQUITECTURA: Ocultamos los documentos "Espejo" transaccionales de la vista de usuarios
    query = db.query(Comprobante).filter(
        Comprobante.entidad_id == entidad_id,
        Comprobante.is_active == True,
        Comprobante.fecha_emision >= desde.date(),
        Comprobante.fecha_emision <= hasta.date(),
        Comprobante.tipo_operacion != "ORDEN_PAGO_MIRROR"
    )

    if clase_documento:
        query = query.filter(Comprobante.clase_documento == clase_documento)
    if cuit_receptor:
        clean_cuit = "".join(filter(str.isdigit, cuit_receptor))
        if clean_cuit:
            query = query.filter(Comprobante.cuit_receptor == clean_cuit)
    if tipo_operacion:
        query = query.filter(Comprobante.tipo_operacion == tipo_operacion)
    if estado:
        query = query.filter(Comprobante.estado == estado)

    comprobantes = query.order_by(desc(Comprobante.fecha_emision)).offset(skip).limit(limit).all()

    return comprobantes

@router.get("/pendientes-proveedor/{proveedor_id}", response_model=List[ComprobanteResponse], dependencies=[Depends(EntityRoleChecker(["admin", "dueño", "editor", "operador"]))])
def listar_pendientes_proveedor(
    proveedor_id: int,
    entidad_id: int = Header(..., alias="X-Entity-ID"),
    db: Session = Depends(get_tenant_db_session)
):
    """
    Endpoint de alta performance para alimentar el modal de órdenes de pago.
    Solo devuelve deuda viva (saldo > 0) del proveedor especificado.
    """
    return comprobante_service.obtener_pendientes_proveedor(db, entidad_id, proveedor_id)

@router.post("/", response_model=ComprobanteResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(EntityRoleChecker(["admin", "dueño", "editor", "operador"]))])
def crear_comprobante_manual(
    comprobante_in: ComprobanteCreate,
    entidad_id: int = Header(..., alias="X-Entity-ID"),
    db: Session = Depends(get_tenant_db_session),
    current_user: CachedUser = Depends(get_current_user)
):
    usuario_id_str = str(getattr(current_user, 'id', getattr(current_user, 'email', 'unknown')))
    return comprobante_service.crear_comprobante_con_vinculo(
        db=db,
        comprobante_in=comprobante_in,
        tenant_id=entidad_id,
        usuario_id=usuario_id_str
    )

@router.post("/emitir-electronica", response_model=ComprobanteResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(EntityRoleChecker(["admin", "dueño", "editor", "operador"]))])
def emitir_comprobante_electronico_afip(
    comprobante_in: ComprobanteCreate,
    entidad_id: int = Header(..., alias="X-Entity-ID"),
    db: Session = Depends(get_tenant_db_session),
    afip_client: Any = Depends(get_afip_client)
):
    comprobante_in.entidad_id = entidad_id
    return comprobante_service.emitir_y_guardar_comprobante(
        db=db,
        afip_client=afip_client,
        comprobante_in=comprobante_in,
        tenant_id=entidad_id
    )

@router.delete("/{comprobante_id}", status_code=status.HTTP_200_OK, dependencies=[Depends(EntityRoleChecker(["admin", "dueño", "editor"]))])
def anular_comprobante(
    comprobante_id: int,
    entidad_id: int = Header(..., alias="X-Entity-ID"),
    db: Session = Depends(get_tenant_db_session)
):
    comprobante_service.anular_comprobante_seguro(db, comprobante_id, entidad_id)
    return {"status": "success", "message": "Comprobante anulado y saldos revertidos con éxito."}

@router.post("/sync-afip", response_model=SyncTaskResponse, status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(EntityRoleChecker(["admin", "dueño", "editor"]))])
def trigger_sync(
    payload: SyncAfipPayload,
    request: Request,
    entidad_id: int = Header(..., alias="X-Entity-ID"),
    db: Session = Depends(get_tenant_db_session),
    current_user: CachedUser = Depends(get_current_user)
):
    schema_name = current_user.tenant.schema_name

    entidad = db.query(RazonSocialPropia).filter(
        RazonSocialPropia.id == entidad_id,
        RazonSocialPropia.is_active == True
    ).with_for_update(nowait=True).first()

    if not entidad:
        raise HTTPException(status_code=404, detail="Entidad activa no encontrada o bloqueada por operación concurrente.")

    if not entidad.afip_certificate or not entidad.afip_private_key_encrypted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La entidad no tiene credenciales AFIP configuradas en la bóveda fiscal."
        )

    try:
        task = sync_arca_comprobantes.apply_async(
            kwargs={
                "tenant_id": schema_name,
                "entidad_id": entidad_id,
                "punto_venta": payload.punto_venta,
                "tipo_cbte": payload.tipo_cbte
                # 🌟 FIX ARQUITECTURA: Se eliminó el 'correlation_id' fantasma
            },
            queue='accounting_queue',
            retry=False,
            expires=60
        )
        return {
            "task_id": task.id,
            "status": "PENDING",
            "message": f"Sincronización encolada exitosamente para PV {payload.punto_venta}."
        }
    except Exception as e:
        logger.error(f"❌ Fallo al encolar tarea AFIP: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No se pudo conectar con el broker de tareas."
        )

@router.get("/alertas", status_code=status.HTTP_200_OK, dependencies=[Depends(EntityRoleChecker(["admin", "dueño", "editor", "operador"]))])
def obtener_alertas_fiscales(
    entidad_id: int = Header(..., alias="X-Entity-ID"),
    db: Session = Depends(get_tenant_db_session)
):
    query_dlq = db.query(ColaMensajesMuertos).filter(
        ColaMensajesMuertos.entidad_id == entidad_id,
        ColaMensajesMuertos.resuelto == False
    )
    total_dlq = query_dlq.count()
    dlq_items = query_dlq.order_by(desc(ColaMensajesMuertos.created_at)).limit(50).all()

    limite_tiempo = datetime.utcnow() - timedelta(hours=24)
    query_cae = db.query(Comprobante).filter(
        Comprobante.entidad_id == entidad_id,
        Comprobante.estado == 'BORRADOR',
        Comprobante.created_at < limite_tiempo
    )
    total_cae = query_cae.count()
    borradores_estancados = query_cae.order_by(desc(Comprobante.created_at)).limit(50).all()

    total_real = total_dlq + total_cae

    return {
        "estado_salud": "CRITICO" if total_real > 0 else "OPTIMO",
        "total_alertas": total_real,
        "alertas_dlq": [
            {
                "id_registro": item.id,
                "punto_venta": item.punto_venta,
                "tipo_cbte_afip": item.tipo_cbte_afip,
                "numero": item.numero,
                "error": item.error_msg,
                "fecha_falla": item.created_at.isoformat() if item.created_at else None
            } for item in dlq_items
        ],
        "alertas_cae": [
            {
                "id_comprobante": comp.id,
                "punto_venta": comp.punto_venta,
                "numero_interno": comp.numero,
                "fecha_creacion": comp.created_at.isoformat() if comp.created_at else None,
                "riesgo": "Comprobante sin validez fiscal (Falta CAE)"
            } for comp in borradores_estancados
        ]
    }

@router.patch("/alertas/{alerta_id}/resolver", status_code=status.HTTP_200_OK, dependencies=[Depends(EntityRoleChecker(["admin", "dueño", "editor"]))])
def resolver_alerta_dlq(
    alerta_id: int,
    entidad_id: int = Header(..., alias="X-Entity-ID"),
    db: Session = Depends(get_tenant_db_session),
    current_user: CachedUser = Depends(get_current_user)
):
    alerta = db.query(ColaMensajesMuertos).filter(
        ColaMensajesMuertos.id == alerta_id,
        ColaMensajesMuertos.entidad_id == entidad_id
    ).with_for_update().first()

    if not alerta:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alerta no encontrada o sin privilegios.")

    usuario_id_str = str(getattr(current_user, 'id', getattr(current_user, 'email', 'unknown')))

    alerta.resuelto = True
    alerta.resolved_by_id = usuario_id_str
    alerta.resolved_at = func.now()

    db.commit()
    return {"status": "success", "message": "Alerta marcada como resuelta."}

@router.patch("/alertas/resolver-todas", status_code=status.HTTP_200_OK, dependencies=[Depends(EntityRoleChecker(["admin", "dueño"]))])
def resolver_todas_alertas_dlq(
    entidad_id: int = Header(..., alias="X-Entity-ID"),
    db: Session = Depends(get_tenant_db_session),
    current_user: CachedUser = Depends(get_current_user)
):
    usuario_id_str = str(getattr(current_user, 'id', getattr(current_user, 'email', 'unknown')))

    alertas_a_resolver = db.query(ColaMensajesMuertos.id).filter(
        ColaMensajesMuertos.entidad_id == entidad_id,
        ColaMensajesMuertos.resuelto == False
    ).limit(500).all()

    if alertas_a_resolver:
        ids_lista = [a.id for a in alertas_a_resolver]
        db.query(ColaMensajesMuertos).filter(ColaMensajesMuertos.id.in_(ids_lista)).update({
            "resuelto": True,
            "resolved_by_id": usuario_id_str,
            "resolved_at": func.now()
        }, synchronize_session=False)
        db.commit()

    return {"status": "success", "message": "Lote de alertas marcado como resuelto exitosamente."}