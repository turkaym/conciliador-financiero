import os
import logging
import hashlib
import uuid
from typing import List, Optional, Dict, Literal

from fastapi import APIRouter, Depends, Query, status, HTTPException, Header, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from core.api.deps import get_tenant_db_session, get_current_user, CachedUser, EntityRoleChecker, redis_client
from core.services.banco_service import banco_service
from core.database.models.tesoreria import CuentaTesoreria
from core.api.rate_limiter import RateLimiter
from core.storage.minio_client import minio_client
from core.parsers.bancos.heuristic_parser import HeuristicEngine
from core.database.models_tenant import ContactoComercial

from core.schemas.banco import (
    CuentaBancariaRequest, CuentaBancariaCreate, CuentaBancariaResponse,
    MovimientoBancarioRequest, MovimientoBancarioCreate, MovimientoBancarioResponse,
    MovimientosPaginadosResponse
)

logger = logging.getLogger("API_BANCOS")
logger.setLevel(logging.INFO)

router = APIRouter(
    dependencies=[Depends(EntityRoleChecker(["admin", "dueño", "operador", "visor", "editor"]))]
)

# ==========================================
# RUTAS PARA CUENTAS BANCARIAS
# ==========================================

@router.get("/cuentas", response_model=List[CuentaBancariaResponse])
def list_cuentas(
    x_entity_id: int = Header(..., alias="X-Entity-ID", description="ID de la Razón Social Activa"),
    db: Session = Depends(get_tenant_db_session),
    current_user: CachedUser = Depends(get_current_user)
):
    try:
        return banco_service.obtener_cuentas(db, entidad_id=x_entity_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error(f"Error listando cuentas: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno listando cuentas bancarias.")

@router.post("/cuentas", response_model=CuentaBancariaResponse, status_code=status.HTTP_201_CREATED)
def create_cuenta(
    cuenta_in: CuentaBancariaRequest,
    x_entity_id: int = Header(..., alias="X-Entity-ID"),
    db: Session = Depends(get_tenant_db_session),
    current_user: CachedUser = Depends(get_current_user)
):
    try:
        payload = cuenta_in.model_dump()

        # 🌟 FIX: 'banco' ya es un string (texto libre), ya no usamos .value
        # Hacemos una extracción segura para los otros campos por si mantuviste los Enums ahí
        if hasattr(cuenta_in.tipo_cuenta, 'value'):
            payload["tipo_cuenta"] = cuenta_in.tipo_cuenta.value
        if hasattr(cuenta_in.moneda, 'value'):
            payload["moneda"] = cuenta_in.moneda.value

        cuenta_create = CuentaBancariaCreate(**payload, entidad_id=x_entity_id)

        return banco_service.crear_cuenta(db, cuenta_create, user_id=current_user.id)

    except HTTPException as http_exc:
        raise http_exc

    except IntegrityError as e:
        db.rollback()
        logger.warning(f"⚠️ Conflicto de integridad en DB: {str(e.orig)}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe una cuenta con esos datos: {str(e.orig).split('Key ')[-1]}"
        )

    except Exception as e:
        logger.error(f"Error crítico creando cuenta bancaria: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno al registrar la cuenta bancaria.")


@router.get("/proveedores-clearing", status_code=status.HTTP_200_OK)
def listar_proveedores_clearing(
    x_entity_id: int = Header(..., alias="X-Entity-ID"),
    db: Session = Depends(get_tenant_db_session),
    current_user: CachedUser = Depends(get_current_user)
):
    try:
        proveedores = db.query(ContactoComercial).filter(
            ContactoComercial.entidad_id == x_entity_id,
            ContactoComercial.is_active == True,
            ContactoComercial.is_entidad_financiera == True
        ).all()

        return [
            {
                "id": p.id,
                "razon_social": p.razon_social,
                "cuit": p.cuit
            }
            for p in proveedores
        ]
    except Exception as e:
        logger.error(f"Error listando proveedores de clearing: {e}")
        raise HTTPException(status_code=500, detail="Error interno consultando pasarelas.")

# ==========================================
# RUTAS PARA MOVIMIENTOS Y EXTRACOTS
# ==========================================

@router.get("/movimientos", response_model=MovimientosPaginadosResponse)
def list_movimientos(
    cuenta_id: int = Query(..., description="ID de cuenta específica (Requerido)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    x_entity_id: int = Header(..., alias="X-Entity-ID"),
    db: Session = Depends(get_tenant_db_session),
    current_user: CachedUser = Depends(get_current_user)
):
    try:
        return banco_service.obtener_extracto_inteligente(db, cuenta_id, skip, limit, entidad_id=x_entity_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error(f"Error listando movimientos: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno consultando los movimientos.")

@router.post("/movimientos", response_model=MovimientoBancarioResponse, status_code=status.HTTP_201_CREATED)
def create_movimiento(
    movimiento_in: MovimientoBancarioRequest,
    x_entity_id: int = Header(..., alias="X-Entity-ID"),
    db: Session = Depends(get_tenant_db_session),
    current_user: CachedUser = Depends(get_current_user)
):
    try:
        mov_create = MovimientoBancarioCreate(**movimiento_in.model_dump(), entidad_id=x_entity_id)

        user_role = getattr(current_user, "role", "operador")

        umbral_aprobacion = 0.0
        if hasattr(current_user, "tenant") and current_user.tenant and hasattr(current_user.tenant, "features") and isinstance(current_user.tenant.features, dict):
            umbral_aprobacion = float(current_user.tenant.features.get("umbral_aprobacion", 0.0))

        if umbral_aprobacion == 0.0:
             umbral_aprobacion = 10000.00

        return banco_service.registrar_movimiento_con_saldo(
            db=db,
            mov_in=mov_create,
            entidad_id=x_entity_id,
            user_id=current_user.id,
            user_role=user_role,
            umbral_aprobacion=umbral_aprobacion
        )
    except HTTPException as http_exc:
        raise http_exc
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El movimiento ya existe.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error creando movimiento manual: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno al registrar el movimiento.")


class ResolucionAprobacionRequest(BaseModel):
    registro_id: int
    tipo_registro: Literal["MOVIMIENTO", "SOLICITUD"]
    accion: str
    motivo_rechazo: Optional[str] = None

# 🌟 FIX FASE 2.2: Eliminación de {movimiento_id} en la URL. Endpoint genérico.
@router.post(
    "/movimientos/resolucion",
    response_model=MovimientoBancarioResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(EntityRoleChecker(["admin", "editor"]))]
)
def resolver_movimiento_pendiente(
    req: ResolucionAprobacionRequest,
    x_entity_id: int = Header(..., alias="X-Entity-ID"),
    idempotency_key: str = Header(..., alias="Idempotency-Key", description="Llave única para prevenir resoluciones duplicadas"),
    db: Session = Depends(get_tenant_db_session),
    current_user: CachedUser = Depends(get_current_user)
):
    lock_key = f"idempotency:bancos:{current_user.tenant.schema_name}:{idempotency_key}"

    if redis_client:
        existing_val = redis_client.get(lock_key)
        if existing_val == "resolved":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Esta operación ya fue procesada exitosamente.")

        # 🌟 FIX FASE 2.2: Firma de idempotencia basada en la tupla estricta (tipo + id)
        payload_signature = hashlib.sha256(f"{req.tipo_registro}:{req.registro_id}:{req.accion.lower()}".encode()).hexdigest()

        lock_adquirido = redis_client.set(lock_key, payload_signature, nx=True, ex=30)

        if not lock_adquirido:
            logger.warning(f"🛡️ [IDEMPOTENCIA] Ráfaga HTTP interceptada. Llave en uso: {idempotency_key}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Esta operación ya está siendo procesada. Por favor aguarde."
            )

    try:
        # 🌟 FIX FASE 2.2: Pasamos los campos de routing desacoplados al servicio
        resultado = banco_service.resolver_aprobacion_movimiento(
            db=db,
            registro_id=req.registro_id,
            tipo_registro=req.tipo_registro,
            entidad_id=x_entity_id,
            accion=req.accion.lower(),
            admin_id=current_user.id,
            motivo_rechazo=req.motivo_rechazo
        )

        if redis_client:
            redis_client.setex(lock_key, 86400, "resolved")

        return resultado

    except PermissionError as e:
        if redis_client: redis_client.delete(lock_key)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    except ValueError as e:
        db.rollback()
        if redis_client: redis_client.delete(lock_key)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    except Exception as e:
        db.rollback()
        if redis_client: redis_client.delete(lock_key)
        logger.error(f"Error resolviendo {req.tipo_registro} {req.registro_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Fallo interno al resolver la transacción.")

# ==========================================
# INGESTA MASIVA Y MOTOR X-RAY (FASE 7)
# ==========================================
import asyncio

@router.get("/ingesta/analyze-format", status_code=status.HTTP_200_OK, dependencies=[Depends(EntityRoleChecker(["admin", "operador", "editor"]))])
async def analyze_unknown_bank_format(
    object_name: str = Query(..., description="El object_name del archivo recién subido a MinIO"),
    current_user: CachedUser = Depends(get_current_user)
):
    tenant_id = current_user.tenant.schema_name
    bucket_name = tenant_id.replace("_", "-")

    _, original_extension = os.path.splitext(object_name)
    file_extension = original_extension.lower()

    if file_extension not in ['.csv', '.txt', '.xls', '.xlsx']:
         raise HTTPException(status_code=400, detail="Formato no soportado para análisis heurístico.")

    def _blocking_io_and_cpu_task():
        chunk_response = None
        try:
            chunk_response = minio_client.client.get_object(bucket_name, object_name, offset=0, length=102400)
            sample_bytes = chunk_response.read()
        finally:
            if chunk_response:
                chunk_response.close()
                chunk_response.release_conn()

        return HeuristicEngine.analyze_sample(sample_bytes, file_extension)

    try:
        analysis_result = await asyncio.to_thread(_blocking_io_and_cpu_task)

        if analysis_result.get("status") == "error":
             raise ValueError(analysis_result.get("message"))

        return analysis_result

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Fallo en X-Ray Engine: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Fallo interno al analizar el archivo.")

class ConfirmarIngestaRequest(BaseModel):
    object_name: str
    parser_code: str
    column_mapping: Optional[Dict[str, int]] = None

@router.post(
    "/cuentas/{cuenta_id}/importar/confirm",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(RateLimiter("ingesta_bancaria", limit_seconds=10))]
)
def confirmar_importacion_bancaria(
    cuenta_id: int,
    req: ConfirmarIngestaRequest,
    request: Request,
    x_entity_id: int = Header(..., alias="X-Entity-ID"),
    db: Session = Depends(get_tenant_db_session),
    current_user: CachedUser = Depends(get_current_user)
):
    from core.tasks.banking_tasks import process_bank_statement_task

    cuenta = db.query(CuentaTesoreria).filter(
        CuentaTesoreria.id == cuenta_id, CuentaTesoreria.entidad_id == x_entity_id
    ).first()

    if not cuenta:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cuenta no encontrada.")
    if cuenta.is_syncing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sincronización en curso.")

    tenant_id = current_user.tenant.schema_name
    task_id = str(uuid.uuid4())

    cuenta.is_syncing = True
    cuenta.last_task_id = task_id
    db.commit()

    process_bank_statement_task.apply_async(
        kwargs={
            "tenant_id": tenant_id,
            "entidad_id": x_entity_id,
            "cuenta_id": cuenta_id,
            "tipo_cuenta": cuenta.tipo_cuenta.value,
            "modelo_origen": "TESORERIA",
            "parser_code": req.parser_code,
            "object_name": req.object_name,
            "column_mapping": req.column_mapping,
            "audit_user_id": str(current_user.id),
            "audit_ip_address": request.client.host if request.client else "127.0.0.1"
        },
        task_id=task_id
    )

    return {"task_id": task_id, "status": "ACCEPTED"}

# ==========================================
# 🛑 BOTÓN DE PÁNICO: CANCELACIÓN DE INGESTA
# ==========================================

@router.delete("/cuentas/importar/cancel/{task_id}", status_code=status.HTTP_200_OK)
def cancel_importacion_bancaria(
    task_id: str,
    x_entity_id: int = Header(..., alias="X-Entity-ID"),
    db: Session = Depends(get_tenant_db_session),
    current_user: CachedUser = Depends(get_current_user)
):
    from core.tasks.celery_config import app as celery_app

    try:
        celery_app.control.revoke(task_id, terminate=True, signal='SIGTERM')
        logger.warning(f"🛑 [REVOKE] Tarea {task_id} abortada activamente por el usuario.")

        # 🌟 FIX: Consultar la tabla de Tesorería, no el esquema legacy
        cuenta_zombie = db.query(CuentaTesoreria).filter(CuentaTesoreria.last_task_id == task_id).first()
        if cuenta_zombie:
            cuenta_zombie.is_syncing = False
            db.commit()
            logger.info(f"🔓 [UNLOCK] Candado relacional liberado preventivamente para cuenta {cuenta_zombie.id}.")

        return {"status": "REVOKED", "message": "Proceso detenido y cuenta liberada con éxito."}
    except Exception as e:
        logger.error(f"Error cancelando tarea {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Fallo de comunicación con el orquestador.")