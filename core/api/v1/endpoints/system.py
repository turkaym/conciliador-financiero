import os
import uuid
import json
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from jose import jwt
from fastapi import APIRouter, Depends, Query, Path, Request, status, HTTPException
from fastapi.responses import StreamingResponse
from celery.result import AsyncResult
from pydantic import BaseModel
from typing import List

from config.config import settings
from core.api.deps import get_current_user, CachedUser, RoleChecker, verify_sse_token
from core.storage.minio_client import minio_client
from core.tasks.celery_config import app as celery_app

logger = logging.getLogger("API_SYSTEM")
router = APIRouter(tags=["Sistema & Asincronismo"])

# 🌟 FIX REDES: Endpoint para emitir el Ticket Efímero de conexión SSE
@router.post("/auth/sse-token", status_code=status.HTTP_201_CREATED)
def generate_sse_token(current_user: CachedUser = Depends(get_current_user)):
    """Genera un JWT estricto de 5 minutos, válido únicamente para transmisiones en vivo."""
    expires = datetime.now(timezone.utc) + timedelta(minutes=5)
    payload = {
        "sub": current_user.email,
        "type": "sse",
        "exp": expires.timestamp()
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return {"sse_token": token}

# 🌟 FIX SEGURIDAD: Bloqueamos el endpoint de firmas con el RoleChecker
@router.get("/ingesta/upload-url", status_code=status.HTTP_200_OK, dependencies=[Depends(RoleChecker(["admin", "operator"]))])
def request_upload_url(
    modulo: str = Query(..., description="Ej: 'bancos', 'padrones', 'comprobantes'"),
    extension: str = Query(..., description="Extensión del archivo (.csv, .txt, .xls, .xlsx)"),
    current_user: CachedUser = Depends(get_current_user)
):
    """Genera la Post Policy (Contrato de subida directa a MinIO) para archivos menores a 20MB."""
    ext_lower = extension.lower()

    # 🌟 FIX HARDENING: Mantenemos whitelist de extensiones, pero eliminamos el escudo MIME
    allowed_extensions = ['.csv', '.txt', '.xls', '.xlsx']

    if ext_lower not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Extensión de archivo no permitida por seguridad.")

    tenant_id = current_user.tenant.schema_name
    file_uuid = str(uuid.uuid4())[:8]
    object_name = f"{modulo}/{file_uuid}{ext_lower}"

    # 🌟 FIX DEUDA TÉCNICA: Generamos policy pura sin acoplamiento MIME.
    # Si el archivo es más pesado, el frontend usará automáticamente la ruta Multipart
    form_fields = minio_client.generate_presigned_post_policy(
        tenant_schema=tenant_id,
        object_name=object_name,
        expiry_minutes=15,
        max_mb=20
    )

    minio_host = os.getenv("MINIO_EXTERNAL_URL", "http://localhost:9000")
    bucket_name = tenant_id.replace("_", "-")
    upload_url = f"{minio_host}/{bucket_name}"

    return {
        "upload_url": upload_url,
        "form_fields": form_fields,
        "object_name": object_name
    }

# ===================================================================
# 🌟 CAPA 4: INFRAESTRUCTURA MULTIPART PARA ARCHIVOS MASIVOS (> 20MB)
# ===================================================================

class MultipartUrlRequest(BaseModel):
    modulo: str
    extension: str
    total_parts: int

@router.post("/ingesta/multipart/urls", status_code=status.HTTP_200_OK, dependencies=[Depends(RoleChecker(["admin", "operator"]))])
def request_multipart_urls(
    payload: MultipartUrlRequest,
    current_user: CachedUser = Depends(get_current_user)
):
    """
    Genera un 'Upload Plan' para archivos gigantes.
    Devuelve N URLs pre-firmadas (PUT) para que el Frontend suba fragmentos en paralelo.
    """
    if payload.extension.lower() not in ['.csv', '.txt', '.xls', '.xlsx']:
        raise HTTPException(status_code=400, detail="Extensión de archivo no permitida.")

    if not (1 <= payload.total_parts <= 100):
        raise HTTPException(status_code=400, detail="El archivo fue dividido en una cantidad inválida de partes (Máx 100).")

    tenant_id = current_user.tenant.schema_name
    file_uuid = str(uuid.uuid4())[:8]

    # El nombre final que tendrá el archivo ensamblado
    final_object_name = f"{payload.modulo}/{file_uuid}{payload.extension.lower()}"

    # Generamos una lista de URLs temporales para cada parte
    minio_host = os.getenv("MINIO_EXTERNAL_URL", "http://localhost:9000")
    bucket_name = tenant_id.replace("_", "-")

    parts = []
    parts = []
    for part_number in range(1, payload.total_parts + 1):
        # Cada parte se sube a un subdirectorio temporal
        part_object_name = f"{payload.modulo}/_tmp/{file_uuid}/part_{part_number}"

        # 🌟 FIX: El cliente efímero ahora nos devuelve la URL ya firmada con el Host correcto.
        external_url = minio_client.generate_presigned_put_url(tenant_id, part_object_name, expiry_minutes=60)

        parts.append({
            "part_number": part_number,
            "object_name": part_object_name,
            "upload_url": external_url
        })

    return {
        "final_object_name": final_object_name,
        "parts": parts
    }

@router.get("/status/stream/{task_id}")
async def stream_task_status(
    request: Request,
    task_id: str = Path(...),
    email: str = Depends(verify_sse_token),
):
    """Canal global de Server-Sent Events con lectura directa desde Redis."""
    last_event_id = request.headers.get("Last-Event-ID")

    async def event_generator():
        event_id_counter = int(last_event_id) if last_event_id and last_event_id.isdigit() else 0
        loops = 0

        while True:
            fresh_task = AsyncResult(task_id, app=celery_app)
            state = fresh_task.state

            response = {"task_id": task_id, "status": state}
            event_id_counter += 1

            # 🌟 FIX: Extraemos el progreso de forma segura si el worker ya lo publicó
            if state in ['PROCESSING', 'PENDING', 'STARTED']:
                if isinstance(fresh_task.info, dict):
                    response["progress"] = fresh_task.info.get("progress", 0)
                    response["message"] = fresh_task.info.get("message", "Procesando...")
                else:
                    response["progress"] = 0
                    response["message"] = "Iniciando worker..."

            if state == 'SUCCESS':
                response["result"] = fresh_task.result
                response["progress"] = 100
                response["message"] = "Completado"
                yield f"id: {event_id_counter}\ndata: {json.dumps(response)}\n\n"
                break

            elif state in ['FAILURE', 'REVOKED']:
                raw_error = str(fresh_task.result)
                if "[BUSINESS_LOGIC]" in raw_error:
                    error_msg = raw_error.split("[BUSINESS_LOGIC]")[-1].strip()
                elif "[PARSING_ERROR]" in raw_error:
                    error_msg = raw_error.split("[PARSING_ERROR]")[-1].strip()
                else:
                    error_msg = raw_error.split("('")[-1].split("')")[0] if "('" in raw_error else raw_error

                error_msg = error_msg.replace("\\", "").strip("'\"")
                response["error"] = error_msg
                response["status"] = "FAILURE"
                yield f"id: {event_id_counter}\ndata: {json.dumps(response)}\n\n"
                break

            yield f"id: {event_id_counter}\ndata: {json.dumps(response)}\n\n"

            loops += 1
            if loops >= 20:  # Emitimos latido cada ~3 segundos (20 * 0.15s)
                yield f": heartbeat\n\n"
                loops = 0

            # 🌟 EL SECRETO: Polling ultra rápido (150 milisegundos)
            # Esto atrapa a Celery mientras está trabajando, sin colapsar Redis.
            await asyncio.sleep(0.15)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@router.delete("/status/cancel/{task_id}", status_code=status.HTTP_200_OK)
async def cancel_running_task(
    task_id: str = Path(..., description="El UUID de la tarea de Celery a cancelar")
):
    """
    Botón de pánico: Mata de forma forzosa un proceso de Celery en ejecución.
    """
    try:
        # Revisa el estado actual antes de matar
        task_result = celery_app.AsyncResult(task_id)
        estado_actual = task_result.state

        if estado_actual in ['SUCCESS', 'FAILURE', 'REVOKED']:
            return {"message": f"La tarea {task_id} ya finalizó con estado {estado_actual}. No se requiere cancelación."}

        # 🌟 FIX: Mandamos la señal de terminación al worker.
        # signal='SIGKILL' asegura que el proceso muera inmediatamente y libere RAM.
        celery_app.control.revoke(task_id, terminate=True, signal='SIGKILL')

        logger.warning(f"🛑 [REVOKE] Tarea {task_id} abortada por el usuario.")

        return {
            "status": "REVOKED",
            "message": "Señal de cancelación enviada con éxito. El worker detendrá el procesamiento."
        }

    except Exception as e:
        logger.error(f"Error al intentar cancelar la tarea {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Fallo al comunicarse con el orquestador para cancelar la tarea."
        )