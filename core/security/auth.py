import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt
from passlib.context import CryptContext
from core.api.deps import revoke_token, oauth2_scheme
from fastapi import APIRouter, Depends, status

# 🌟 NUEVO: Importamos nuestra configuración centralizada tipada
from config.config import settings

# --- MOTOR DE SEGURIDAD SUPERIOR ---
# Implementación pura de Argon2id (Ganador de la Password Hashing Competition)
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto"
)

# Carga estricta de secretos delegada a Pydantic Settings
# Ya no usamos os.getenv ni validamos manualmente, si falta algo, FastAPI explota solo al arrancar.
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Valida la integridad del password usando Argon2id."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Genera un hash irreversible de alta resistencia mediante Argon2id."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Emite un JWT firmado criptográficamente con los claims de identidad y UUID."""
    to_encode = data.copy()

    # 🌟 Usamos el tiempo de expiración de nuestra config global
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    # Inyectamos el JTI para la Denylist de Redis y la fecha en UTC puro
    to_encode.update({
        "exp": expire,
        "jti": str(uuid.uuid4())
    })

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)