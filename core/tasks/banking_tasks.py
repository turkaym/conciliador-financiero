import logging
import os
import random
from core.tasks.celery_config import app
from core.tasks.base_task import DLQTask
from core.utils.redis_locks import redis_lock
from core.storage.minio_client import minio_client
from core.database.session import tenant_session_ctx

logger = logging.getLogger("TASKS_BANKING")

@app.task(name="core.tasks.banking_tasks.process_bank_statement_task", base=DLQTask, bind=True, max_retries=3)
@redis_lock(key_prefix="ingesta")

def process_bank_statement_task(self, tenant_id: str, entidad_id: int, cuenta_id: int, parser_code: str, object_name: str, column_mapping: dict = None, audit_user_id: str = None, audit_ip_address: str = None, **kwargs):
    from core.bank_adapters.ingest import ingest_file
    from core.utils.validators import FileSecurityValidator

    try:
        from core.api.context import set_audit_user_id, set_audit_ip_address
        if audit_user_id:
            set_audit_user_id(int(audit_user_id))
        if audit_ip_address:
            set_audit_ip_address(audit_ip_address)
    except Exception as e:
        logger.warning(f"⚠️ [AUDIT] No se pudo inyectar el contexto de auditoría en Celery: {e}")

    logger.info(f"🏦 [INGESTA ZERO-DISK] Iniciando asíncrono. Cuenta: {cuenta_id} | Object: {object_name}")
    bucket_name = tenant_id.replace("_", "-")
    _, original_extension = os.path.splitext(object_name)
    file_extension = original_extension.lower() if original_extension else ".tmp"
    should_delete_minio = False

    chunk_response = None
    file_stream = None

    try:
        try:
            chunk_response = minio_client.client.get_object(bucket_name, object_name, offset=0, length=2048)
            chunk = chunk_response.read()
        finally:
            if chunk_response:
                chunk_response.close()
                chunk_response.release_conn()

        if hasattr(FileSecurityValidator, 'is_safe_binary_buffer'):
            is_valid = FileSecurityValidator.is_safe_binary_buffer(chunk, file_extension)
        else:
            is_valid = True

        if not is_valid:
            raise ValueError("[PARSING_ERROR] El archivo está corrupto o tiene un formato camuflado.")

        def emisor_progreso(porcentaje: int, mensaje: str):
            self.update_state(state='PROCESSING', meta={'progress': porcentaje, 'message': mensaje})

        file_stream = minio_client.client.get_object(bucket_name, object_name)

        try:
            # 🌟 FIX: Extraemos el cuenta_contable_id del payload de kwargs que envía FastAPI
            cuenta_contable_id = kwargs.get('cuenta_contable_id', 0)

            with tenant_session_ctx(tenant_id) as db_ingest:
                resultado = ingest_file(
                    db=db_ingest,
                    file_stream=file_stream,
                    file_extension=file_extension,
                    parser_code=parser_code,
                    cuenta_id=cuenta_id,
                    entidad_id=entidad_id,
                    cuenta_contable_id=cuenta_contable_id, # 🌟 FIX: Pasamos el parámetro
                    progress_cb=emisor_progreso,
                    column_mapping=column_mapping
                )
        finally:
            if file_stream:
                file_stream.close()
                file_stream.release_conn()

        logger.info(f"✅ [INGESTA] Completada exitosamente: {resultado}")
        should_delete_minio = True
        return resultado

    except ValueError as ve:
        logger.error(f"❌ [INGESTA] Rechazo de Negocio: {ve}")
        should_delete_minio = True
        raise ValueError(f"[BUSINESS_LOGIC] {str(ve)}")

    except Exception as e:
        logger.error(f"❌ [INGESTA] Fallo procesando cuenta {cuenta_id}: {e}", exc_info=True)
        if self.request.retries >= self.max_retries:
            logger.critical(f"☠️ [DLQ TRAP] Cuarentenando archivo: {object_name}")

            # 🌟 FIX UX: Emitimos un estado final explícito al túnel SSE
            self.update_state(state='QUARANTINED', meta={'progress': 100, 'message': 'El archivo fue bloqueado y puesto en cuarentena por seguridad.'})

            should_delete_minio = True
            try:
                minio_client.quarantine_file(tenant_id, object_name, self.request.id)
            except Exception as copy_err:
                logger.error(f"Fallo al mover a cuarentena: {copy_err}")
                should_delete_minio = False

        # Calculamos la base exponencial (15s, 30s, 60s)
        base_delay = 15 * (2 ** self.request.retries)
        # Añadimos un factor de dispersión aleatoria (hasta un 25% extra de tiempo)
        jitter = random.uniform(0, base_delay * 0.25)
        # El tiempo final de espera descentraliza la carga del worker
        raise self.retry(exc=e, countdown=int(base_delay + jitter))

    finally:
        try:
            with tenant_session_ctx(tenant_id) as db_state:
                # 🌟 FIX ARQUITECTURA: Evaluamos el modelo real, no el enum de negocio
                modelo_origen = kwargs.get('modelo_origen', 'LEGACY').upper()

                if modelo_origen == 'TESORERIA':
                    from core.database.models.tesoreria import CuentaTesoreria
                    db_state.query(CuentaTesoreria).filter(CuentaTesoreria.id == cuenta_id).update(
                        {"is_syncing": False, "last_task_id": None},
                        synchronize_session=False
                    )
                else:
                    from core.database.models_tenant import CuentaBancaria
                    db_state.query(CuentaBancaria).filter(CuentaBancaria.id == cuenta_id).update(
                        {"is_syncing": False, "last_task_id": None},
                        synchronize_session=False
                    )

                db_state.commit()

        except Exception as lock_err:
            logger.critical(f"FATAL: No se pudo liberar estado is_syncing de la cuenta {cuenta_id}: {lock_err}")

        if should_delete_minio:
            try:
                minio_client.client.remove_object(bucket_name, object_name)
            except Exception as e:
                logger.error(f"❌ [STORAGE] Fallo al eliminar {object_name} en MinIO: {e}")