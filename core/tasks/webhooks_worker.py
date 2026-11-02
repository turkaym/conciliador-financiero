import hmac
import hashlib
import json
import logging
import uuid
import requests
import random
from datetime import datetime, timezone
from requests.exceptions import RequestException

# Usamos la instancia unificada de Celery
from core.tasks.celery_config import app
from core.database.session import tenant_session_ctx
from core.database.models_tenant import WebhookSubscription, WebhookDeliveryLog

logger = logging.getLogger("WEBHOOKS_DISPATCHER")
logger.setLevel(logging.INFO)

@app.task(name="core.tasks.webhooks_worker.dispatch_webhook", bind=True, max_retries=5)
def dispatch_webhook(self, tenant_id: str, subscription_id: int, event_type: str, payload_data: dict):
    """
    Despacha un evento al ERP del cliente con Firma Criptográfica (HMAC),
    Timeout estricto de 3.0s y registro legal irrefutable.
    """
    logger.info(f"🚀 [WEBHOOK] Iniciando despacho. Evento: {event_type} | Subs: {subscription_id}")

    event_id = str(uuid.uuid4()) # Casuística 10: Idempotencia para el cliente

    with tenant_session_ctx(tenant_id) as db:
        subs = db.query(WebhookSubscription).filter(
            WebhookSubscription.id == subscription_id,
            WebhookSubscription.is_active == True
        ).first()

        if not subs:
            logger.warning(f"⚠️ [WEBHOOK] Suscripción {subscription_id} inactiva o eliminada. Abortando.")
            return {"status": "aborted", "reason": "subscription_inactive"}

        # 1. Preparar Payload y Firma Criptográfica (Casuística 9)
        payload_str = json.dumps(payload_data, separators=(',', ':'))

        signature = hmac.new(
            key=subs.secret.encode('utf-8'),
            msg=payload_str.encode('utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Conciliador-B2B-Engine/1.0",
            "X-Event-ID": event_id,
            "X-Event-Type": event_type,
            "X-Conciliador-Signature": f"sha256={signature}"
        }

        # 2. Registrar el intento en la Bitácora (Delivery Log)
        log_entry = WebhookDeliveryLog(
            subscription_id=subs.id,
            event_id=event_id,
            event_type=event_type,
            payload=payload_data,
            attempt_number=self.request.retries + 1
        )
        db.add(log_entry)
        db.flush()

        # 3. Disparo de Red (Casuística 8: Timeout Asesino)
        try:
            # 🌟 FIX: Timeout estricto de 3 segundos. Si el ERP está caído, no congelamos el worker.
            response = requests.post(subs.url, data=payload_str, headers=headers, timeout=3.0)

            log_entry.response_status = response.status_code
            log_entry.response_body = response.text[:1000] # Guardamos los primeros 1000 chars por seguridad

            if 200 <= response.status_code < 300:
                log_entry.is_successful = True
                db.commit()
                logger.info(f"✅ [WEBHOOK] Entregado con éxito a {subs.url} (Status: {response.status_code})")
                return {"status": "delivered", "event_id": event_id}
            else:
                # El cliente respondió, pero con un error (Ej: 500 Internal Server Error)
                db.commit()
                logger.warning(f"⚠️ [WEBHOOK] El ERP del cliente rechazó el payload (Status: {response.status_code})")
                raise ValueError(f"HTTP {response.status_code}")

        except RequestException as net_err:
            log_entry.response_status = 0
            log_entry.response_body = str(net_err)
            db.commit()
            logger.error(f"❌ [WEBHOOK] Fallo de red contactando a {subs.url}: {net_err}")

            # 🌟 FIX RIESGO 7: Jitter (Aleatoriedad anti-estampida)
            base_delay = 10 * (2 ** self.request.retries)
            jitter = random.uniform(0, base_delay * 0.2) # Agrega hasta un 20% de dispersión temporal
            raise self.retry(exc=net_err, countdown=base_delay + jitter)

        except ValueError as val_err:
            base_delay = 10 * (2 ** self.request.retries)
            jitter = random.uniform(0, base_delay * 0.2)
            raise self.retry(exc=val_err, countdown=base_delay + jitter)