import logging
import stripe
from abc import ABC, abstractmethod
from typing import Optional
from config.config import settings

logger = logging.getLogger("BILLING_STRATEGY")

class PaymentGatewayError(Exception):
    pass

class PaymentGateway(ABC):
    """💎 PATRÓN STRATEGY: Interfaz Base para adaptadores de facturación."""

    @abstractmethod
    def create_checkout_session(self, tenant_id: int, plan_name: str, email: str, razon_social: str, cuit: str, customer_id: Optional[str] = None) -> str:
        pass

    @abstractmethod
    def get_customer_portal_url(self, customer_id: str) -> str:
        pass


class StripeAdapter(PaymentGateway):
    def __init__(self):
        if not settings.STRIPE_SECRET_KEY:
            logger.error("🛑 STRIPE_SECRET_KEY no está configurada.")
        stripe.api_key = settings.STRIPE_SECRET_KEY

        # Mapeo dinámico de planes basado en variables de entorno
        self.price_map = {
            "starter": settings.STRIPE_PRICE_STARTER,
            "business": settings.STRIPE_PRICE_BUSINESS,
            "enterprise": settings.STRIPE_PRICE_ENTERPRISE
        }

    def create_checkout_session(self, tenant_id: int, plan_name: str, email: str, razon_social: str, cuit: str, customer_id: Optional[str] = None) -> str:
        price_id = self.price_map.get(plan_name.lower())
        if not price_id:
            raise PaymentGatewayError(f"Plan '{plan_name}' no tiene un Price ID configurado en Stripe.")

        try:
            # Payload base para la sesión
            session_kwargs = {
                "payment_method_types": ["card"],
                "line_items": [{"price": price_id, "quantity": 1}],
                "mode": "subscription",
                "success_url": f"{settings.FRONTEND_URL}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
                "cancel_url": f"{settings.FRONTEND_URL}/billing/cancel",
                # 🌟 Habilitamos recolección de CUIT automática para factura B2B
                "tax_id_collection": {"enabled": True},
                # 🌟 Metadata vital: Así el Webhook sabrá a qué Tenant de la DB impactar el pago
                "subscription_data": {"metadata": {"tenant_id": str(tenant_id)}},
                "metadata": {"tenant_id": str(tenant_id)}
            }

            # 🛡️ Anti-Duplicación: Si ya lo tenemos registrado, reusamos el perfil.
            if customer_id:
                session_kwargs["customer"] = customer_id
                session_kwargs["customer_update"] = {"name": "auto"} # Actualiza Razón Social si cambió
            else:
                # Cliente nuevo: Stripe lo creará y pedirá los datos
                session_kwargs["customer_email"] = email

            session = stripe.checkout.Session.create(**session_kwargs)
            logger.info(f"💳 [STRIPE] Checkout generado para Tenant {tenant_id}. URL: {session.url}")
            return session.url

        except stripe.StripeError as e:
            logger.error(f"❌ [STRIPE] Error generando Checkout: {e.user_message}")
            raise PaymentGatewayError(f"Error en pasarela de pagos: {e.user_message}")


class BillingFactory:
    @staticmethod
    def get_gateway(provider_name: str = "STRIPE") -> PaymentGateway:
        if provider_name.upper() == "STRIPE":
            return StripeAdapter()
        # Aquí entrará MercadoPagoAdapter en el futuro
        raise ValueError(f"Proveedor desconocido: {provider_name}")