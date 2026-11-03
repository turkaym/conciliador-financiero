import os
import uuid
import logging
import asyncio
import redis.asyncio as aioredis
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, APIRouter, Request
from fastapi.middleware.cors import CORSMiddleware

from core.database.session import engine
from core.database.models_master import Base as MasterBase
from core.api.deps import get_current_user, FeatureChecker
from config.config import settings
from config.feature_flags import feature_flags
from core.api.context import set_audit_ip_address

# Middlewares propios
from core.api.middleware_idempotency import IdempotencyMiddleware

from core.api.v1.endpoints.auth import router as auth_router
from core.domains.comprobantes.router import router as comprobantes_router
from core.domains.contabilidad.router import router as contabilidad_router
from core.api.v1.endpoints.bancos import router as bancos_router
from core.api.v1.endpoints.reports import router as reports_router
from core.api.v1.endpoints.entidades import router as entidades_router
from core.api.v1.endpoints.equipo import router as equipo_router
from core.api.v1.endpoints.tenants import router as tenants_router
from core.api.v1.endpoints.padrones import router as padrones_router
from core.api.v1.endpoints.dlq_admin import router as dlq_router
from core.api.v1.endpoints.afip_vault import router as afip_vault_router
from core.api.permissions import RoleChecker
from core.api.v1.endpoints.system import router as system_router
from core.api.v1.endpoints import billing
from core.api.v1.endpoints.pagos import router as pagos_router
from core.api.v1.endpoints.fiscal import router as fiscal_router

logger = logging.getLogger(__name__)

# ==========================================
# LIFESPAN: Inicialización y Apagado Seguro
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Iniciando API Gateway (Booting sequence)...")

    max_retries = 5
    base_delay = 2

    # 1. Inicialización de Redis y Pool de Conexiones
    for attempt in range(1, max_retries + 1):
        try:
            redis_pool = aioredis.ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True)
            # 🌟 FIX FASE D: Almacenamos el pool para poder destruirlo limpiamente
            app.state.redis_pool = redis_pool
            app.state.redis = aioredis.Redis(connection_pool=redis_pool)
            await app.state.redis.ping()

            logger.info("✅ Conexión asíncrona a Redis establecida.")
            break
        except Exception as e:
            if attempt == max_retries:
                logger.critical(f"❌ Fallo crítico de red. Redis inalcanzable tras {max_retries} intentos: {e}")
                raise e
            wait_time = base_delay * (2 ** (attempt - 1))
            logger.warning(f"⏳ Redis no encontrado. Reintentando en {wait_time}s...")
            await asyncio.sleep(wait_time)

    # 2. Verificación de DB Maestra
    logger.info("Verificando conexión a la Base de Datos Maestra...")
    for attempt in range(1, max_retries + 1):
        try:
            with engine.connect() as conn:
                from sqlalchemy import text
                conn.execute(text("SELECT 1"))
            logger.info("✅ Conexión a DB maestra verificada.")
            break
        except Exception as e:
            if attempt == max_retries:
                logger.critical(f"❌ Fallo crítico conectando a la Base de Datos. Abortando: {e}")
                raise e
            wait_time = base_delay * (2 ** (attempt - 1))
            logger.warning(f"⏳ DB no está lista. Reintentando en {wait_time}s...")
            await asyncio.sleep(wait_time)

    yield

    logger.info("🛑 Apagando API Gateway de forma segura...")
    # 🌟 FIX FASE D: Cierre estricto del Connection Pool para evitar fugas de memoria
    if hasattr(app.state, 'redis_pool'):
        await app.state.redis_pool.disconnect()
        logger.info("✅ Redis Connection Pool destruido.")

app = FastAPI(
    title="Conciliador SaaS API",
    description="Gateway unificado de servicios con soporte Multi-Empresa y RBAC",
    version="1.6.0",
    lifespan=lifespan
)

# Inyección de Middleware de Idempotencia (Debe ir antes que el de Auditoría en la declaración)
app.add_middleware(IdempotencyMiddleware)

# ==========================================
# MOTOR DE AUDITORÍA Y TRAZABILIDAD
# ==========================================
@app.middleware("http")
async def audit_and_trace_middleware(request: Request, call_next):
    # 1. Extracción o Creación del Pasaporte
    correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    request.state.correlation_id = correlation_id

    # 2. Auditoría IP
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        ip = cf_ip.strip()
    else:
        forwarded = request.headers.get("X-Forwarded-For")
        ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "127.0.0.1")

    set_audit_ip_address(ip)

    # 3. Procesamiento blindado contra Crashes
    try:
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response
    except Exception as e:
        # 🌟 FIX FORENSE: Si el servidor explota, garantizamos el log con el UUID antes de morir
        logger.error(f"🚨 [CRITICAL CRASH] TraceID {correlation_id} | Ruta: {request.url.path} | Error: {str(e)}")
        raise e


# --- CONFIGURACIÓN CORS ENTERPRISE ---
origins = [
    "http://localhost:5173",
    "https://app.htsolution.org",
    "https://api.htsolution.org",
    "https://admin.htsolution.org",
    "https://htsolution.org",
]

extra_origins = os.getenv("CORS_ORIGINS", "")
if extra_origins:
    origins.extend(extra_origins.split(","))

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# TOPOLOGÍA DE RUTAS BLINDADA (RBAC)
# ==========================================

# 1. Rutas Públicas
public_router = APIRouter(prefix="/v1")
public_router.include_router(auth_router, prefix="/auth", tags=["Seguridad"])
if feature_flags.usable("b2b_directory"):
    public_router.include_router(entidades_router, prefix="/entidades", tags=["Entidades (Multi-Empresa)"])

# 2. Rutas de Operador (Lectura y Gestión Operativa)
operator_router = APIRouter(
    prefix="/v1",
    dependencies=[Depends(get_current_user), Depends(RoleChecker(["admin", "operator", "operador", "owner", "dueño", "propietario","visor", "editor"]))]
)
if feature_flags.usable("tax_registries"):
    operator_router.include_router(afip_vault_router, prefix="/afip-vault", tags=["Integración Fiscal AFIP"])
if feature_flags.usable("expenses_payments"):
    operator_router.include_router(bancos_router, prefix="/bancos", tags=["Bancos"])
    operator_router.include_router(pagos_router, prefix="/pagos", tags=["Egresos y Pagos"])
operator_router.include_router(contabilidad_router, prefix="/contabilidad", tags=["Contabilidad"])
if feature_flags.usable("ai_copilot"):
    from core.api.v1.endpoints.ai import router as ai_router
    operator_router.include_router(ai_router, tags=["Copiloto Financiero"])
if feature_flags.usable("reconciliation"):
    from core.api.v1.endpoints.matching import router as matching_router
    operator_router.include_router(matching_router, prefix="/matching", tags=["Conciliación"])
if feature_flags.usable("team"):
    operator_router.include_router(equipo_router, prefix="/equipo", tags=["Equipo y Permisos"])
operator_router.include_router(reports_router, prefix="/reports", tags=["Reportes Contables"])

# 🌟 FIX FASE C: Inyección del Router Tributario (SIRE, Padrones Activos)
if feature_flags.usable("tax_registries"):
    operator_router.include_router(fiscal_router, prefix="/fiscal", tags=["Gestión Tributaria y DDJJ"])


# 3. Rutas de Administración (Gestión Estricta del Sistema)
admin_router = APIRouter(
    prefix="/v1",
    dependencies=[Depends(get_current_user), Depends(RoleChecker(["admin", "superadmin", "owner", "dueño", "propietario", "editor"]))]
)
admin_router.include_router(tenants_router, prefix="/tenants", tags=["Gestión de Inquilinos"])
if feature_flags.usable("tax_registries"):
    admin_router.include_router(padrones_router, prefix="/padrones", tags=["Padrones Fiscales"])
if feature_flags.usable("b2b_integrations"):
    from core.api.v1.endpoints.b2b_setup import router as b2b_router
    admin_router.include_router(b2b_router, prefix="/b2b", tags=["B2B Integrations"])
admin_router.include_router(dlq_router, prefix="/dlq", tags=["Administración DLQ"])

app.include_router(system_router, prefix="/v1", tags=["Sistema"])
app.include_router(public_router)
app.include_router(operator_router)
app.include_router(admin_router)
app.include_router(billing.router, prefix="/v1/billing", tags=["Facturación B2B"])
app.include_router(comprobantes_router)

@app.get("/health", tags=["Infraestructura"])
def health_check():
    return {
        "status": "online",
        "version": "1.6.0",
        "multi_empresa": True,
        "rbac_enabled": True
    }
