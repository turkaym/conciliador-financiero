from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.access.schemas import LoginRequest, TokenResponse, UserResponse
from app.access.security import authenticate_user, create_access_token
from app.config import settings
from app.database import get_db
from app.errors import ApiError

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Annotated[Session, Depends(get_db)]):
    user = authenticate_user(db, payload.email, payload.password)
    if user is None:
        raise ApiError(
            status_code=401,
            code="INVALID_CREDENTIALS",
            message="Invalid email or password",
        )

    return TokenResponse(
        access_token=create_access_token(user.id),
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserResponse.model_validate(user),
    )
