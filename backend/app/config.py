import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str
    jwt_secret_key: str
    access_token_expire_minutes: int
    cors_origins: tuple[str, ...]

    @classmethod
    def from_environment(cls) -> "Settings":
        secret = os.getenv("JWT_SECRET_KEY")
        if not secret:
            raise RuntimeError("JWT_SECRET_KEY must be set")

        return cls(
            database_url=os.getenv(
                "DATABASE_URL",
                "postgresql+psycopg://conciliador:conciliador_local_only@localhost:5432/conciliador",
            ),
            jwt_secret_key=secret,
            access_token_expire_minutes=int(
                os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
            ),
            cors_origins=tuple(
                origin.strip()
                for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
                if origin.strip()
            ),
        )


settings = Settings.from_environment()
