import logging
from celery.result import AsyncResult
from datetime import datetime, timezone, timedelta
from core.tasks.celery_config import app
from core.tasks.base_task import DLQTask
from core.database.session import SessionLocal, tenant_session_ctx
from core.database.models_master import Tenant, User
from core.database.models_tenant import CuentaBancaria
from core.services.tenant_manager import TenantManager

logger = logging.getLogger("TASKS_MAINTENANCE")

# ==========================================
# 🌟 EL META-CRON (ORQUESTADOR UNIVERSAL)
# ==========================================
import time

# ==========================================
# 🌟 EL META-CRON (ORQUESTADOR UNIVERSAL)
# ==========================================
@app.task(name="core.tasks.maintenance_tasks.meta_orchestrator_task")
def meta_orchestrator_task(tarea_esclava: str, queue_name: str, extra_kwargs: dict = None):
    """Abre la maestra una sola vez y despacha N tareas esclavas dinámicamente."""
    logger.info(f"🔄 [META-CRON] Orquestando masivamente: {tarea_esclava} -> {queue_name}")
    master_db = SessionLocal()
    extra_kwargs = extra_kwargs or {}
    try:
        # 🌟 FIX OOM: Extraemos exclusivamente el string del esquema, no el objeto pesado.
        query = master_db.query(Tenant.schema_name).filter(Tenant.is_active == True)
        schemas = [row[0] for row in query.all()]
    except Exception as e:
        logger.error(f"❌ [META-CRON] Fallo al leer maestra: {e}")
        return
    finally:
        master_db.close()

    # 🌟 FIX BROKER SPIKE: Inyección parcelada (Chunking Asíncrono)
    for i, tenant_id in enumerate(schemas):
        kwargs = {"tenant_id": tenant_id}
        kwargs.update(extra_kwargs)
        app.send_task(tarea_esclava, kwargs=kwargs, queue=queue_name)

        # Cada 50 mensajes, liberamos presión de red por 100ms
        if (i + 1) % 50 == 0:
            time.sleep(0.1)

    logger.info(f"✨ [META-CRON] {len(schemas)} tareas '{tarea_esclava}' delegadas exitosamente.")

# ==========================================
# 🌟 TAREAS ESCLAVAS
# ==========================================
@app.task(name="core.tasks.maintenance_tasks.sweep_tenant_zombies_task", bind=True)
def sweep_tenant_zombies_task(self, tenant_id: str):
    liberadas = 0
    now_utc = datetime.now(timezone.utc)
    try:
        with tenant_session_ctx(tenant_id) as db:
            cuentas_zombies = db.query(CuentaBancaria).filter(CuentaBancaria.is_syncing == True).all()
            for cuenta in cuentas_zombies:
                if not cuenta.last_task_id:
                    cuenta.is_syncing = False
                    liberadas += 1
                    continue

                res = AsyncResult(cuenta.last_task_id, app=app)
                if res.state in ['SUCCESS', 'FAILURE', 'REVOKED']:
                    cuenta.is_syncing = False
                    liberadas += 1
                elif res.state == 'PENDING' and cuenta.updated_at:
                    cuenta_updated = cuenta.updated_at.replace(tzinfo=timezone.utc) if cuenta.updated_at.tzinfo is None else cuenta.updated_at
                    if (now_utc - cuenta_updated) > timedelta(hours=2):
                        cuenta.is_syncing = False
                        liberadas += 1
                        logger.warning(f"👻 [SWEEPER] Cazada cuenta ZOMBIE {cuenta.id} en {tenant_id}.")
            db.commit()
        if liberadas > 0:
            logger.info(f"✨ [SWEEPER] Tenant {tenant_id}: {liberadas} cuentas destrabadas.")
    except Exception as e:
        logger.error(f"❌ [SWEEPER] Fallo limpiando tenant {tenant_id}: {e}")

@app.task(name="core.tasks.maintenance_tasks.run_tenant_matching_task", base=DLQTask, bind=True, max_retries=1)
def run_tenant_matching_task(self, tenant_id: str, entidad_id: int = 1):
    from core.matching.engine import run_advanced_matching
    with tenant_session_ctx(tenant_id) as db:
        try:
            matches = run_advanced_matching(db, tenant_id, entidad_id)
            logger.info(f"✅ [MATCHING] Tenant {tenant_id}: {matches} matches automáticos creados.")
        except Exception as e:
            db.rollback()
            logger.error(f"❌ [MATCHING] Error Lógico/Estructural en Tenant {tenant_id}: {e}", exc_info=True)
            raise e

@app.task(name="core.tasks.maintenance_tasks.run_tenant_fiscal_audit_task", bind=True)
def run_tenant_fiscal_audit_task(self, tenant_id: str):
    from core.tasks.auditor import ejecutar_auditoria_integral
    with tenant_session_ctx(tenant_id) as db:
        ejecutar_auditoria_integral(db, tenant_id)

@app.task(name="core.tasks.maintenance_tasks.provision_new_tenant_task", bind=True, max_retries=3)
def provision_new_tenant_task(self, schema_name: str):
    logger.info(f"🏗️ [PROVISIÓN] Iniciando construcción de esquema para: {schema_name}")
    db = SessionLocal()
    try:
        TenantManager.provision_tenant(db, schema_name)
        logger.info(f"✅ [PROVISIÓN] Éxito total aprovisionando: {schema_name}")
        return {"status": "success", "tenant": schema_name}
    except Exception as e:
        raise self.retry(exc=e, countdown=10 * (2 ** self.request.retries))
    finally:
        db.close()

@app.task(name="core.tasks.maintenance_tasks.purge_tenant_cache_task", bind=True, max_retries=3)
def purge_tenant_cache_task(self, tenant_id: int):
    from core.api.deps import invalidate_user_cache
    db = SessionLocal()
    try:
        users = db.query(User).filter(User.tenant_id == tenant_id).all()
        purged = 0
        for user in users:
            try:
                invalidate_user_cache(user.email)
                purged += 1
            except Exception:
                pass
        logger.info(f"✅ [WORKER] Caché aniquilada para {purged} usuarios del Tenant {tenant_id}.")
        return {"status": "success", "purged": purged}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=10)
    finally:
        db.close()