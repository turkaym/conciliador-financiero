import uuid
import json
import asyncio
import logging
from fastapi import APIRouter, Depends, Header, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from celery.result import AsyncResult

from core.api.deps import get_current_user, CachedUser, EntityRoleChecker
from core.tasks.ai_tasks import process_agent_message_task

logger = logging.getLogger("API_AI")
router = APIRouter(prefix="/ai", tags=["Copiloto Financiero"])

class ChatMessageRequest(BaseModel):
    message: str
    # Si es None, es una conversación nueva. Si trae UUID, continúa la memoria.
    thread_id: str | None = None

# Instanciamos el escudo de seguridad perimetral
verificador_autoridad = EntityRoleChecker(["dueño", "admin", "superadmin", "operador", "analista"])

@router.post("/chat", status_code=status.HTTP_202_ACCEPTED)
def send_message_to_copilot(
    payload: ChatMessageRequest,
    x_entity_id: int = Header(..., alias="X-Entity-ID"),
    current_user: CachedUser = Depends(verificador_autoridad)
):
    """
    Ingesta un mensaje del usuario hacia el Copiloto de IA.
    Devuelve un task_id para que el Frontend se suscriba al túnel SSE.
    """
    # 1. Generación o mantenimiento del Hilo de Conversación
    thread_id = payload.thread_id if payload.thread_id else str(uuid.uuid4())

    # 2. Extracción de Identidad Segura
    tenant_schema = current_user.tenant.schema_name
    user_id = str(current_user.id)

    # 3. Delegación Asíncrona al AI-Worker
    task = process_agent_message_task.delay(
        tenant_schema=tenant_schema,
        entidad_id=x_entity_id,
        user_id=user_id,
        thread_id=thread_id,
        user_message=payload.message
    )

    logger.info(f"🧠 [AI-ROUTER] Mensaje delegado a Celery. Task: {task.id} | Thread: {thread_id}")

    return {
        "task_id": task.id,
        "thread_id": thread_id,
        "status": "Procesando en AI-Worker..."
    }

@router.get("/stream/{task_id}")
async def stream_ai_response(
    task_id: str,
    x_entity_id: int = Header(..., alias="X-Entity-ID"),
    current_user: CachedUser = Depends(verificador_autoridad)
):
    """
    Túnel Server-Sent Events (SSE) para el Frontend.
    Observa la tarea de Celery y empuja estados intermedios (Heartbeats) y la respuesta final.
    """
    async def event_generator():
        task = AsyncResult(task_id)
        last_state_str = None
        max_retries = 180  # 180 ciclos de 0.5s = 90 segundos de timeout máximo

        for _ in range(max_retries):
            # 1. Fallo Crítico
            if task.state == 'FAILURE':
                error_info = str(task.info) if task.info else "Fallo sistémico en el Agente IA."
                payload = json.dumps({"status": "ERROR", "message": error_info})
                yield f"data: {payload}\n\n"
                break

            # 2. Éxito Transaccional
            elif task.state == 'SUCCESS':
                result_data = task.result if isinstance(task.result, dict) else {"respuesta": str(task.result)}
                payload = json.dumps({"status": "SUCCESS", "data": result_data})
                yield f"data: {payload}\n\n"
                break

            # 3. Estados Intermedios (PROGRESS, PENDING, o Custom)
            else:
                # Recuperamos los metadatos inyectados por Celery (self.update_state)
                current_info = task.info if isinstance(task.info, dict) else {}
                state_data = {
                    "status": task.state,
                    "message": current_info.get("message", "Conectando con el Copiloto...")
                }

                state_str = json.dumps(state_data)

                # Emitimos el evento solo si el estado cambió, para no saturar el canal del cliente
                if state_str != last_state_str:
                    yield f"data: {state_str}\n\n"
                    last_state_str = state_str
                else:
                    # 🌟 FIX ARQUITECTÓNICO: Heartbeat
                    # Enviamos un comentario SSE vacío para evitar el Timeout (504 Gateway Timeout)
                    # de balanceadores de carga como Nginx o Cloudflare.
                    yield ": heartbeat\n\n"

            # Descansamos el Event Loop de FastAPI para atender otras peticiones
            await asyncio.sleep(0.5)

        else:
            # Si el bucle termina sin break, excedimos los 90 segundos.
            timeout_payload = json.dumps({
                "status": "TIMEOUT",
                "message": "El agente tardó demasiado en responder. La tarea sigue en segundo plano."
            })
            yield f"data: {timeout_payload}\n\n"

    # Retornamos un StreamingResponse estructurado bajo el protocolo estándar de text/event-stream
    return StreamingResponse(event_generator(), media_type="text/event-stream")