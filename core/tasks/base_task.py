import logging
from celery import Task
from core.database.session import SessionLocal

logger = logging.getLogger("CELERY_BASE_TASK")

class DLQTask(Task):
    abstract = True

    def validate_tenant_context(self, tenant_id: str) -> bool:
        """🛡️ FIX RIESGO 7: Spoofing de Contexto."""
        master_db = SessionLocal()
        try:
            from core.database.models_master import Tenant
            tenant = master_db.query(Tenant).filter(
                Tenant.schema_name == tenant_id,
                Tenant.is_active == True
            ).first()
            if not tenant:
                logger.critical(f"🚫 [SECURITY] Intento de Spoofing o Tenant inactivo detectado: {tenant_id}")
                return False
            return True
        finally:
            master_db.close()

    def __call__(self, *args, **kwargs):
        tenant_id = kwargs.get('tenant_id')
        if tenant_id and not self.validate_tenant_context(tenant_id):
            raise ValueError(f"[SECURITY_VIOLATION] Contexto de inquilino inválido: {tenant_id}")
        return super().__call__(*args, **kwargs)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        exc_str = str(exc)

        if "[PARSING_ERROR]" in exc_str or "[BUSINESS_LOGIC]" in exc_str or "formato esperado" in exc_str:
            logger.warning(f"⚠️ [WORKER] Fallo de Negocio controlado. No va a DLQ: {exc_str}")
            return

        logger.critical(f"☠️ [DLQ] Tarea {self.name}[{task_id}] MURIÓ por fallo de sistema. Derivando a Dead Letter Queue...")

        tenant_id = kwargs.get('tenant_id')
        entidad_id = kwargs.get('entidad_id', 1)

        if not tenant_id and kwargs.get('email'):
            master_db = SessionLocal()
            try:
                from core.database.models_master import User, Tenant
                user = master_db.query(User).filter(User.email == kwargs.get('email')).first()
                if user:
                    tenant = master_db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
                    if tenant:
                        tenant_id = tenant.schema_name
            except Exception as e_lookup:
                logger.error(f"Fallo al buscar identidad para DLQ: {e_lookup}")
            finally:
                master_db.close()

        # ==========================================
        # 1. INTENTO DE PERSISTENCIA EN BD (Aislado)
        # ==========================================
        cantidad_errores = 0
        db_error_msg = ""

        if tenant_id:
            try:
                from core.database.session import tenant_session_ctx
                from core.database.models_tenant import ColaMensajesMuertos
                from datetime import datetime, timezone, timedelta
                from sqlalchemy import func

                with tenant_session_ctx(tenant_id) as db:
                    context_str = f"ARGS: {args}\nKWARGS: {kwargs}\nTRACEBACK: {einfo.traceback}"
                    pv = kwargs.get('punto_venta', 0)
                    tc = kwargs.get('tipo_cbte', 0)
                    num = kwargs.get('numero', 0)

                    muerto = ColaMensajesMuertos(
                        entidad_id=entidad_id,
                        punto_venta=pv,
                        tipo_cbte_afip=tc,
                        numero=num,
                        error_msg=exc_str,
                        traceback=context_str
                    )
                    db.add(muerto)
                    db.commit()
                    logger.critical(f"🚨 [DLQ_ALERT] MSG_DEAD | Tenant: {tenant_id} | Task: {self.name}")

                    # Cálculo de picos
                    hace_10_minutos = datetime.now(timezone.utc) - timedelta(minutes=10)
                    error_prefix = exc_str[:100]
                    cantidad_errores = db.query(func.count(ColaMensajesMuertos.id)).filter(
                        ColaMensajesMuertos.error_msg.like(f"{error_prefix}%"),
                        ColaMensajesMuertos.created_at >= hace_10_minutos
                    ).scalar()

            except Exception as dlq_err:
                logger.critical(f"☠️ [DLQ] FALLO AL ESCRIBIR EN BD (Tabla faltante o error SQL): {dlq_err}")
                db_error_msg = f"\n⚠️ *Atención:* No se pudo guardar el error en la base de datos."
        else:
            db_error_msg = f"\n⚠️ *Atención:* tenant_id desconocido. Error perdido en el vacío."

        # ==========================================
        # 2. ALERTA A SLACK (Garantizada)
        # ==========================================
        try:
            import requests
            from config.config import settings
            webhook_url = settings.SLACK_OPERATIONS_WEBHOOK

            if webhook_url:
                spike_warning = "\n🔥 *SPIKE MASIVO DETECTADO*" if cantidad_errores >= 5 else ""

                payload = {
                    "text": f"🚨 *CRITICAL ALERT (DLQ ENTRY)* 🚨\n*Tenant:* `{tenant_id or 'UNKNOWN'}`\n*Task:* `{self.name}`\n*Error:* ```{exc_str}```{spike_warning}{db_error_msg}"
                }
                requests.post(webhook_url, json=payload, timeout=3)
                logger.info("✅ [DLQ] Alerta de Slack despachada con éxito.")
            else:
                logger.warning("⚠️ [DLQ] No hay SLACK_OPERATIONS_WEBHOOK configurado.")
        except Exception as web_err:
            logger.error(f"❌ [DLQ] Fallo al despachar Webhook de emergencia a Slack: {web_err}")