import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.api.deps import get_tenant_db_session, get_current_user, CachedUser
from core.api.permissions import RoleChecker
from core.database.models_tenant import ColaMensajesMuertos
from core.tasks.celery_config import app as celery_app

logger = logging.getLogger("DLQ_ADMIN")
router = APIRouter(tags=["Administración DLQ (Mensajes Muertos)"])

class ReplayRequest(BaseModel):
    dlq_ids: List[int]

@router.post("/replay", status_code=status.HTTP_202_ACCEPTED)
def replay_dead_letters(
    req: ReplayRequest,
    db: Session = Depends(get_tenant_db_session),
    current_user: CachedUser = Depends(RoleChecker(["admin", "propietario"]))
):
    """
    🌟 FIX RIESGO 8: Resurrección de Tareas (Replay).
    Toma mensajes muertos de la cola de base de datos, los marca como resueltos
    y los vuelve a inyectar en el broker AMQP (RabbitMQ) para su re-procesamiento.
    """
    tenant_id = current_user.tenant.schema_name

    muertos = db.query(ColaMensajesMuertos).filter(
        ColaMensajesMuertos.id.in_(req.dlq_ids),
        ColaMensajesMuertos.resuelto == False
    ).all()

    if not muertos:
        raise HTTPException(status_code=404, detail="No se encontraron mensajes pendientes con los IDs provistos.")

    enviados = 0
    for msg in muertos:
        try:
            # Reinyectamos en la tarea de AFIP (que es la que mapea estos campos en tu modelo)
            celery_app.send_task(
                'core.tasks.afip_tasks.sync_arca_comprobantes',
                args=[tenant_id, msg.entidad_id, msg.punto_venta, msg.tipo_cbte_afip],
                queue='afip_queue'
            )
            # Marcamos como resuelto para no re-enviarlo por accidente en el futuro
            msg.resuelto = True
            msg.resolved_by_id = current_user.email
            enviados += 1
        except Exception as e:
            logger.error(f"Fallo al reinyectar DLQ ID {msg.id}: {e}")

    db.commit()

    return {
        "message": f"Se re-encolaron {enviados} tareas fallidas en RabbitMQ.",
        "failed_replays": len(muertos) - enviados
    }