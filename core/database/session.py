import logging
import sys
import os
import json
import hashlib
from sqlalchemy import create_engine, text, event, insert
from sqlalchemy.orm import sessionmaker, Session, Mapper, object_session, ColumnProperty
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool, QueuePool
from contextlib import contextmanager

from config.config import settings
from sqlalchemy.orm.attributes import get_history

logger = logging.getLogger("DB_SESSION")

# ==========================================
# 🌟 ARQUITECTURA: POOLING INTELIGENTE
# ==========================================
is_celery = "celery" in sys.argv[0] or os.environ.get("IS_CELERY_WORKER") == "1"

if is_celery:
    logger.info("🔧 [ENGINE] Celery detectado: Usando NullPool (PgBouncer Mode) para prevenir fugas.")
    pool_class = NullPool
    pool_kwargs = {}
else:
    logger.info("🔧 [ENGINE] API detectada: Usando QueuePool nativo para máximo rendimiento síncrono.")
    pool_class = QueuePool
    pool_kwargs = {
        "pool_size": 20,
        "max_overflow": 10,
        "pool_timeout": 30,
        "pool_recycle": 1800
    }

engine = create_engine(
    settings.DATABASE_URL,
    poolclass=pool_class,
    pool_pre_ping=True,
    connect_args={"prepare_threshold": None},
    **pool_kwargs
)

@event.listens_for(Engine, "first_connect")
def setup_postgresql_extensions(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
        cursor.execute("COMMIT;")
    except Exception as e:
        logger.error(f"💥 Fallo al aprovisionar extensiones: {e}")
    finally:
        cursor.close()

@event.listens_for(Engine, "checkin")
def receive_checkin(dbapi_connection, connection_record):
    if dbapi_connection is None:
        return
    try:
        dbapi_connection.rollback()
        estado_original = dbapi_connection.autocommit
        dbapi_connection.autocommit = True
        cursor = dbapi_connection.cursor()
        try:
            # Saneamiento y reseteo de roles por si la conexión vuelve de una sesión de IA
            cursor.execute("RESET ROLE;")
            cursor.execute("DISCARD ALL;")
        finally:
            cursor.close()
            dbapi_connection.autocommit = estado_original
    except Exception as e:
        connection_record.invalidate(e)

# ==========================================
# 🛡️ INTERCEPTOR ORM: Enrutamiento Dual O(1) (FLUSH LEVEL)
# ==========================================
def _get_audit_context():
    try:
        from core.api.context import get_audit_user_id, get_audit_ip_address, get_audit_tenant_id
        return get_audit_user_id() or "SYSTEM", get_audit_ip_address() or "127.0.0.1", get_audit_tenant_id()
    except Exception:
        return "SYSTEM", "127.0.0.1", None

@event.listens_for(Session, "after_flush")
def audit_after_flush(session, flush_context):
    """
    Surgical Intercept: Dispara exactamente después de que SQLAlchemy procesa la memoria
    y tiene los IDs generados, pero ANTES de cerrar la transacción.
    """
    if getattr(session, '_auditing_now', False):
        return

    session._auditing_now = True
    try:
        master_events = []
        tenant_events = []

        user_id, ip_address, current_tenant = _get_audit_context()
        secret = getattr(settings, "SECRET_KEY", "fallback_secret")

        def procesar_evento(obj, action, changes_dict):
            if getattr(obj, "__tablename__", "") in ["audit_trail", "logs_auditoria", "system_logs", "cola_mensajes_muertos"]:
                return

            is_master = hasattr(obj.__class__, '__table_args__') and isinstance(obj.__class__.__table_args__, dict) and obj.__class__.__table_args__.get('schema') == 'public'

            raw_details = json.dumps(changes_dict, sort_keys=True)
            firma_str = f"{'MASTER' if is_master else 'TENANT'}|{action}|{obj.__tablename__}|{user_id}|{raw_details}|{secret}"
            hash_firma = hashlib.sha256(firma_str.encode('utf-8')).hexdigest()

            if is_master:
                master_events.append({
                    "tenant_id": int(current_tenant) if current_tenant and str(current_tenant).isdigit() else None,
                    "user_id": int(user_id) if user_id and str(user_id).isdigit() else None,
                    "action": action,
                    "entity_name": obj.__tablename__,
                    "entity_id": str(getattr(obj, "id", "")),
                    "ip_address": ip_address,
                    "changes": changes_dict,
                    "hash_firma": hash_firma
                })
            else:
                tenant_events.append({
                    "entidad": obj.__tablename__,
                    "entidad_id": int(getattr(obj, "id", 0)) if getattr(obj, "id", None) else 0,
                    "accion": action,
                    "usuario_id": str(user_id),
                    "ip_origen": ip_address,
                    "detalles": raw_details,
                    "hash_firma": hash_firma
                })

        for obj in session.new:
            payload = {c.key: str(getattr(obj, c.key)) for c in obj.__mapper__.columns}
            procesar_evento(obj, "INSERT", payload)

        for obj in session.dirty:
            changes = {}
            for attr in obj.__mapper__.attrs:
                if not isinstance(attr, ColumnProperty):
                    continue

                history = get_history(obj, attr.key)
                if history.has_changes():
                    changes[attr.key] = {
                        "old": str(history.deleted[0]) if history.deleted else None,
                        "new": str(history.added[0]) if history.added else None
                    }
            if changes:
                procesar_evento(obj, "UPDATE", changes)

        for obj in session.deleted:
            payload = {c.key: str(getattr(obj, c.key)) for c in obj.__mapper__.columns}
            procesar_evento(obj, "DELETE", {"old": payload})

        if tenant_events:
            from core.database.models_tenant import OutboxEvent
            outbox_payloads = [
                {
                    "aggregate_type": "LogAuditoria",
                    "payload": event,
                    "status": "PENDING"
                }
                for event in tenant_events
            ]
            session.connection().execute(insert(OutboxEvent).values(outbox_payloads))

    except Exception as e:
        logger.error(f"Fallo crítico en motor de Auditoría: {e}", exc_info=True)
    finally:
        session._auditing_now = False

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_master_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==========================================
# 🌟 UNIFICACIÓN ARQUITECTÓNICA MULTI-TENANT
# ==========================================
def get_tenant_db(schema_name: str):
    connection = engine.connect()
    connection = connection.execution_options(schema_translate_map={None: schema_name})
    TenantSession = sessionmaker(bind=connection, autocommit=False, autoflush=False)
    db = TenantSession()
    try:
        yield db
    finally:
        db.close()
        connection.close()

@contextmanager
def tenant_session_ctx(schema_name: str):
    connection = engine.connect()
    connection = connection.execution_options(schema_translate_map={None: schema_name})
    TenantSession = sessionmaker(bind=connection, autocommit=False, autoflush=False)
    db = TenantSession()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
        connection.close()

# ==========================================
# 🤖 FASE 14.3: BLINDAJE TEXT-TO-SQL (AI ROL)
# ==========================================
@contextmanager
def ai_readonly_session(schema_name: str):
    """
    Context Manager de Alta Seguridad.
    Fuerza el ruteo al esquema del inquilino y aplica un candado a nivel de motor de PostgreSQL
    cambiando el rol transaccional a 'ai_readonly_role'. Bloquea físicamente INSERT/UPDATE/DELETE.
    """
    connection = engine.connect()
    connection = connection.execution_options(schema_translate_map={None: schema_name})

    TenantSession = sessionmaker(bind=connection, autocommit=False, autoflush=False)
    db = TenantSession()

    try:
        # 1. Bajamos los privilegios del usuario 'admin' en esta transacción específica
        db.execute(text("SET LOCAL ROLE ai_readonly_role;"))
        # 2. Impedimos alteraciones estructurales/DML
        db.execute(text("SET LOCAL default_transaction_read_only = 'on';"))

        yield db

        # En Solo Lectura el commit es irrelevante para datos, pero sella la transacción
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"💥 Operación destructiva detectada en sesión IA (Bloqueada por PostgreSQL): {e}")
        raise
    finally:
        db.close()
        connection.close()
