import secrets
import string
import passlib
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, HttpUrl
from typing import List
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from core.api.deps import get_current_user, CachedUser, RoleChecker, get_tenant_db_session
from core.database.models_tenant import ApiKey, WebhookSubscription

router = APIRouter(tags=["B2B Integrations"])
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# --- Schemas ---
class ApiKeyCreate(BaseModel):
    name: str

class WebhookCreate(BaseModel):
    url: HttpUrl
    event_types: List[str]

# --- Endpoints API Keys ---
@router.post("/api-keys", status_code=status.HTTP_201_CREATED)
def create_api_key(
    req: ApiKeyCreate,
    db: Session = Depends(get_tenant_db_session),
    current_user: CachedUser = Depends(RoleChecker(["admin", "propietario"]))
):
    prefix = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
    secret_key = secrets.token_urlsafe(32)

    # 🌟 FIX SEGURIDAD: Hashing con Argon2
    hashed_key = pwd_context.hash(secret_key)

    new_key = ApiKey(
        entidad_id=current_user.tenant.id,
        name=req.name,
        prefix=prefix,
        hashed_key=hashed_key
    )
    db.add(new_key)
    db.commit()

    return {
        "message": "Guarde este token de forma segura, no se volverá a mostrar.",
        "api_key": f"{prefix}.{secret_key}",
        "name": new_key.name
    }

@router.get("/api-keys")
def list_api_keys(
    db: Session = Depends(get_tenant_db_session),
    current_user: CachedUser = Depends(RoleChecker(["admin", "propietario"]))
):
    """Lista las API Keys activas (solo muestra el prefijo)."""
    keys = db.query(ApiKey).filter(ApiKey.entidad_id == current_user.tenant.id).all()
    return [{"id": k.id, "name": k.name, "prefix": k.prefix, "is_active": k.is_active, "last_used": k.last_used_at} for k in keys]

# --- Endpoints Webhooks ---
@router.post("/webhooks", status_code=status.HTTP_201_CREATED)
def subscribe_webhook(
    req: WebhookCreate,
    db: Session = Depends(get_tenant_db_session),
    current_user: CachedUser = Depends(RoleChecker(["admin", "propietario"]))
):
    """Registra una URL para recibir eventos asíncronos."""
    webhook_secret = secrets.token_urlsafe(32) # Secreto para firmar el HMAC

    sub = WebhookSubscription(
        entidad_id=current_user.tenant.id,
        url=str(req.url),
        event_types=req.event_types,
        secret=webhook_secret
    )
    db.add(sub)
    db.commit()

    return {
        "message": "Suscripción creada.",
        "webhook_id": sub.id,
        "webhook_secret": webhook_secret # El ERP del cliente lo necesita para verificar firmas
    }