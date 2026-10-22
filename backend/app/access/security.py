from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.errors import ApiError
from app.models import User

password_hash = PasswordHash.recommended()
dummy_hash = "$argon2id$v=19$m=65536,t=3,p=4$aQSspJ3//ENfXwT+R3YLjw$vB8GV3LVtARTu/X/HjTVVNLOYqgAVDzc3Cc9NrIOfJs"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def _invalid_token() -> ApiError:
    return ApiError(
        status_code=401,
        code="INVALID_TOKEN",
        message="Invalid or expired access token",
    )


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


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    try:
        claims = jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
        user_id = int(claims.get("sub", ""))
    except (jwt.InvalidTokenError, TypeError, ValueError):
        raise _invalid_token() from None

    user = db.get(User, user_id)
    if user is None or not user.active:
        raise _invalid_token()
    return user
