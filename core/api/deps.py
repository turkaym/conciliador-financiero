import json
import logging
import hashlib
from typing import Generator, List
from datetime import datetime, timezone

import redis
from fastapi import HTTPException, Depends, status, Header, Request, Query
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from jose import jwt, JWTError
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.sql import func
from passlib.context import CryptContext

from config.config import settings
from core.database.session import SessionLocal, get_tenant_db
from core.database.models_master import Tenant, User
from core.schemas.auth import TokenData
from core.api.context import set_audit_user_id, set_audit_tenant_id, get_audit_user_id, get_audit_ip_address, get_audit_tenant_id

logger = logging.getLogger("AUTH_CACHE")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="v1/auth/login")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Argon2id es resistente a ataques por GPU/ASIC
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

try:
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
except Exception as e:
    logger.error(f"Error inicializando Redis: {e}")
    redis_client = None

class CachedTenant:
    def __init__(self, id: int, schema_name: str, is_active: bool, features: dict = None, subscription_status: str = "trialing", manual_subscription_bypass: bool = False):
        self.id = id
        self.schema_name = schema_name
        self.is_active = is_active
        self.features = features or {}
        self.subscription_status = subscription_status
        self.manual_subscription_bypass = manual_subscription_bypass

class CachedUser:
    def __init__(self, id: int, email: str, role: str, is_active: bool, tenant: CachedTenant, sub: str):
        self.id = id
        self.email = email
        self.role = role
        self.is_active = is_active
        self.tenant = tenant
        self.sub = sub

def get_current_user(token: str = Depends(oauth2_scheme)) -> CachedUser:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar la identidad o el token expiró",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        tenant_id = payload.get("tenant_id")
        role_from_jwt = payload.get("role", "admin")
        jti = payload.get("jti")

        if email is None or tenant_id is None:
            raise credentials_exception

        if jti and redis_client:
            try:
                if redis_client.exists(f"blacklist:{jti}"):
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Token revocado. Sesión terminada por seguridad."
                    )
            except redis.RedisError as e:
                logger.warning(f"Error verificando denylist en Redis: {e}")

        token_data = TokenData(email=email, tenant_id=str(tenant_id), role=role_from_jwt)
    except JWTError:
        raise credentials_exception

    cache_key = f"auth:session:{token_data.email}"

    # =======================================================
    # 1. INTENTO DE LECTURA DESDE RAM (Fast Path)
    # =======================================================
    if redis_client:
        try:
            cached_data = redis_client.get(cache_key)
            if cached_data:
                data = json.loads(cached_data)

                if not data.get("is_active"):
                    raise HTTPException(status_code=403, detail="Usuario inactivo o suspendido")
                if not data.get("tenant_active"):
                    raise HTTPException(status_code=403, detail="Empresa suspendida temporalmente")

                tenant = CachedTenant(
                    id=data["tenant_id"],
                    schema_name=data["tenant_schema"],
                    is_active=data["tenant_active"],
                    features=data.get("tenant_features", {}),
                    subscription_status=data.get("subscription_status", "trialing"),
                    manual_subscription_bypass=data.get("manual_subscription_bypass", False)
                )

                user_id = data.get("id")
                active_role = data.get("role", token_data.role)

                if user_id:
                    set_audit_user_id(user_id)
                set_audit_tenant_id(tenant.id)

                return CachedUser(
                    id=user_id,
                    email=token_data.email,
                    role=active_role,
                    is_active=data["is_active"],
                    tenant=tenant,
                    sub=token_data.email
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Error leyendo caché de sesión, fallback a DB: {e}")

    # =======================================================
    # 2. FALLBACK A BASE DE DATOS Y RE-HIDRATACIÓN (Slow Path)
    # =======================================================
    db = SessionLocal()
    try:
        user = db.query(User).options(joinedload(User.tenant)).filter(User.email == token_data.email).first()

        if user is None:
            raise credentials_exception
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Usuario inactivo o suspendido")
        if not user.tenant.is_active:
            raise HTTPException(status_code=403, detail="Empresa suspendida temporalmente")

        if redis_client:
            try:
                cache_payload = {
                    "id": user.id,
                    "role": user.role,
                    "is_active": user.is_active,
                    "account_status": getattr(user, 'status', 'ACTIVE'),
                    "tenant_id": user.tenant.id,
                    "tenant_schema": user.tenant.schema_name,
                    "tenant_active": user.tenant.is_active,
                    "tenant_features": getattr(user.tenant, 'features', {}),
                    "subscription_status": getattr(user.tenant, 'subscription_status', 'trialing'),
                    "manual_subscription_bypass": getattr(user.tenant, 'manual_subscription_bypass', False)
                }
                redis_client.setex(cache_key, 3600, json.dumps(cache_payload))
            except redis.RedisError as e:
                logger.warning(f"Error guardando sesión en caché: {e}")

        tenant_obj = CachedTenant(
            id=user.tenant.id,
            schema_name=user.tenant.schema_name,
            is_active=user.tenant.is_active,
            features=getattr(user.tenant, 'features', {}),
            subscription_status=getattr(user.tenant, 'subscription_status', 'trialing'),
            manual_subscription_bypass=getattr(user.tenant, 'manual_subscription_bypass', False)
        )

        set_audit_user_id(user.id)
        set_audit_tenant_id(user.tenant.id)

        return CachedUser(
            id=user.id,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            tenant=tenant_obj,
            sub=user.email
        )
    finally:
        db.close()

def verify_sse_token(token: str = Query(..., description="Short-lived SSE Token")):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "sse":
            raise HTTPException(status_code=403, detail="Tipo de token inválido para streaming")
        return payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="El token de transmisión en vivo expiró.")

def get_db_session() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_tenant_db_session(current_user: CachedUser = Depends(get_current_user)) -> Generator:
    tenant = current_user.tenant

    if not tenant or not tenant.is_active:
        raise HTTPException(status_code=403, detail="Espacio de trabajo (Tenant) no encontrado o inactivo")

    if not tenant.manual_subscription_bypass:
        estado_suscripcion = tenant.subscription_status or "trialing"
        if estado_suscripcion not in ["active", "trialing"]:
            logger.warning(f"🛑 [PAYWALL] Acceso bloqueado al Tenant {tenant.schema_name}. Estado: {estado_suscripcion}")
            raise HTTPException(
                status_code=402,
                detail="Suscripción inactiva o con pago pendiente. Por favor, regularice su plan."
            )

    yield from get_tenant_db(tenant.schema_name)

def invalidate_user_cache(email: str):
    if not redis_client:
        return
    try:
        cache_key = f"auth:session:{email}"
        redis_client.delete(cache_key)
        logger.info(f"Caché invalidada exitosamente para: {email}")
    except Exception as e:
        logger.warning(f"Error borrando caché de Redis para {email}: {e}")

def revoke_token(token: str):
    if not redis_client:
        logger.error("No se pudo revocar el token porque Redis está inaccesible.")
        return
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM], options={"verify_signature": False})
        jti = payload.get("jti")
        exp = payload.get("exp")

        if not jti or not exp:
            return

        now = datetime.now(timezone.utc).timestamp()
        ttl = int(exp - now)

        if ttl > 0:
            redis_client.setex(f"blacklist:{jti}", ttl, "revoked")
            logger.info(f"🛡️ [SECURITY] Token {jti} revocado. Quedará en Denylist por {ttl} segundos.")
    except JWTError as e:
        logger.warning(f"Intento de revocar un token malformado: {e}")

class RoleChecker:
    """Verificador Global de Rol a nivel JWT."""
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = [r.lower() for r in allowed_roles]

    def __call__(self, current_user: CachedUser = Depends(get_current_user)):
        user_role = str(current_user.role).lower()
        if user_role not in self.allowed_roles:
            logger.warning(
                f"🚫 [SECURITY] Intento de acceso no autorizado. "
                f"Usuario: {current_user.email} | Rol: {current_user.role} | Requerido: {self.allowed_roles}"
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permisos suficientes.")
        return current_user

class EntityRoleChecker:
    """
    🛡️ Escudo Zero-Trust Multi-Entidad.
    Cruza la base de datos para garantizar que el usuario posea la autoridad
    financiera explícita sobre la Entidad/Sucursal en la que intenta operar.
    """
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = [r.lower() for r in allowed_roles]

    def __call__(
        self,
        x_entity_id: int = Header(..., alias="X-Entity-ID", description="ID de la Razón Social Activa"),
        current_user: CachedUser = Depends(get_current_user),
        db: Session = Depends(get_tenant_db_session)
    ):
        # 1. Fallback Global: Dueños y Admins de sistema tienen paso libre entre sucursales
        if str(current_user.role).lower() in ["dueño", "owner", "admin", "superadmin"]:
            return current_user

        enlace = None

        # 2. Búsqueda Restrictiva en Base de Datos (Normalizada)
        try:
            from core.database.models_tenant import UsuarioEntidadRol
            from sqlalchemy import func

            # 🌟 FIX ARQUITECTURA: La DB guarda Emails en 'user_id'.
            # Normalizamos ambos lados a minúsculas y sin espacios para evitar falsos negativos.
            enlace = db.query(UsuarioEntidadRol).filter(
                func.trim(func.lower(UsuarioEntidadRol.user_id)) == current_user.email.strip().lower(),
                UsuarioEntidadRol.entidad_id == x_entity_id
            ).first()

        except ImportError:
            logger.error("No se encontró el modelo UsuarioEntidadRol. Omitiendo validación.")
            raise HTTPException(status_code=501, detail="Configuración Multi-Entidad incompleta.")
        except Exception as e:
            logger.error(f"Fallo de motor SQL en escudo Multi-Entidad: {str(e)}")
            raise HTTPException(status_code=500, detail="Error crítico validando la matriz de autoridades.")

        # 3. Resolución FSM y RBAC Blindada
        # Extraemos el valor real. Si SQLAlchemy lo mapea como Enum (ej: RolEnum.OPERADOR),
        # lo convertimos a string, tomamos la última parte, lo pasamos a minúscula y quitamos espacios.
        rol_real = getattr(enlace.rol, "value", str(enlace.rol)) if enlace else ""
        rol_limpio = str(rol_real).split(".")[-1].strip().lower()

        if not enlace or rol_limpio not in self.allowed_roles:
            logger.warning(
                f"🚫 [ZERO-TRUST] Intento de Autoridad Cruzada bloqueado. "
                f"User: {current_user.email} intentó manipular Entidad: {x_entity_id}. "
                f"Rol detectado: '{rol_limpio}'"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Brecha de seguridad: No posees autoridad financiera sobre esta Entidad/Sucursal."
            )

        return current_user

class FeatureChecker:
    def __init__(self, required_feature: str):
        self.required_feature = required_feature

    def __call__(self, current_user: CachedUser = Depends(get_current_user)):
        features = current_user.tenant.features
        if isinstance(features, dict) and not features.get(self.required_feature):
             raise HTTPException(status_code=403, detail=f"Tu plan no incluye: {self.required_feature}")
        elif isinstance(features, list) and self.required_feature not in features:
             raise HTTPException(status_code=403, detail=f"Tu plan no incluye: {self.required_feature}")
        return current_user

def verify_api_key_hash(plain_key: str, hashed_key: str) -> bool:
    return pwd_context.verify(plain_key, hashed_key)

def get_b2b_client(
    tenant_schema: str,
    api_key: str = Depends(api_key_header)
) -> CachedUser:
    if not api_key or "." not in api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key format")

    prefix, secret_part = api_key.split(".", 1)

    # =======================================================
    # 🌟 FAST PATH: Caché Criptográfica Efímera (Bypass Argon2id)
    # =======================================================
    cache_key = None
    if redis_client:
        # Generamos un hash rápido SHA-256 de toda la llave para usar de identificador en RAM
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        cache_key = f"b2b_auth_valid:{tenant_schema}:{api_key_hash}"
        try:
            if redis_client.get(cache_key) == "valid":
                tenant_obj = CachedTenant(id=1, schema_name=tenant_schema, is_active=True)
                bot_email = f"b2b_bot_{prefix}@{tenant_schema}.system"
                set_audit_user_id("B2B_SYSTEM")
                set_audit_tenant_id(tenant_obj.id)
                return CachedUser(id=0, email=bot_email, role="b2b_system", is_active=True, tenant=tenant_obj, sub=bot_email)
        except Exception as e:
            logger.warning(f"Fallo al leer caché criptográfica B2B: {e}")

    # =======================================================
    # SLOW PATH: Validación Base de Datos y Argon2id
    # =======================================================
    db_gen = get_tenant_db(tenant_schema)
    db = next(db_gen)

    try:
        from core.database.models_tenant import ApiKey
        key_record = db.query(ApiKey).filter(ApiKey.prefix == prefix).first()

        if not key_record or not key_record.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API Key is invalid or inactive")

        if key_record.expires_at and key_record.expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API Key has expired")

        # Esto es lo que hunde la CPU en un ataque DoS si no se frena antes
        if not verify_api_key_hash(secret_part, key_record.hashed_key):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API Key is invalid")

        key_record.last_used_at = func.now()
        db.commit()

        # 🌟 Otorgamos pasaporte de 5 minutos en la RAM
        if redis_client and cache_key:
            try:
                redis_client.setex(cache_key, 300, "valid")
            except Exception:
                pass

        tenant_obj = CachedTenant(id=1, schema_name=tenant_schema, is_active=True)
        bot_email = f"b2b_bot_{prefix}@{tenant_schema}.system"

        set_audit_user_id("B2B_SYSTEM")
        set_audit_tenant_id(tenant_obj.id)

        return CachedUser(
            id=0,
            email=bot_email,
            role="b2b_system",
            is_active=True,
            tenant=tenant_obj,
            sub=bot_email
        )
    finally:
        db.close()

# ==========================================
# 🛡️ ESCUDO ANTI-DOS PERIMETRAL (B2B & ERPs)
# ==========================================
class B2BRateLimiter:
    """
    Algoritmo 'Fixed Window' atómico. Actúa ANTES de la criptografía.
    """
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    # 🌟 FIX ARQUITECTURA: Desacoplamos del get_b2b_client para que evalúe la cabecera pura
    async def __call__(self, request: Request, api_key: str = Depends(api_key_header)):
        # Extracción segura de la identidad sin tocar Base de Datos
        client_id = "unknown_ip"
        if api_key and "." in api_key:
            client_id = api_key.split(".", 1)[0]
        elif request.client:
            client_id = request.client.host

        key = f"rate_limit:b2b:{client_id}"

        # Soporte híbrido para Redis asíncrono o síncrono (según inyección de FastAPI)
        redis_inst = getattr(request.app.state, "redis", None)

        try:
            if redis_inst:
                async with redis_inst.pipeline(transaction=True) as pipe:
                    pipe.incr(key)
                    pipe.ttl(key)
                    results = await pipe.execute()
                current_count, ttl = results[0], results[1]
                if current_count == 1 or ttl == -1:
                    await redis_inst.expire(key, self.window_seconds)
            elif redis_client:
                with redis_client.pipeline(transaction=True) as pipe:
                    pipe.incr(key)
                    pipe.ttl(key)
                    results = pipe.execute()
                current_count, ttl = results[0], results[1]
                if current_count == 1 or ttl == -1:
                    redis_client.expire(key, self.window_seconds)
            else:
                return # Bypass seguro si no hay Redis

            if current_count > self.max_requests:
                logger.warning(f"🚫 [RATE LIMIT] Firewall bloqueó tráfico de {client_id}. Req: {current_count}/{self.max_requests}.")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Límite de API excedido. Máximo {self.max_requests} peticiones cada {self.window_seconds} segundos."
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Fallo en Rate Limiter nativo: {e}")

# ==========================================
# 🔌 PROVEEDORES DE INTEGRACIÓN EXTERNA (DEPENDENCY INJECTION)
# ==========================================
class AfipClientMock:
    """Mock inyectable para entornos de Test / QA"""
    def get_last_voucher_number(self, pv, cbte):
        raise Exception("Falla simulada de red AFIP para QA (Timeout)")

def get_afip_client():
    """
    Inyector dinámico de dependencias.
    Resuelve la instancia correcta según el entorno (Producción vs Testing).
    """
    # Si estamos en modo de prueba o desarrollo, inyectamos el mock.
    # En producción real, devolveríamos la instancia de tu cliente AFIP verdadero.
    # Por ahora, como lo exige QA Capa 1, forzamos el Mock.
    is_testing_env = getattr(settings, "TESTING_MODE", True)

    if is_testing_env:
        return AfipClientMock()
    else:
        # Aquí iría el cliente real: return RealAfipClient()
        raise NotImplementedError("Cliente AFIP de producción no inyectado aún.")