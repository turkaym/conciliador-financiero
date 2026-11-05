from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # --- Configuración Básica ---
    PROJECT_NAME: str = "Conciliador ERP"
    VERSION: str = "1.0.0"

    # --- Seguridad (Obligatorios) ---
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    ENCRYPTION_KEY_MASTER: str

    # --- Variables de Base de Datos (Leen del .env) ---

    # --- Variables de Base de Datos (Leen del .env) ---
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str = "postgres"
    DB_PORT: str = "5432"
    DB_NAME: str = "conciliador_master"

    # --- Caché y Colas ---
    REDIS_URL: str = "redis://redis:6379/0"
    RABBITMQ_URL: str

    # --- Integraciones Externas (Opcionales) ---
    PROMETEO_API_KEY: Optional[str] = None
    PROMETEO_ENV: str = "testing"
    CLOUDFLARE_TOKEN: Optional[str] = None
    SLACK_OPERATIONS_WEBHOOK: Optional[str] = None

    # 🌟 FIX ARQUITECTURA: Variables Transaccionales (SMTP)
    SMTP_HOST: str = "smtp.resend.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = "resend"
    SMTP_PASS: Optional[str] = None
    EMAIL_FROM: str = "Conciliador ERP <notificaciones@htsolution.org>"
    FRONTEND_URL: str = "http://localhost:5173"

    # 💳 FASE 10: MOTOR DE PAGOS (Stripe)
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None

    # IDs de los Productos/Precios en Stripe (ej: price_1Pxyz...)
    STRIPE_PRICE_STARTER: Optional[str] = None
    STRIPE_PRICE_BUSINESS: Optional[str] = None
    STRIPE_PRICE_ENTERPRISE: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

settings = Settings()
