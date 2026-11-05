import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

# 🌟 FIX: Importamos RoleChecker
from core.api.deps import get_current_user, CachedUser, get_db_session, RoleChecker
from core.services.billing.strategy import BillingFactory, PaymentGatewayError
from core.database.models_master import Tenant
from config.config import settings
import stripe

logger = logging.getLogger("BILLING_API")

# 🌟 ARQUITECTURA: Router abierto porque el /webhook necesita ser público
router = APIRouter()

class CheckoutRequest(BaseModel):
    plan_name: str

# 🌟 FIX RBAC: Inyectamos la seguridad directamente en la firma de la ruta
@router.post("/checkout", status_code=status.HTTP_200_OK, dependencies=[Depends(RoleChecker(["admin", "dueño"]))])
def create_checkout_session(
    payload: CheckoutRequest,
    current_user: CachedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """
    Genera un link de pago seguro (HTTP 303) delegando la lógica a la fábrica de pagos.
    """
    # 🌟 FIX TECH-DEBT: Eliminado el 'if' manual de roles. El RoleChecker ya lo hizo.

    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant.id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Inquilino no encontrado.")

    gateway = BillingFactory.get_gateway(tenant.billing_provider or "STRIPE")

    try:
        checkout_url = gateway.create_checkout_session(
            tenant_id=tenant.id,
            plan_name=payload.plan_name,
            email=current_user.email,
            razon_social=tenant.name,
            cuit=tenant.cuit,
            customer_id=tenant.provider_customer_id
        )
        return {"checkout_url": checkout_url}
    except PaymentGatewayError as e:
        raise HTTPException(status_code=400, detail=str(e))


# 🌟 FIX RBAC: Blindamos el portal
@router.post("/portal", status_code=status.HTTP_200_OK, dependencies=[Depends(RoleChecker(["admin", "dueño"]))])
def customer_portal(
    current_user: CachedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """
    Redirige al portal de autogestión de Stripe.
    """
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant.id).first()
    if not tenant or not tenant.provider_customer_id:
        raise HTTPException(status_code=400, detail="No tienes una suscripción activa vinculada a un proveedor.")

    gateway = BillingFactory.get_gateway(tenant.billing_provider)
    try:
        portal_url = gateway.get_customer_portal_url(tenant.provider_customer_id)
        return {"portal_url": portal_url}
    except PaymentGatewayError as e:
        raise HTTPException(status_code=400, detail=str(e))

# =======================================================
# 🌐 WEBHOOK (Queda expuesto a Internet, protegido por firma Symmetrica)
# =======================================================
@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(request: Request):
    """
    Receptor Idempotente de eventos de Stripe.
    NO procesa aquí, despacha a RabbitMQ.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Payload inválido")
    except stripe.error.SignatureVerificationError:
        logger.critical("⚠️ [WEBHOOK] Firma de Stripe inválida. Intento de ataque detectado.")
        raise HTTPException(status_code=400, detail="Firma inválida")

    from core.tasks.billing_tasks import process_stripe_webhook_task

    process_stripe_webhook_task.apply_async(
        kwargs={
            "event_dict": event.to_dict(),
            "object_name": event.get("id")
        },
        queue="billing_queue"
    )

    return {"status": "success", "message": "Webhook recibido y encolado."}