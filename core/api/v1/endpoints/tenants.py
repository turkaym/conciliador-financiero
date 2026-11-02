from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Header
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import logging
from pydantic import BaseModel

from core.database.models_master import Tenant, User
from core.services.tenant_manager import TenantManager
from core.security.encryption import SecretManager
from core.schemas.tenant import TenantResponse, TenantCreate
from core.api.deps import get_current_user, CachedUser, get_db_session, RoleChecker, invalidate_user_cache

logger = logging.getLogger(__name__)

# Router base para asegurar autenticación
router = APIRouter(dependencies=[Depends(get_current_user)])

# Definición de políticas estandarizadas
require_superadmin = RoleChecker(["superadmin"])
require_admin_god = RoleChecker(["admin", "superadmin"])
require_dueño_god = RoleChecker(["admin", "superadmin", "dueño"])

class ApprovalRequest(BaseModel):
    tenant_id: int
    user_id: int

class FeatureUpdateRequest(BaseModel):
    features: Dict[str, Any]

@router.get("/", response_model=List[TenantResponse])
def get_tenants(
    current_user: CachedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Lista los inquilinos aplicando Aislamiento de Datos (RBAC)."""
    if current_user.role in ["admin", "superadmin"]:
        return TenantManager.list_tenants(db)

    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant.id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Inquilino no encontrado.")
    return [tenant]

@router.post("/", response_model=TenantResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin_god)])
def create_tenant(
    tenant_in: TenantCreate,
    db: Session = Depends(get_db_session)
):
    """Aprovisiona un nuevo inquilino orgánicamente."""
    try:
        return TenantManager.create_tenant(
            db=db,
            name=tenant_in.name,
            cuit=tenant_in.cuit
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error al crear tenant: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Fallo interno en el aprovisionamiento.")

@router.post("/{tenant_id}/certificados", status_code=status.HTTP_200_OK, dependencies=[Depends(require_dueño_god)])
def upload_tenant_certificates(
    tenant_id: int,
    certificado: UploadFile = File(..., description="Archivo .crt o .pem"),
    clave_privada: UploadFile = File(..., description="Archivo .key"),
    current_user: CachedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Recibe credenciales de AFIP, encripta clave privada vía KMS y sella en Master DB."""
    if current_user.role not in ["admin", "superadmin"] and current_user.tenant.id != tenant_id:
        raise HTTPException(status_code=403, detail="Aislamiento cruzado. No autorizado para este inquilino.")

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado en Master DB.")

    try:
        cert_content = certificado.file.read().decode("utf-8")
        key_content = clave_privada.file.read().decode("utf-8")

        kms = SecretManager()
        encrypted_key = kms.encrypt_string(key_content)

        tenant.afip_certificate = cert_content
        tenant.afip_private_key_encrypted = encrypted_key

        db.commit()
        logger.info(f"🔐 Credenciales selladas por API para tenant {tenant.schema_name} por usuario {current_user.email}")

        return {"status": "success", "message": "Credenciales KMS selladas exitosamente."}

    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="El formato de los archivos debe ser texto plano (UTF-8).")
    except Exception as e:
        db.rollback()
        logger.error(f"Fallo criptográfico: {e}")
        raise HTTPException(status_code=500, detail="Fallo interno al procesar los certificados.")

@router.post(
    "/approve-tenant",
    status_code=status.HTTP_200_OK,
    summary="Aprobación Zero Trust de nuevos inquilinos",
    dependencies=[Depends(require_superadmin)]
)
async def approve_pending_tenant(
    payload: ApprovalRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key", description="UUID único para la transacción"),
    db: Session = Depends(get_db_session),
    current_admin: CachedUser = Depends(get_current_user)
):
    """Transiciona una cuenta corporativa de PENDING_SUPERADMIN_APPROVAL a ACTIVE."""
    user = db.query(User).filter(User.id == payload.user_id, User.tenant_id == payload.tenant_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="Usuario o Empresa no encontrados en la base maestra.")

    if getattr(user, 'status', 'ACTIVE') == 'ACTIVE' and user.is_active:
        return {"message": "El inquilino ya se encuentra activo.", "status": "ALREADY_ACTIVE"}

    if getattr(user, 'status', 'ACTIVE') != 'PENDING_SUPERADMIN_APPROVAL':
        raise HTTPException(status_code=400, detail=f"El estado actual ({getattr(user, 'status', 'UNKNOWN')}) no permite esta transición.")

    try:
        tenant = db.query(Tenant).filter(Tenant.id == payload.tenant_id).first()
        tenant.is_active = True

        user.status = 'ACTIVE'
        user.is_active = True

        db.commit()
        logger.info(f"🛡️ [GOD MODE] Inquilino {tenant.schema_name} aprobado operativamente por {current_admin.email}")

    except Exception as e:
        db.rollback()
        logger.error(f"Fallo crítico al aprobar inquilino en DB: {e}")
        raise HTTPException(status_code=500, detail="Fallo transaccional al cambiar el estado de la empresa.")

    try:
        from core.tasks.notification_tasks import send_welcome_email_task
        send_welcome_email_task.apply_async(
            kwargs={"email": user.email, "empresa_nombre": tenant.name}
        )
    except Exception as celery_err:
        logger.error(f"⚠️ Inquilino aprobado, pero falló encolado de correo de bienvenida: {celery_err}")

    invalidate_user_cache(user.email)

    return {
        "message": "Empresa aprobada exitosamente. El usuario ya puede iniciar sesión.",
        "status": "APPROVED",
        "schema_name": tenant.schema_name
    }

@router.put(
    "/{tenant_id}/features",
    status_code=status.HTTP_200_OK,
    summary="God Mode: Upselling y Control de Cuotas",
    dependencies=[Depends(require_superadmin)]
)
def update_tenant_features(
    tenant_id: int,
    payload: FeatureUpdateRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key", description="UUID único para la transacción"),
    db: Session = Depends(get_db_session)
):
    """
    Modifica el JSONB de 'features' de un inquilino.
    Protegido contra doble-clic por Idempotency-Key y procesado asíncronamente vía Celery.
    """
    try:
        tenant = TenantManager.upgrade_plan_and_features(db, tenant_id, payload.features)

        return {
            "status": "success",
            "message": "Plan comercial actualizado. La caché de los operadores será purgada en background.",
            "tenant_id": tenant.id,
            "schema_name": tenant.schema_name,
            "features": tenant.features
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error crítico al actualizar features del tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail="Fallo transaccional al impactar el nuevo plan comercial.")