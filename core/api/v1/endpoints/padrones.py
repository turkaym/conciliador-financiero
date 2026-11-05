import logging
from datetime import datetime
from fastapi import APIRouter, Depends, Form, HTTPException, status, Query, Header, Request
from pydantic import BaseModel
from typing import Dict, List
from sqlalchemy.orm import Session
from datetime import datetime
from core.database.models.sistema import HistorialIngestaPadron, PadronFiscal

from core.storage.minio_client import minio_client
from core.tasks.celery_config import app as celery_app

# 🌟 FIX: Migración a EntityRoleChecker para aislamiento Multi-Tenant
from core.api.deps import get_current_user, CachedUser, EntityRoleChecker, get_tenant_db_session

logger = logging.getLogger("API_PADRONES")

# 🌟 FIX RBAC: Blindaje perimetral cruzado con la tabla de Entidades.
router = APIRouter(dependencies=[Depends(EntityRoleChecker(["admin", "dueño", "editor", "operador"]))])

# ==========================================
# 🛡️ VALIDACIONES DE NEGOCIO
# ==========================================
def validar_periodo_historico(periodo: str):
    """Verifica que el período YYYYMM no sea futuro."""
    if len(periodo) != 6 or not periodo.isdigit():
        raise HTTPException(status_code=400, detail="Formato de período inválido. Debe ser YYYYMM.")

    hoy = datetime.now()
    periodo_actual = hoy.year * 100 + hoy.month
    periodo_ingresado = int(periodo)

    if periodo_ingresado > periodo_actual:
        raise HTTPException(
            status_code=400,
            detail=f"Operación denegada. No se puede ingestar un padrón de un período futuro ({periodo})."
        )

# ==========================================
# 🚀 FLUJO ENTERPRISE: PRE-SIGNED POST POLICY
# ==========================================

class PresignedUrlResponse(BaseModel):
    upload_url: str
    form_fields: Dict[str, str]
    object_name: str
    expires_in_minutes: int

class HistorialIngestaResponse(BaseModel):
    id: int
    jurisdiccion: str
    periodo: str
    nombre_archivo: str
    estado: str
    registros_insertados: int
    mensaje_error: str | None = None
    tarea_celery_id: str | None = None
    iniciado_el: datetime
    finalizado_el: datetime | None = None

    class Config:
        from_attributes = True

class PadronFiscalResponse(BaseModel):
    cuit: str
    jurisdiccion: str
    periodo: str
    alicuota_retencion: float
    alicuota_percepcion: float
    coeficiente_riesgo: float | None = None

    class Config:
        from_attributes = True

@router.post("/ingesta/confirm", status_code=status.HTTP_202_ACCEPTED)
def confirm_upload_and_trigger(
    request: Request,
    jurisdiccion: str = Form(..., description="Jurisdicción del padrón (Ej: ARBA)"),
    periodo: str = Form(..., description="Período fiscal en formato YYYYMM"),
    object_name: str = Form(..., description="El object_name devuelto en el Paso 1"),
    x_entity_id: int = Header(..., alias="X-Entity-ID", description="ID de la Razón Social Activa"),
    current_user: CachedUser = Depends(get_current_user)
):
    """PASO 2: Confirmación para subida simple."""
    validar_periodo_historico(periodo)

    tenant_id = current_user.tenant.schema_name
    bucket_name = tenant_id.replace("_", "-")

    # 🌟 FIX ARQUITECTURA: Propagación de Entidad y Trazabilidad (UUID) al Worker
    task = celery_app.send_task(
        'core.tasks.padrones_worker.procesar_padron_fiscal',
        args=[tenant_id, bucket_name, object_name, jurisdiccion, periodo],
        kwargs={
            "entidad_id": x_entity_id,
            "correlation_id": getattr(request.state, 'correlation_id', None)
        },
        queue='afip_queue'
    )

    return {
        "status": "ACCEPTED",
        "task_id": task.id,
        "message": "Confirmación recibida. Padrones encolados para procesamiento asíncrono."
    }

class MultipartConfirmRequest(BaseModel):
    jurisdiccion: str
    periodo: str
    final_object_name: str
    source_objects: List[str]

@router.post("/ingesta/multipart/confirm", status_code=status.HTTP_202_ACCEPTED)
def confirm_multipart_upload(
    payload: MultipartConfirmRequest,
    request: Request,
    x_entity_id: int = Header(..., alias="X-Entity-ID"),
    current_user: CachedUser = Depends(get_current_user)
):
    """PASO 3 (Multipart): Ensamblaje Zero-Copy."""
    validar_periodo_historico(payload.periodo)

    tenant_id = current_user.tenant.schema_name
    bucket_name = tenant_id.replace("_", "-")

    try:
        logger.info(f"🧩 Iniciando ensamblaje de {len(payload.source_objects)} partes para {payload.final_object_name}")
        minio_client.compose_file(
            tenant_schema=tenant_id,
            target_object=payload.final_object_name,
            source_objects=payload.source_objects
        )
    except Exception as e:
        logger.error(f"Fallo al ensamblar archivo multipart: {e}")
        raise HTTPException(status_code=500, detail="Fallo en la bóveda al intentar consolidar el archivo maestro.")

    task = celery_app.send_task(
        'core.tasks.padrones_worker.procesar_padron_fiscal',
        args=[tenant_id, bucket_name, payload.final_object_name, payload.jurisdiccion, payload.periodo],
        kwargs={
            "entidad_id": x_entity_id,
            "correlation_id": getattr(request.state, 'correlation_id', None)
        },
        queue='afip_queue'
    )

    return {
        "status": "ACCEPTED",
        "task_id": task.id,
        "message": "Archivo consolidado exitosamente. Padrones encolados para procesamiento."
    }

@router.post("/cotizaciones/sincronizar", status_code=status.HTTP_202_ACCEPTED)
def forzar_sincronizacion_cotizacion(
    request: Request,
    moneda: str = Query("USD", description="Código de moneda ISO 4217"),
    origen: str = Query("BNA", description="Fuente de la cotización (BNA, AFIP)"),
    x_entity_id: int = Header(..., alias="X-Entity-ID"),
    current_user: CachedUser = Depends(get_current_user)
):
    tenant_id = current_user.tenant.schema_name
    try:
        task = celery_app.send_task(
            'core.tasks.cotizacion_worker.sincronizar_cotizacion_diaria',
            args=[tenant_id, moneda.upper(), origen.upper()],
            kwargs={"correlation_id": getattr(request.state, 'correlation_id', None)},
            queue='afip_queue',
            expires=120
        )
        return {
            "status": "ACCEPTED",
            "task_id": task.id,
            "message": f"Orden de sincronización para {moneda.upper()} enviada al motor asíncrono."
        }
    except Exception as e:
        logger.error(f"Fallo al encolar tarea de cotización: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="El motor asíncrono no está disponible. Intente más tarde.")

# ==========================================
# 📊 TELEMETRÍA E INSPECCIÓN FISCAL
# ==========================================

@router.get("/historial", response_model=List[HistorialIngestaResponse])
def obtener_historial_ingestas(
    x_entity_id: int = Header(..., alias="X-Entity-ID"),
    db: Session = Depends(get_tenant_db_session),
    current_user: CachedUser = Depends(get_current_user)
):
    """Obtiene el historial de subidas de padrones de la entidad activa."""
    historial = db.query(HistorialIngestaPadron).filter(
        HistorialIngestaPadron.entidad_id == x_entity_id
    ).order_by(HistorialIngestaPadron.iniciado_el.desc()).limit(50).all()

    return historial

@router.get("/consulta/{cuit}", response_model=PadronFiscalResponse)
def consultar_padron_cuit(
    cuit: str,
    jurisdiccion: str = Query(..., description="Ej: ARBA, AGIP"),
    periodo: str = Query(..., description="Ej: 202607"),
    x_entity_id: int = Header(..., alias="X-Entity-ID"),
    db: Session = Depends(get_tenant_db_session),
    current_user: CachedUser = Depends(get_current_user)
):
    """Inspector fiscal: Busca las alícuotas exactas de un CUIT en un padrón específico."""
    registro = db.query(PadronFiscal).filter(
        PadronFiscal.entidad_id == x_entity_id,
        PadronFiscal.cuit == cuit,
        PadronFiscal.jurisdiccion == jurisdiccion.upper(),
        PadronFiscal.periodo == periodo
    ).first()

    if not registro:
        raise HTTPException(
            status_code=404,
            detail=f"El CUIT {cuit} no fue encontrado en el padrón de {jurisdiccion.upper()} para el período {periodo}."
        )

    return registro