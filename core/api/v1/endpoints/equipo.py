from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, EmailStr
import logging
import redis
import os

from core.api.deps import get_db_session, get_current_user, CachedUser, invalidate_user_cache, RoleChecker
from core.database.models_master import User
from config.config import settings

logger = logging.getLogger("API_EQUIPO")

# 🌟 FIX RBAC: Permiso base para listar el equipo (Todos los roles operativos)
router = APIRouter(dependencies=[Depends(RoleChecker(["admin", "owner", "dueño", "propietario", "editor", "operador"]))])

# ==========================================
# SCHEMAS (Pydantic v2)
# ==========================================
class InvitacionResponse(BaseModel):
    message: str
    magic_link_token: str
    expires_in_hours: int

class MiembroEquipoCreate(BaseModel):
    email: EmailStr
    rol: str
    entidad_id: int

class MiembroEquipoUpdate(BaseModel):
    rol: Optional[str] = None
    is_active: Optional[bool] = None

class MiembroEquipoResponse(BaseModel):
    id: int
    user_id: str
    rol: str
    is_active: bool

    model_config = {"from_attributes": True}

# 🌟 FIX TECH-DEBT: Eliminada la función manual `verificar_permiso_dueno`.
# La validación ahora es 100% interceptada en memoria RAM por el RoleChecker de FastAPI.

# ==========================================
# RUTAS DE GESTIÓN DE EQUIPO (ZERO TRUST)
# ==========================================

@router.get("/", response_model=List[MiembroEquipoResponse])
def listar_equipo(
    db_master: Session = Depends(get_db_session),
    current_user: CachedUser = Depends(get_current_user)
):
    """Lista todos los usuarios usando el tenant_id seguro del token."""
    tenant_id_str = str(current_user.tenant.id)
    usuarios = db_master.query(User).filter(User.tenant_id == tenant_id_str).all()

    return [
        MiembroEquipoResponse(
            id=u.id, user_id=u.email, rol=u.role.upper(), is_active=u.is_active
        ) for u in usuarios
    ]

# 🌟 MICRO-SEGMENTACIÓN: Solo dueños pueden invitar
@router.post("/", response_model=InvitacionResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RoleChecker(["admin", "owner", "dueño", "propietario"]))])
def invitar_miembro(
    miembro_in: MiembroEquipoCreate,
    db_master: Session = Depends(get_db_session),
    current_user: CachedUser = Depends(get_current_user)
):
    tenant_id_str = str(current_user.tenant.id)

    # 💳 FASE 9: FILTRO ANTI-GORRÓN (Validación de Cuota O(1))
    features = current_user.tenant.features
    if isinstance(features, dict) and 'max_operadores' in features:
        max_operadores = features.get('max_operadores')
        if max_operadores is not None:
            operadores_actuales = db_master.query(User).filter(
                User.tenant_id == tenant_id_str,
                User.is_active == True,
                func.lower(User.role).in_(['operador', 'operator'])
            ).count()

            if operadores_actuales >= max_operadores:
                logger.warning(f"🛑 [PAYWALL] Tenant {current_user.tenant.schema_name} alcanzó límite de {max_operadores} operadores.")
                raise HTTPException(
                    status_code=403,
                    detail=f"Límite de plan alcanzado. Su plan permite un máximo de {max_operadores} operadores. Por favor, mejore su suscripción para invitar a más equipo."
                )

    try:
        r_sync = redis.from_url(settings.REDIS_URL, decode_responses=True)
        lock_key = f"idempotency:invite:{tenant_id_str}:{miembro_in.entidad_id}:{miembro_in.email}"
        if not r_sync.set(lock_key, "locked", nx=True, ex=5):
            raise HTTPException(status_code=409, detail="Procesando invitación. Por favor aguarde un instante.")
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"⚠️ Degradación elegante del Mutex en Redis: {e}")

    entidad_validada_id = None
    empresa_nombre = None

    from core.database.session import tenant_session_ctx
    from core.database.models_tenant import UsuarioEntidadRol, RazonSocialPropia

    try:
        with tenant_session_ctx(current_user.tenant.schema_name) as tenant_db:
            empresa = tenant_db.query(RazonSocialPropia).filter(RazonSocialPropia.id == miembro_in.entidad_id).first()
            if not empresa:
                raise HTTPException(status_code=404, detail="La empresa seleccionada no existe o no tienes acceso a ella.")

            rol_existente = tenant_db.query(UsuarioEntidadRol).filter_by(
                user_id=miembro_in.email,
                entidad_id=empresa.id
            ).first()
            if rol_existente:
                raise HTTPException(status_code=409, detail=f"El usuario ya tiene acceso a la empresa {empresa.razon_social}.")

            entidad_validada_id = empresa.id
            empresa_nombre = str(empresa.razon_social)

        from core.security.auth import create_access_token
        from datetime import timedelta

        invite_expires = timedelta(hours=48)
        invite_token = create_access_token(
            data={
                "sub": miembro_in.email,
                "type": "magic_link_invite",
                "entidad_id": entidad_validada_id,
                "tenant_schema": current_user.tenant.schema_name,
                "tenant_id_master": tenant_id_str,
                "role": miembro_in.rol.upper()
            },
            expires_delta=invite_expires
        )

        from core.tasks.notification_tasks import send_magic_link_email_task
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
        magic_link_url = f"{frontend_url}/join?token={invite_token}"

        send_magic_link_email_task.apply_async(
            args=[miembro_in.email, magic_link_url, empresa_nombre]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fallo crítico al generar invitación para {miembro_in.email} en tenant {current_user.tenant.schema_name}: {e}")
        raise HTTPException(status_code=500, detail="Fallo sistémico al generar el enlace de invitación.")

    return InvitacionResponse(
        message=f"Invitación generada para {miembro_in.email}.",
        magic_link_token=invite_token,
        expires_in_hours=48
    )

# 🌟 MICRO-SEGMENTACIÓN: Solo dueños pueden modificar equipo
@router.patch("/{email}", response_model=MiembroEquipoResponse, dependencies=[Depends(RoleChecker(["admin", "owner", "dueño", "propietario"]))])
def actualizar_miembro(
    email: str,
    miembro_upd: MiembroEquipoUpdate,
    db_master: Session = Depends(get_db_session),
    current_user: CachedUser = Depends(get_current_user)
):
    tenant_id_str = str(current_user.tenant.id)

    miembro = db_master.query(User).filter(User.email == email, User.tenant_id == tenant_id_str).first()
    if not miembro:
        raise HTTPException(status_code=404, detail="Usuario no encontrado en el equipo.")

    # 🛡️ SEGURO ANTI-LOCKOUT (Degradación de Rol)
    roles_administrativos = ['admin', 'owner', 'dueño', 'propietario']

    if miembro_upd.rol and miembro_upd.rol.lower() not in roles_administrativos and miembro.role.lower() in roles_administrativos:
        admin_count = db_master.query(User).filter(
            User.tenant_id == tenant_id_str,
            User.is_active == True,
            func.lower(User.role).in_(roles_administrativos)
        ).count()

        if admin_count <= 1:
            raise HTTPException(
                status_code=400,
                detail="Acción denegada: Eres el último administrador. Degradar tu cuenta dejará a la empresa sin acceso administrativo."
            )

    if email == current_user.email and miembro_upd.is_active is False:
        raise HTTPException(status_code=400, detail="Acción bloqueada: No puedes desactivar tu propia cuenta.")

    if miembro_upd.rol is not None:
        miembro.role = miembro_upd.rol.lower()

        try:
            from core.database.session import tenant_session_ctx
            from core.database.models_tenant import UsuarioEntidadRol
            with tenant_session_ctx(current_user.tenant.schema_name) as tenant_db:
                tenant_db.query(UsuarioEntidadRol).filter(
                    UsuarioEntidadRol.user_id == email
                ).update({"rol": miembro_upd.rol.upper()}, synchronize_session=False)
        except Exception as e:
            logger.error(f"Fallo crítico al sincronizar rol de {email} en esquema {current_user.tenant.schema_name}: {e}")
            raise HTTPException(status_code=500, detail="Error de integridad. No se pudo sincronizar el rol en la base operativa.")

    if miembro_upd.is_active is not None:
        miembro.is_active = miembro_upd.is_active

    db_master.commit()
    db_master.refresh(miembro)
    invalidate_user_cache(email)

    return MiembroEquipoResponse(
        id=miembro.id, user_id=miembro.email,
        rol=miembro.role.upper(), is_active=miembro.is_active
    )

# 🌟 MICRO-SEGMENTACIÓN: Solo dueños pueden eliminar equipo
@router.delete("/{email}", status_code=status.HTTP_200_OK, dependencies=[Depends(RoleChecker(["admin", "owner", "dueño", "propietario"]))])
def remover_miembro(
    email: str,
    db_master: Session = Depends(get_db_session),
    current_user: CachedUser = Depends(get_current_user)
):
    tenant_id_str = str(current_user.tenant.id)

    miembro = db_master.query(User).filter(User.email == email, User.tenant_id == tenant_id_str).first()
    if not miembro:
        raise HTTPException(status_code=404, detail="El usuario no se encontró en esta empresa.")

    # 🛡️ SEGURO ANTI-LOCKOUT (Borrado Físico)
    if miembro.role.lower() in ['admin', 'owner', 'dueño', 'propietario']:
        admin_count = db_master.query(User).filter(
            User.tenant_id == tenant_id_str,
            User.is_active == True,
            func.lower(User.role).in_(['admin', 'owner', 'dueño', 'propietario'])
        ).count()

        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="Acción denegada: No puedes eliminar al último administrador de la empresa.")

    if email == current_user.email:
        raise HTTPException(status_code=400, detail="No puedes eliminarte a ti mismo.")

    try:
        from core.database.session import tenant_session_ctx
        from core.database.models_tenant import UsuarioEntidadRol
        with tenant_session_ctx(current_user.tenant.schema_name) as tenant_db:
            tenant_db.query(UsuarioEntidadRol).filter(
                UsuarioEntidadRol.user_id == email
            ).delete(synchronize_session=False)
    except Exception as e:
        logger.error(f"Fallo al purgar identidades en esquema {current_user.tenant.schema_name}: {e}")
        raise HTTPException(status_code=500, detail="Fallo de integridad. No se pudo limpiar la huella del usuario en la base operativa.")

    db_master.delete(miembro)
    db_master.commit()
    invalidate_user_cache(email)

    return {"message": f"Acceso revocado y cuenta eliminada permanentemente para {email}."}