import logging
import json
from datetime import datetime, timezone
import redis

from core.tasks.celery_config import app
from core.tasks.base_task import DLQTask
from core.utils.redis_locks import redis_lock
from core.database.session import SessionLocal
from core.database.models_master import Tenant, User
from config.config import settings
from core.api.deps import invalidate_user_cache

logger = logging.getLogger("BILLING_WORKER")
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

@app.task(name="core.tasks.billing_tasks.process_stripe_webhook_task", base=DLQTask, bind=True, max_retries=5)
@redis_lock(key_prefix="webhook_stripe", timeout=30)
def process_stripe_webhook_task(self, event_dict: dict, object_name: str = None):
    """
    Motor Asíncrono de Procesamiento de Webhooks B2B.
    El parámetro `object_name` se inyecta para que el decorador @redis_lock lo use como llave.
    """
    event_id = event_dict.get("id")
    event_type = event_dict.get("type")
    data_object = event_dict.get("data", {}).get("object", {})

    # =======================================================
    # 🛡️ 1. IDEMPOTENCIA HISTÓRICA (Anti-Rebote de Stripe)
    # =======================================================
    idempotency_key = f"webhook:processed:{event_id}"
    if redis_client.exists(idempotency_key):
        logger.info(f"♻️ [WEBHOOK] Evento {event_id} ya fue procesado con éxito. Ignorando silenciosamente.")
        return {"status": "ignored", "reason": "already_processed"}

    logger.info(f"💳 [WEBHOOK] Iniciando procesamiento de evento: {event_type} | ID: {event_id}")

    db = SessionLocal()
    tenant = None

    try:
        # =======================================================
        # 🏢 2. RESOLUCIÓN DE IDENTIDAD (Mapping)
        # =======================================================
        if event_type == "checkout.session.completed":
            # En el primer pago, el tenant_id viene en los metadatos que inyectamos en el Checkout
            tenant_id_str = data_object.get("metadata", {}).get("tenant_id")
            if not tenant_id_str:
                logger.warning(f"⚠️ [WEBHOOK] Evento {event_id} carece de tenant_id en metadata.")
                return
            tenant = db.query(Tenant).filter(Tenant.id == int(tenant_id_str)).first()

        elif event_type in ["customer.subscription.updated", "customer.subscription.deleted"]:
            # En actualizaciones futuras, buscamos por el ID del cliente de Stripe
            customer_id = data_object.get("customer")
            if not customer_id:
                return
            tenant = db.query(Tenant).filter(Tenant.provider_customer_id == customer_id).first()

        if not tenant:
            logger.error(f"❌ [WEBHOOK] No se encontró el Tenant para el evento {event_id}. Abortando.")
            return

        # =======================================================
        # ⚙️ 3. MÁQUINA DE ESTADOS COMERCIALES (Business Logic)
        # =======================================================
        if event_type == "checkout.session.completed":
            tenant.provider_customer_id = data_object.get("customer")
            tenant.billing_provider = "STRIPE"
            tenant.subscription_status = "active"
            logger.info(f"✅ [BILLING] Tenant {tenant.schema_name} suscrito exitosamente. Paywall levantado.")

        elif event_type == "customer.subscription.updated":
            # Stripe envía estados como: active, past_due, unpaid, canceled
            new_status = data_object.get("status")
            tenant.subscription_status = new_status

            # Actualizar fecha de corte (Unix Timestamp a DateTime UTC)
            period_end = data_object.get("current_period_end")
            if period_end:
                tenant.current_period_end = datetime.fromtimestamp(period_end, tz=timezone.utc)

            logger.info(f"🔄 [BILLING] Tenant {tenant.schema_name} actualizó estado a: {new_status}")

        elif event_type == "customer.subscription.deleted":
            tenant.subscription_status = "canceled"
            logger.warning(f"🛑 [BILLING] Tenant {tenant.schema_name} canceló suscripción. Activando Paywall.")

        # Guardar en Base Maestra
        db.commit()

        # =======================================================
        # 🚀 4. INVALIDACIÓN DE CACHÉ (Evaporación O(1))
        # =======================================================
        users = db.query(User).filter(User.tenant_id == tenant.id).all()
        for user in users:
            try:
                invalidate_user_cache(user.email)
            except Exception as cache_err:
                logger.warning(f"Fallo al invalidar caché para {user.email}: {cache_err}")

        # =======================================================
        # 🔒 5. SELLAR IDEMPOTENCIA
        # =======================================================
        # Guardamos la marca de éxito por 48 horas. Si Stripe reintenta el mismo ID, chocará con la validación inicial.
        redis_client.setex(idempotency_key, 172800, "PROCESSED")

        return {"status": "success", "tenant": tenant.schema_name, "event": event_type}

    except Exception as e:
        db.rollback()
        logger.error(f"❌ [WEBHOOK] Fallo crítico procesando evento {event_id}: {e}", exc_info=True)
        # Al lanzar el retry, el candado de 30s se libera y Celery reintentará en el futuro
        raise self.retry(exc=e, countdown=15 * (2 ** self.request.retries))

    finally:
        db.close()