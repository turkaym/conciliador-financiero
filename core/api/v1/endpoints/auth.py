import hashlib
import json
import logging
from datetime import timedelta

import redis
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from starlette.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from jose import jwt, JWTError
from pydantic import BaseModel

from config.config import settings
from core.schemas.auth import OTPRequest, OTPVerify, UserCreate, Token
from core.security.otp_manager import OTPManager
from core.api.deps import get_db_session, get_current_user, CachedUser, revoke_token, invalidate_user_cache
from core.security.auth import create_access_token, verify_password, get_password_hash
from core.database.models_master import User, Tenant
from core.services.tenant_manager import TenantManager
from core.api.rate_limiter import IPRateLimiter

router = APIRouter(tags=["Autenticación y Setup"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="v1/auth/login")
logger = logging.getLogger(__name__)

# ==========================================
# SCHEMAS DE INVITACIÓN
# ==========================================
class AcceptInviteRequest(BaseModel):
    token: str
    password: str

# ==========================================
# ENDPOINTS DE REGISTRO Y LOGIN
# ==========================================

@router.post("/register", status_code=status.HTTP_202_ACCEPTED)
async def register(user_in: UserCreate, db: Session = Depends(get_db_session)):
    # 🌟 FIX CONDICIÓN DE CARRERA: Eliminamos el SELECT previo.
    nuevo_tenant = None
    try:
        nuevo_tenant = TenantManager.create_tenant(
            db=db,
            name=user_in.company_name,
            cuit=user_in.cuit
        )

        hashed_pw = await run_in_threadpool(get_password_hash, user_in.password)

        new_user = User(
            email=user_in.email.lower(),
            hashed_password=hashed_pw,
            tenant_id=nuevo_tenant.id,
            role="admin",
            is_active=False
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

    except IntegrityError:
        db.rollback()
        # 🌟 FIX COMPENSACIÓN: Si falla por duplicidad, limpiamos la basura
        if nuevo_tenant:
            TenantManager.deprovision_tenant(db, nuevo_tenant.schema_name, hard_delete=True)
        raise HTTPException(status_code=409, detail="El email o CUIT ya se encuentra registrado.")

    except ValueError as ve:
        db.rollback()
        logger.warning(f"Rechazo de negocio en registro: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))

    except Exception as e:
        db.rollback()
        if nuevo_tenant:
            try:
                TenantManager.deprovision_tenant(db, nuevo_tenant.schema_name, hard_delete=True)
            except Exception as rollback_err:
                logger.critical(f"Fallo catastrófico en compensación de registro para {nuevo_tenant.schema_name}: {rollback_err}")

        logger.error(f"Error crítico en registro: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor. No se pudo completar el registro.")

    otp_enviado = True
    try:
        # Lazy Import intencional para evitar importaciones circulares pesadas (Celery Tasks)
        from core.tasks.notification_tasks import send_otp_email_task

        otp_code = await OTPManager.generate_otp(user_in.email)
        send_otp_email_task.apply_async(
            kwargs={"email": user_in.email, "otp_code": otp_code}
        )
        logger.info(f"📧 [AUTO] Activación encolada para {user_in.email}")
    except ValueError as ve:
        logger.warning(f"⚠️ OTP Cooldown activo para {user_in.email}. Tarea cancelada: {ve}")
        otp_enviado = False
    except Exception as e_otp:
        logger.error(f"⚠️ Fallo al encolar OTP post-registro: {e_otp}")
        otp_enviado = False

    if not otp_enviado:
        return {
            "message": "Cuenta creada con éxito, pero el envío del código automático está temporalmente bloqueado por límite de intentos. Por favor, solicita un reenvío desde la pantalla de activación.",
            "schema_name": nuevo_tenant.schema_name
        }

    return {
        "message": "Cuenta creada con éxito. Te enviamos un código de 6 dígitos a tu correo para activar la cuenta.",
        "schema_name": nuevo_tenant.schema_name
    }


# ==========================================
# FIX FASE 4.1: MAPEO DE CAPACIDADES (RBAC)
# ==========================================
def _get_permissions_for_role(role: str) -> list:
    """Traduce el rol duro del usuario en un vector de capacidades (Capabilities)."""
    r = role.lower() if role else ""
    if r in ["admin", "dueño", "propietario"]:
        return [
            "liquidar_ordenes",
            "anular_ordenes",
            "anular_pagos_conciliados",
            "ver_maestros",
            "editar_maestros"
        ]
    elif r == "editor":
        return [
            "liquidar_ordenes",
            "anular_ordenes",
            "ver_maestros"
        ]
    elif r == "operador":
        return ["ver_maestros"] # El operador solo ve, no liquida ni anula
    return []

@router.post(
    "/login",
    response_model=Token,
    dependencies=[Depends(IPRateLimiter(action="login", limit_seconds=60, max_requests=5))]
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db_session)
):
    user = db.query(User).filter(User.email == form_data.username.lower()).first()

    is_valid_password = False
    if user:
        is_valid_password = await run_in_threadpool(verify_password, form_data.password, user.hashed_password)

    if not user or not is_valid_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail={
                "message": "Cuenta pendiente de activación.",
                "action": "REQUIRE_OTP_VERIFICATION",
                "email": user.email
            }
        )

    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
    if not tenant or not tenant.is_active:
        raise HTTPException(status_code=404, detail="Espacio de trabajo inactivo o en construcción.")

    tenant_features = tenant.features if isinstance(tenant.features, dict) else {}
    if isinstance(tenant.features, str):
        try:
            tenant_features = json.loads(tenant.features)
        except json.JSONDecodeError:
            tenant_features = {}

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    # 🌟 FIX FASE 4.1: Inyección del vector de permisos en el Token JWT
    user_permissions = _get_permissions_for_role(user.role)

    access_token = create_access_token(
        data={
            "sub": user.email,
            "tenant_id": tenant.schema_name,
            "role": user.role,
            "permissions": user_permissions # <-- Inyectado en JWT (Opcional pero recomendado para otros microservicios)
        },
        expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "tenant_id": tenant.schema_name,
        "user": {
            "id": str(user.id),
            "email": user.email,
            "role": user.role,
            "tenant_id": tenant.schema_name,
            "permissions": user_permissions # <-- 🌟 FIX FASE 4.1: Inyectado en el Store de React (Zustand)
        },
        "features": tenant_features
    }


@router.post("/refresh", response_model=Token)
def refresh_token(
    token: str = Depends(oauth2_scheme),
    current_user: CachedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    tenant_schema = current_user.tenant.schema_name
    user_email = current_user.email
    user_role = current_user.role

    revoke_token(token)

    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado en la base maestra.")

    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
    if not tenant or not tenant.is_active:
        raise HTTPException(status_code=404, detail="Espacio de trabajo inactivo o en construcción.")

    tenant_features = tenant.features if isinstance(tenant.features, dict) else {}
    if isinstance(tenant.features, str):
        try:
            tenant_features = json.loads(tenant.features)
        except json.JSONDecodeError:
            tenant_features = {}

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    user_permissions = _get_permissions_for_role(user_role)

    new_access_token = create_access_token(
        data={
            "sub": user_email,
            "tenant_id": tenant_schema,
            "role": user_role,
            "permissions": user_permissions
        },
        expires_delta=access_token_expires
    )

    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "tenant_id": tenant_schema,
        "user": {
            "id": str(current_user.id),
            "email": user_email,
            "role": user_role,
            "tenant_id": tenant_schema,
            "permissions": user_permissions # <-- 🌟 FIX FASE 4.1: Mantenemos la persistencia en el refresh
        },
        "features": tenant_features
    }

@router.post("/logout", status_code=status.HTTP_200_OK, tags=["Seguridad"])
def logout_seguro(
    token: str = Depends(oauth2_scheme),
    current_user: CachedUser = Depends(get_current_user)
):
    revoke_token(token)
    invalidate_user_cache(current_user.email)
    return {"status": "success", "message": "Sesión cerrada de forma segura y token revocado."}


@router.post(
    "/request-otp",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(IPRateLimiter(action="request_otp", limit_seconds=60, max_requests=3))]
)
async def request_activation_otp(
    payload: OTPRequest,
    db: Session = Depends(get_db_session)
):
    user = db.query(User).filter(User.email == payload.email.lower()).first()

    success_msg = {"message": "Si el correo está registrado y pendiente de activación, se enviará un código."}

    if not user or user.is_active:
        return success_msg

    try:
        # Lazy Import intencional para tareas Celery
        from core.tasks.notification_tasks import send_otp_email_task

        otp_code = await OTPManager.generate_otp(payload.email)
        send_otp_email_task.apply_async(
            kwargs={"email": user.email, "otp_code": otp_code}
        )
    except ValueError as ve:
        # 🌟 FIX ENMASCARAMIENTO: Informamos al cliente si hay bloqueo por Flooding en Redis
        raise HTTPException(status_code=429, detail=str(ve))
    except Exception as celery_err:
        logger.warning(f"⚠️ No se pudo encolar el email en RabbitMQ: {celery_err}")

    return success_msg


@router.post(
    "/verify-otp",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(IPRateLimiter(action="verify_otp", limit_seconds=60, max_requests=5))]
)
async def verify_activation_otp(
    payload: OTPVerify,
    db: Session = Depends(get_db_session)
):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    if user.is_active:
        raise HTTPException(status_code=400, detail="El usuario ya se encuentra activo.")

    is_valid = await OTPManager.validate_otp(payload.email, payload.otp_code)

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El código ingresado es inválido o ha expirado."
        )

    try:
        user.is_active = True
        db.commit()
        return {"message": "Cuenta verificada y activada exitosamente. Ya puede iniciar sesión."}
    except Exception as e:
        db.rollback()
        logger.error(f"Error al activar usuario tras OTP válido: {e}")
        raise HTTPException(status_code=500, detail="Error interno al guardar la activación.")

# ==========================================
# ENDPOINT DE ACEPTACIÓN DE INVITACIÓN (Magic Link)
# ==========================================

@router.post(
    "/accept-invite",
    status_code=status.HTTP_200_OK,
    tags=["Setup Equipo"],
    dependencies=[Depends(IPRateLimiter(action="accept_invite", limit_seconds=60, max_requests=5))]
)
async def accept_invite(
    payload: AcceptInviteRequest,
    db: Session = Depends(get_db_session)
):
    # 🌟 FIX HITO 7.13: Anti-Replay Absoluto
    token_hash = hashlib.sha256(payload.token.encode('utf-8')).hexdigest()
    redis_key = f"blacklist:invite:{token_hash}"

    # Forzamos un cliente SÍNCRONO puro para evitar Corrutinas descartadas
    r_sync = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)

    try:
        # exists() devuelve > 0 si la llave ya existe
        if r_sync.exists(redis_key) > 0:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="El enlace de invitación ya fue utilizado y ha sido quemado por seguridad."
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"⚠️ Degradación elegante en revisión de Blacklist: {e}")

    # 1. Validación Criptográfica del Token
    try:
        token_data = jwt.decode(payload.token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if token_data.get("type") != "magic_link_invite":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token inválido para este flujo.")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="El enlace de invitación es inválido o ha expirado.")

    email = token_data.get("sub")
    raw_role = token_data.get("role", "OPERADOR").upper()

    role_mapping = {
        "OPERATOR": "OPERADOR",
        "OPERADOR": "OPERADOR",
        "ADMIN": "OPERADOR",
        "OWNER": "DUEÑO",
        "DUEÑO": "DUEÑO",
        "PROPIETARIO": "DUEÑO"
    }
    role = role_mapping.get(raw_role, "OPERADOR")
    tenant_schema = token_data.get("tenant_schema")
    tenant_id_master = token_data.get("tenant_id_master")
    entidad_id = token_data.get("entidad_id")

    # 2. Materialización y Configuración de Credenciales
    hashed_pw = await run_in_threadpool(get_password_hash, payload.password)

    user = db.query(User).filter(User.email == email).first()
    is_new_creation = False

    if not user:
        is_new_creation = True
        user = User(
            email=email,
            hashed_password=hashed_pw,
            tenant_id=tenant_id_master,
            role=role.lower(),
            is_active=True
        )
        db.add(user)
    else:
        user.hashed_password = hashed_pw
        user.tenant_id = tenant_id_master
        user.role = role.lower()
        user.is_active = True

    db.commit()
    db.refresh(user)

    # 3. Propagación de Identidad Tenant
    try:
        from core.database.session import tenant_session_ctx
        from core.database.models_tenant import UsuarioEntidadRol

        with tenant_session_ctx(tenant_schema) as tenant_db:
            rol_existente = tenant_db.query(UsuarioEntidadRol).filter_by(
                user_id=email, entidad_id=entidad_id
            ).first()

            if not rol_existente:
                nuevo_rol = UsuarioEntidadRol(
                    user_id=email,
                    entidad_id=entidad_id,
                    rol=role
                )
                tenant_db.add(nuevo_rol)
    except Exception as e:
        logger.error(f"Fallo de propagación Zero-Trust: {e}")

        if is_new_creation:
            db.delete(user)
            db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Fallo sistémico al inyectar permisos en la empresa. Operación revertida."
        )

    # 🌟 FIX HITO 7.13: QUEMADO GARANTIZADO DEL TOKEN
    try:
        # TTL fijo de 48 horas (172800 segundos) para evadir cálculos riesgosos
        r_sync.setex(redis_key, 172800, "burned")
        logger.info(f"🔥 Token Magic Link quemado en Redis con éxito para {email}.")
    except Exception as e:
        logger.error(f"Fallo crítico al quemar Magic Link en Redis: {e}")

    return {"message": "Cuenta configurada y activada exitosamente. Ya puedes iniciar sesión."}