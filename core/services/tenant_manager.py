import os
import logging
import shutil
import traceback
from argparse import Namespace
from urllib.parse import quote_plus
from sqlalchemy.orm import Session
from sqlalchemy import text
from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine

from core.database.session import engine, tenant_session_ctx
from core.database.models_tenant import RazonSocialPropia
from core.database.models_master import Tenant, SystemLog
from core.database.seeder import DataSeeder
from config.config import settings

logger = logging.getLogger(__name__)

class TenantManager:
    """
    Servicio de ciclo de vida Multi-Tenant Asíncrono.
    Arquitectura 100% DB-Backed, Orquestada por Alembic y blindada contra concurrencia.
    """

    @staticmethod
    def upgrade_plan_and_features(db: Session, tenant_id: int, features: dict) -> Tenant:
        """
        Aplica un upselling o modificación de features al inquilino.
        Delega la invalidación masiva de caché a Celery para mantener O(1) en la API.
        """
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise ValueError("Inquilino no encontrado en la base maestra.")

        # 1. Inyección de la nueva estructura comercial (Idempotente)
        tenant.features = features
        db.commit()
        db.refresh(tenant)
        logger.info(f"💰 [UPSELLING] Plan comercial persistido en DB para {tenant.schema_name}: {features}")

        # 2. Evaporación Asíncrona de Caché (O(1) para la UI)
        try:
            from core.tasks.maintenance_tasks import purge_tenant_cache_task
            purge_tenant_cache_task.apply_async(args=[tenant_id])
            logger.info(f"🚀 Tarea Celery de purga masiva encolada para Tenant {tenant_id}")
        except Exception as celery_err:
            logger.warning(f"⚠️ Celery inalcanzable. Ejecutando fallback síncrono de purga: {celery_err}")
            # Fallback de Resiliencia: Si RabbitMQ muere, limpiamos a mano para no dejar a los usuarios bloqueados
            from core.database.models_master import User
            from core.api.deps import invalidate_user_cache

            usuarios = db.query(User).filter(User.tenant_id == tenant_id).all()
            for u in usuarios:
                try:
                    invalidate_user_cache(u.email)
                except Exception:
                    pass

        return tenant

    @staticmethod
    def list_tenants(db: Session):
        return db.query(Tenant).order_by(Tenant.id).all()

    @staticmethod
    def create_tenant(db: Session, name: str, cuit: str, schema_name: str = None) -> Tenant:
        if len(cuit) != 11 or not cuit.isdigit():
            raise ValueError(f"El CUIT '{cuit}' debe tener exactamente 11 números.")

        if db.query(Tenant).filter(Tenant.cuit == cuit).first():
            raise ValueError(f"Ya existe un Tenant registrado con el CUIT {cuit}.")

        if schema_name and db.query(Tenant).filter(Tenant.schema_name == schema_name).first():
            raise ValueError(f"El esquema '{schema_name}' ya está en uso.")

        if not schema_name:
            schema_name = f"tenant_{cuit}"

        nuevo_tenant = Tenant(
            name=name,
            cuit=cuit,
            schema_name=schema_name,
            is_active=False
        )
        db.add(nuevo_tenant)

        try:
            db.commit()
            db.refresh(nuevo_tenant)

            try:
                from core.tasks.maintenance_tasks import provision_new_tenant_task, purge_tenant_cache_task
                provision_new_tenant_task.apply_async(args=[schema_name], queue='accounting_queue')
                logger.info(f"📦 Tarea de provisión asíncrona encolada en RabbitMQ para {schema_name}")
            except Exception as e_celery:
                logger.warning(f"⚠️ No se pudo contactar a Celery. Fallback síncrono: {e_celery}")
                TenantManager.provision_tenant(db, schema_name)

            return nuevo_tenant

        except Exception as e:
            db.rollback()
            # 🌟 FIX: Preservamos el registro inactivo para mantener la integridad de la auditoría (SystemLogs)
            raise RuntimeError(f"Error al registrar el tenant: {str(e)}")

    @staticmethod
    def _inject_cuentas_base(tenant_db: Session):
        """Garantiza la existencia de las cuentas ancla necesarias para el Motor de Matching."""
        from core.database.models_tenant import PlanCuentas
        # 🌟 FIX: Expansión del mecanismo de contingencia para incluir las nuevas anclas bimonetarias y pasarelas
        cuentas_requeridas = [
            {"codigo_sistema": "CAJA_FIJA", "nombre": "Caja Fija", "tipo": "ACTIVO"},
            {"codigo_sistema": "BANCOS", "nombre": "Bancos Cuenta Corriente (ARS)", "tipo": "ACTIVO"},
            {"codigo_sistema": "BANCOS_USD", "nombre": "Bancos Moneda Extranjera (USD)", "tipo": "ACTIVO"},
            {"codigo_sistema": "BANCOS_EUR", "nombre": "Bancos Moneda Extranjera (EUR)", "tipo": "ACTIVO"},
            {"codigo_sistema": "BILLETERAS_VIRTUALES", "nombre": "Billeteras Virtuales", "tipo": "ACTIVO"},
            {"codigo_sistema": "VENTAS", "nombre": "Ingresos por Ventas", "tipo": "RESULTADO_POSITIVO"},
            {"codigo_sistema": "COMPRAS_GASTOS", "nombre": "Gastos Generales", "tipo": "RESULTADO_NEGATIVO"},
            {"codigo_sistema": "GASTOS_BANCARIOS", "nombre": "Comisiones y Gastos Bancarios", "tipo": "RESULTADO_NEGATIVO"},
            {"codigo_sistema": "DIF_CAMBIO_POS", "nombre": "Diferencia de Cambio", "tipo": "RESULTADO_POSITIVO"}
        ]

        cuentas_existentes = tenant_db.query(PlanCuentas.codigo_sistema).all()
        codigos_existentes = [c[0] for c in cuentas_existentes if c[0]]

        faltantes = [c for c in cuentas_requeridas if c["codigo_sistema"] not in codigos_existentes]

        if faltantes:
            nuevas_cuentas = []
            for c in faltantes:
                nueva_cuenta = PlanCuentas(
                    codigo=f"SYS-{c['codigo_sistema']}",
                    codigo_sistema=c['codigo_sistema'],
                    nombre=c['nombre'],
                    tipo=c['tipo'],
                    is_system=True,
                    imputable=True
                )
                nuevas_cuentas.append(nueva_cuenta)
            tenant_db.add_all(nuevas_cuentas)
            tenant_db.flush()

    @staticmethod
    def provision_tenant(db: Session, schema_name: str):
        schema_created = False

        tenant_master = db.query(Tenant).filter(Tenant.schema_name == schema_name).first()
        if not tenant_master:
            raise ValueError(f"Incoherencia transaccional: No existe el tenant maestro para {schema_name}")

        try:
            logger.info(f"🏗️ Creando espacio de trabajo para: {schema_name}")
            db.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))

            # 🌟 FIX B2B: Inyección de Permisos Zero-Trust para la Inteligencia Artificial
            # El agente debe poder leer (y solo leer) este nuevo esquema que acaba de nacer.
            try:
                db.execute(text(f'GRANT USAGE ON SCHEMA "{schema_name}" TO ai_readonly_role'))
                db.execute(text(f'GRANT SELECT ON ALL TABLES IN SCHEMA "{schema_name}" TO ai_readonly_role'))
                db.execute(text(f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema_name}" GRANT SELECT ON TABLES TO ai_readonly_role'))
                logger.info(f"🔒 Permisos de solo lectura (AI Copilot) concedidos para {schema_name}.")
            except Exception as perm_err:
                logger.warning(f"⚠️ No se pudo asignar el rol de IA (quizás no existe en el motor): {perm_err}")

            db.commit()
            schema_created = True

            logger.info("⚙️ Generando tablas físicamente vía API Programática de Alembic...")

            BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            PROJECT_ROOT = os.path.dirname(BASE_DIR)

            # Construimos el motor efímero para DDL
            db_user = quote_plus(settings.DB_USER)
            db_pass = quote_plus(settings.DB_PASSWORD)
            bypass_host = os.environ.get("DB_HOST_DIRECT", "postgres")
            bypass_port = os.environ.get("DB_PORT_DIRECT", "5432")
            db_name = os.environ.get("DB_NAME_MASTER", "conciliador_master")

            direct_url = f"postgresql://{db_user}:{db_pass}@{bypass_host}:{bypass_port}/{db_name}"
            engine_ddl = create_engine(direct_url, pool_pre_ping=True)

            try:
                # Usamos una conexión activa y forzamos el search_path
                with engine_ddl.connect() as connection:
                    connection.execute(text(f'SET search_path TO "{schema_name}", public'))

                    # Configuramos Alembic para usar ESTA conexión
                    alembic_cfg = Config(os.path.join(PROJECT_ROOT, "alembic.ini"))
                    alembic_cfg.config_file_name = None # Evita secuestro de logs
                    alembic_cfg.set_main_option("script_location", os.path.join(PROJECT_ROOT, "alembic_tenants"))

                    # Inyectamos la connection en el atributo para que env.py la consuma
                    alembic_cfg.attributes['connection'] = connection
                    alembic_cfg.attributes['tenant_schema'] = schema_name

                    # Ejecutamos la migración
                    command.upgrade(alembic_cfg, "head")

                    # 🌟 FIX PHANTOM DDL: Forzar el guardado físico de la transacción DDL en disco
                    connection.commit()

                    logger.info(f"✅ Estructura base forjada y persistida vía migraciones para {schema_name}.")

            except Exception as alembic_err:
                logger.critical(f"Alembic Engine Error: {alembic_err}")
                raise
            finally:
                # Saneamiento riguroso de conexiones DDL
                engine_ddl.dispose()

            # 3. Sembrado Orgánico y Sincronizado
            try:
                with tenant_session_ctx(schema_name) as tenant_db:
                    DataSeeder.seed_tenant_defaults(tenant_db)
                    TenantManager._inject_cuentas_base(tenant_db)

                    tenant_db.commit() # Sellado atómico de todo el sembrado
            except Exception as e_inner:
                raise RuntimeError(f"Fallo crítico en el sembrado de datos iniciales: {str(e_inner)}")

            # Activación de Infraestructura
            tenant_master.is_active = True
            db.commit()

            logger.info(f"🚀 Tenant {schema_name} aprovisionado de forma íntegra con soporte Fase B.")

        except Exception as e:
            db.rollback()

            error_traceback = traceback.format_exc()
            nuevo_log = SystemLog(
                level="CRITICAL",
                module="TENANT_PROVISIONING",
                message=f"Fallo sistémico en alta de tenant: {str(e)}",
                details=error_traceback,
                tenant_reference=schema_name
            )
            db.add(nuevo_log)
            db.commit()

            logger.critical(f"💥 FALLO EN PROVISIÓN: {str(e)}. Ejecutando Rollback del esquema...")
            if schema_created:
                db.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))
                db.commit()
                logger.warning(f"🧹 Esquema {schema_name} destruido para mantener integridad.")

            tenant_obj_fail = db.query(Tenant).filter(Tenant.schema_name == schema_name).first()
            if tenant_obj_fail:
                tenant_obj_fail.is_active = False
                db.commit()

            raise RuntimeError(f"Fallo sistémico en alta de tenant: {str(e)}")

    @staticmethod
    def deprovision_tenant(db: Session, schema_name: str, hard_delete: bool = False):
        try:
            tenant_obj = db.query(Tenant).filter(Tenant.schema_name == schema_name).first()
            if not tenant_obj:
                raise ValueError(f"No se encontró el tenant '{schema_name}' en la tabla maestra.")

            if hard_delete:
                db.delete(tenant_obj)
                db.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))
                db.commit()
                logger.info(f"🗑️ Base de datos y registro maestro eliminados para {schema_name}.")

                base_data_path = os.environ.get("TENANTS_DATA_PATH", "tenants_data")
                tenant_path = os.path.join(base_data_path, schema_name)
                if os.path.exists(tenant_path):
                    shutil.rmtree(tenant_path)
                    logger.info(f"📁 Directorio de datos eliminado para {schema_name}.")
            else:
                tenant_obj.is_active = False
                db.commit()
                logger.info(f"⏸️ Tenant '{schema_name}' desactivado correctamente (Soft Delete).")

            from core.database.models_master import User
            from core.api.deps import invalidate_user_cache

            usuarios_afectados = db.query(User).filter(User.tenant_id == tenant_obj.id).all()

            for u in usuarios_afectados:
                try:
                    invalidate_user_cache(u.email)
                except Exception as cache_err:
                    logger.debug(f"Caché no encontrada o error al limpiar para {u.email}: {cache_err}")

            logger.info(f"💥 Caché de sesiones aniquilada para {len(usuarios_afectados)} usuarios de {schema_name}.")

        except Exception as e:
            db.rollback()
            logger.error(f"❌ Error crítico en deprovisión de {schema_name}: {str(e)}")
            raise RuntimeError(f"Error crítico en deprovisión: {str(e)}")