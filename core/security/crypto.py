import os
import base64
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

def _get_fernet_instance() -> Fernet:
    """
    Deriva una llave criptográfica segura a partir de la variable de entorno maestra.
    Si la variable cambia, los datos encriptados previamente quedarán inaccesibles.
    """
    secret_seed = os.environ.get("ENCRYPTION_KEY_MASTER")
    if not secret_seed:
        logger.critical("🚨 RIESGO DE SEGURIDAD: ENCRYPTION_KEY_MASTER no definida en .env. Usando llave efímera (Inseguro para Producción).")
        secret_seed = "llave_efimera_desarrollo_conciliador_2026"

    # Derivación de clave PBKDF2 (Estándar Enterprise)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"afip_vault_salt_conciliador",
        iterations=480000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(secret_seed.encode()))
    return Fernet(key)

def encrypt_private_key(private_key_content: str) -> str:
    """Encripta la llave privada en texto plano y devuelve el token cifrado."""
    if not private_key_content:
        return None
    f = _get_fernet_instance()
    return f.encrypt(private_key_content.encode('utf-8')).decode('utf-8')

def decrypt_private_key(encrypted_token: str) -> str:
    """Desencripta el token y devuelve la llave privada original."""
    if not encrypted_token:
        return None
    f = _get_fernet_instance()
    return f.decrypt(encrypted_token.encode('utf-8')).decode('utf-8')