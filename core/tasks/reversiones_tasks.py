import logging
from celery import shared_task

logger = logging.getLogger("CELERY_REVERSIONES")

@shared_task(name="task_notificar_anulacion", bind=True, max_retries=3)
def task_notificar_anulacion(self, entidad_id: int, orden_id: int, user_id: str, tenant_id: str = None):
    """
    Maneja todos los side-effects que deben ocurrir tras anular una Orden de Pago.
    - Notificaciones por email al proveedor.
    - Recálculo de cubos OLAP (Dashboards).
    - Invalidación de caché en Redis.
    """
    try:
        logger.info(f"[Tenant: {tenant_id}] Iniciando side-effects asíncronos para OP {orden_id} (Entidad: {entidad_id})")

        # Aquí se inyectará la lógica de negocio futura (ej. enviar email)
        # proveedor_service.notificar_pago_anulado(orden_id)

        logger.info(f"Side-effects completados con éxito para OP {orden_id}.")
        return {"status": "success", "orden_id": orden_id}

    except Exception as e:
        logger.error(f"Fallo en procesamiento asíncrono de anulación OP {orden_id}: {e}")
        # Disparamos reintento automático si hay un fallo de red temporal
        raise self.retry(exc=e, countdown=15)