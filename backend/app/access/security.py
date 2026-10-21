from datetime import datetime, timedelta, timezone

import jwt
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import User

password_hash = PasswordHash.recommended()
dummy_hash = "$argon2id$v=19$m=65536,t=3,p=4$aQSspJ3//ENfXwT+R3YLjw$vB8GV3LVtARTu/X/HjTVVNLOYqgAVDzc3Cc9NrIOfJs"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = db.scalar(
        select(User).where(
            func.lower(User.email) == email.strip().lower(), User.active.is_(True)
        )
    )
    stored_hash = user.password_hash if user else dummy_hash
    valid_password = password_hash.verify(password, stored_hash)
    return user if user and valid_password else None


def create_access_token(user_id: int) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    return jwt.encode(
        {"sub": str(user_id), "exp": expires_at},
        settings.jwt_secret_key,
        algorithm="HS256",
    )
