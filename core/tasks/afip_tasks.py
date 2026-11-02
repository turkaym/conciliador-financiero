import logging
import random
import redis
from core.tasks.celery_config import app
from core.tasks.base_task import DLQTask
from core.database.session import tenant_session_ctx
from core.database.models.entidades import RazonSocialPropia
from core.afip.ingest import IngestManager
from core.afip.wsfe import AfipWSFEClient
from core.afip.auth import AfipAuthManager
from config.config import settings
from core.utils.errors import BusinessException, BusinessErrorCode

logger = logging.getLogger("TASKS_AFIP")

# 🌟 FIX: Forzamos decodificación de strings para evitar que Pydantic colapse con bytes
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

@app.task(name="core.tasks.afip_tasks.sync_arca_comprobantes", base=DLQTask, bind=True, max_retries=8)
def sync_arca_comprobantes(self, tenant_id: str, entidad_id: int, punto_venta: int, tipo_cbte: int):
    logger.info(f"🌀 [AFIP] Sincronizando: {tenant_id} | Entidad: {entidad_id} | PV: {punto_venta}")

    with tenant_session_ctx(tenant_id) as db:
        entidad = db.query(RazonSocialPropia).filter(RazonSocialPropia.id == entidad_id).first()
        if not entidad:
            raise BusinessException(BusinessErrorCode.SECURITY_VIOLATION, "Entidad activa no encontrada.")

        cuit = entidad.cuit
        crt_content = entidad.afip_certificate
        encrypted_key = entidad.afip_private_key_encrypted

    if not crt_content or not encrypted_key:
        raise BusinessException(BusinessErrorCode.AFIP_AUTH_FAILED, f"Faltan certificados en Bóveda Fiscal para el CUIT {cuit}")

    try:
        # 🌟 FIX RIESGO DE PRODUCCIÓN: Normalización estricta del string de entorno
        raw_env = getattr(settings, 'PROMETEO_ENV', 'homo')
        env_mode = "prod" if raw_env in ["produccion", "prod", "production"] else "homo"

        with AfipAuthManager(redis_client, crt_content, encrypted_key, env_mode) as auth:
            with AfipWSFEClient(auth, cuit) as client:
                manager = IngestManager(client, redis_client, tenant_id)
                resultado = manager.sync_recent_invoices(entidad_id, punto_venta, tipo_cbte, 500)

        if resultado.get("has_more") and not resultado.get("rate_limited"):
            self.apply_async(
                kwargs={"tenant_id": tenant_id, "entidad_id": entidad_id, "punto_venta": punto_venta, "tipo_cbte": tipo_cbte},
                countdown=5
            )
        else:
            # 🌟 FIX TELEMETRÍA (FASE E): Lote finalizado o al día. Sellamos el Timestamp.
            from datetime import datetime, timezone
            with tenant_session_ctx(tenant_id) as sync_db:
                entidad_sync = sync_db.query(RazonSocialPropia).filter(RazonSocialPropia.id == entidad_id).with_for_update().first()
                if entidad_sync:
                    entidad_sync.afip_last_sync_at = datetime.now(timezone.utc)
                    sync_db.add(entidad_sync)
                    sync_db.commit()

        return {"status": "success", "new_records": resultado.get("new_records", 0), "tenant": tenant_id}

    except BusinessException as be:
        # 🌟 FAIL-FAST: No reintentamos errores de negocio (Ej: certificados vencidos).
        # Se rechazan inmediatamente hacia la Dead Letter Queue (DLQ).
        logger.error(f"🚫 [AFIP] Rechazo de negocio para {tenant_id}: {be}")
        raise be

    except Exception as exc:
        # 🌟 ALGORITMO: Backoff Exponencial Progresivo + Full Jitter
        # Intentos (max_retries=8): 1m, 2m, 4m, 8m, 16m, 32m, 60m, 60m, 60m. Total = ~4 horas de tolerancia.
        logger.warning(f"⚠️ [AFIP] Caída de ARCA o red para {tenant_id}. Intentos: {self.request.retries}/8. Detalle: {exc}")

        base_backoff = 60 * (2 ** self.request.retries)
        retraso_maximo = 3600  # Tope de 1 hora por reintento
        tiempo_base = min(retraso_maximo, base_backoff)

        # Inyectamos hasta un 15% de ruido aleatorio para evitar estampidas (Thundering Herd)
        jitter = random.uniform(0, tiempo_base * 0.15)
        retraso_segundos = int(tiempo_base + jitter)

        raise self.retry(exc=exc, countdown=retraso_segundos)