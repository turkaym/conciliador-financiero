import logging
import redis
from config.config import settings
from core.afip.auth import AfipAuthManager
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Header
from sqlalchemy.orm import Session
from cryptography import x509

from core.api.deps import get_current_user, get_tenant_db, CachedUser, EntityRoleChecker
from core.database.models.entidades import RazonSocialPropia
from core.security.crypto import encrypt_private_key

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(EntityRoleChecker(["admin", "dueño"]))])

@router.post("/{schema_name}/entidad/{entidad_id}/upload-credentials")
async def upload_afip_credentials(
    schema_name: str,
    entidad_id: int,
    x_entity_id: int = Header(..., alias="X-Entity-ID"),
    certificate: UploadFile = File(...),
    private_key: UploadFile = File(...),
    db: Session = Depends(get_tenant_db),
    current_user: CachedUser = Depends(get_current_user)
):
    if current_user.tenant.schema_name != schema_name:
        logger.critical(f"🛡️ [SECURITY] Ataque IDOR bloqueado. Usuario {current_user.email} intentó acceder al esquema {schema_name}.")
        raise HTTPException(status_code=403, detail="Acceso denegado al espacio de trabajo.")

    # Bloqueo de Mismatch Attack (Escudo perimetral)
    if entidad_id != x_entity_id:
        logger.critical(f"🛡️ [SECURITY] Mismatch de Entidad. Path: {entidad_id} vs Header: {x_entity_id}.")
        raise HTTPException(status_code=403, detail="Conflicto de autoridades. La entidad de la URL no coincide con la cabecera firmada.")

    entidad = db.query(RazonSocialPropia).filter(
        RazonSocialPropia.id == x_entity_id,
        RazonSocialPropia.is_active == True
    ).first()

    if not entidad:
        raise HTTPException(status_code=404, detail="Entidad no encontrada o inactiva.")

    try:
        cert_content = await certificate.read()
        key_content = await private_key.read()

        # 🌟 FIX FORENSE ENTERPRISE: Parseo del certificado X.509 para extraer la expiración real de AFIP
        try:
            cert_obj = x509.load_pem_x509_certificate(cert_content)
        except Exception:
            # Fallback en caso de que venga en formato DER (binario puro sin cabeceras PEM)
            try:
                cert_obj = x509.load_der_x509_certificate(cert_content)
            except Exception as cert_err:
                logger.error(f"Estructura de certificado inválida: {str(cert_err)}")
                raise HTTPException(status_code=400, detail="El archivo provisto no es un certificado X.509 válido en formato PEM o DER.")

        # Extraemos la fecha de expiración real inyectada por la autoridad fiscal
        if hasattr(cert_obj, "not_valid_after_utc"):
            expiration_date = cert_obj.not_valid_after_utc
        else:
            # Compatibilidad con versiones anteriores de la librería cryptography
            expiration_date = cert_obj.not_valid_after.replace(tzinfo=timezone.utc)

        # Ciframos la clave privada usando el motor PBKDF2 + Fernet
        encrypted_key = encrypt_private_key(key_content.decode('utf-8'))

        # Guardamos en la base de datos relacional (PostgreSQL)
        entidad.afip_certificate = cert_content.decode('utf-8')
        entidad.afip_private_key_encrypted = encrypted_key
        entidad.afip_cert_expiration = expiration_date

        db.commit()
        logger.info(f"🛡️ Bóveda Asegurada: Credenciales AFIP validadas para el CUIT {entidad.cuit}. Vencimiento real: {expiration_date.isoformat()}")

        return {
            "status": "success",
            "message": "Credenciales fiscales validadas y almacenadas con trazabilidad absoluta.",
            "cuit": entidad.cuit,
            "expiration": expiration_date.strftime("%Y-%m-%d %H:%M:%S UTC")
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Fallo crítico procesando la bóveda de credenciales AFIP: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Fallo interno al asegurar e indexar las credenciales.")

# Inicializamos el cliente Redis para el endpoint de Test
redis_client_test = redis.from_url(settings.REDIS_URL, decode_responses=True)

@router.get("/{schema_name}/entidad/{entidad_id}/test-connection")
async def test_afip_connection(
    schema_name: str,
    entidad_id: int,
    db: Session = Depends(get_tenant_db),
    current_user: CachedUser = Depends(get_current_user)
):
    if current_user.tenant.schema_name != schema_name:
        raise HTTPException(status_code=403, detail="Acceso denegado.")

    entidad = db.query(RazonSocialPropia).filter(
        RazonSocialPropia.id == entidad_id,
        RazonSocialPropia.is_active == True
    ).first()

    # 🌟 FIX: Validación correcta usando las columnas reales de la base de datos
    if not entidad or not entidad.afip_certificate or not entidad.afip_private_key_encrypted:
        raise HTTPException(status_code=400, detail="La entidad no posee credenciales en la bóveda.")

    try:
        raw_env = getattr(settings, 'PROMETEO_ENV', 'homo')
        env_mode = "prod" if raw_env in ["produccion", "prod", "production"] else "homo"

        # Forzamos force_refresh=True para obligar a ir hasta ARCA y no leer del caché
        with AfipAuthManager(redis_client_test, entidad.afip_certificate, entidad.afip_private_key_encrypted, env_mode) as auth:
            token_data = auth.get_token(entidad.cuit, force_refresh=True)

        return {
            "status": "success",
            "message": "Conexión WSAA establecida.",
            "expiration": token_data.expiration_time.isoformat()
        }
    except RuntimeError as re:
        logger.warning(f"Test AFIP Fallido (Negocio/Red): {re}")
        raise HTTPException(status_code=502, detail=str(re))
    except Exception as e:
        logger.error(f"Test AFIP Fallido (Interno): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Fallo criptográfico o estructural al intentar contactar a AFIP.")

@router.delete("/{schema_name}/entidad/{entidad_id}/credentials")
async def revoke_afip_credentials(
    schema_name: str,
    entidad_id: int,
    db: Session = Depends(get_tenant_db),
    current_user: CachedUser = Depends(get_current_user)
):
    if current_user.tenant.schema_name != schema_name:
        raise HTTPException(status_code=403, detail="Acceso denegado al espacio de trabajo.")

    entidad = db.query(RazonSocialPropia).filter(
        RazonSocialPropia.id == entidad_id,
        RazonSocialPropia.is_active == True
    ).first()

    if not entidad:
        raise HTTPException(status_code=404, detail="Entidad no encontrada o inactiva.")

    # Purgado de datos sensibles
    entidad.afip_certificate = None
    entidad.afip_private_key_encrypted = None
    entidad.afip_cert_expiration = None

    try:
        db.commit()
        logger.info(f"🗑️ [SECURITY] Credenciales revocadas y purgadas para la entidad {entidad_id} ({entidad.cuit}) por {current_user.email}.")

        # Opcional: Podrías limpiar también el token de Redis aquí si quisieras ser extremadamente pulcro
        redis_key = f"wsaa_token:{entidad.cuit}:wsfe:homo" # Asumiendo entorno de prueba
        redis_client_test.delete(redis_key)

        return {"status": "success", "message": "Credenciales revocadas y bóveda purgada exitosamente."}
    except Exception as e:
        db.rollback()
        logger.error(f"Error purgando bóveda para entidad {entidad_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Fallo interno al revocar credenciales.")