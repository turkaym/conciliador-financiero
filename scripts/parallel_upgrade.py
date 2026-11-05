import concurrent.futures
import os
import sys
import time
from urllib.parse import quote_plus
from sqlalchemy import text, create_engine

# Asegurar path raíz
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from alembic.config import Config
from alembic import command
from config.config import settings

def migrate_tenant(schema_name: str) -> dict:
    """
    Ejecuta Alembic de forma programática y aislada.
    Devuelve un diccionario con el resultado y el estado para forzar el Fail-Fast del orquestador.
    """
    try:
        # VISIÓN 360: Bypass obligatorio del multiplexor PgBouncer para DDL
        db_user = quote_plus(settings.DB_USER)
        db_pass = quote_plus(settings.DB_PASSWORD)
        bypass_host = os.environ.get("DB_HOST_DIRECT", "postgres")
        bypass_port = os.environ.get("DB_PORT_DIRECT", "5432")
        db_name = os.environ.get("DB_NAME_MASTER", "conciliador_master")

        direct_url = f"postgresql://{db_user}:{db_pass}@{bypass_host}:{bypass_port}/{db_name}"
        engine_ddl = create_engine(direct_url, pool_pre_ping=True)

        with engine_ddl.connect() as connection:
            # Enrutamiento estricto a nivel base de datos
            connection.execute(text(f'SET search_path TO "{schema_name}", public'))

            alembic_cfg = Config(os.path.join(BASE_DIR, "alembic.ini"))
            alembic_cfg.config_file_name = None
            alembic_cfg.set_main_option("script_location", os.path.join(BASE_DIR, "alembic_tenants"))

            # 🌟 FIX ARQUITECTURA: Inyectamos el schema exactamente igual que en la creación
            alembic_cfg.attributes['connection'] = connection
            alembic_cfg.attributes['tenant_schema'] = schema_name

            command.upgrade(alembic_cfg, "head")

            # Forzamos la persistencia del DDL
            connection.commit()

        engine_ddl.dispose()
        return {"status": "success", "message": f"✅ {schema_name} actualizado exitosamente."}
    except Exception as e:
        # 🌟 FIX MANUAL v4.1: Retornamos el error como estado 'failed'
        return {"status": "failed", "message": f"❌ Fallo crítico en {schema_name}:\n{str(e)}"}

def run_parallel_migrations(max_workers: int = 5):
    print(f"🚀 Iniciando Orquestador Paralelo (Aislamiento Programático)...")
    start_time = time.time()

    # Importación local para evitar forkeo de conexiones
    from core.database.session import engine
    with engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS tenant_template"))
        conn.commit()

        schemas = conn.execute(
            text("SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 'tenant_%'")
        ).fetchall()

    schema_names = [s[0] for s in schemas]
    print(f"📦 Se encolaron {len(schema_names)} esquemas inquilinos.")

    has_failures = False # 🌟 Bandera de Fail-Fast

    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(migrate_tenant, schema) for schema in schema_names]

        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            print(result["message"])
            if result["status"] == "failed":
                has_failures = True

    elapsed = round(time.time() - start_time, 2)

    if has_failures:
        print(f"🛑 Despliegue ABORTADO por errores críticos en uno o más inquilinos. Tiempo: {elapsed} segundos.")
        sys.exit(1) # 🌟 Muerte del proceso para CI/CD
    else:
        print(f"🏁 Despliegue global finalizado en {elapsed} segundos.")

if __name__ == "__main__":
    run_parallel_migrations(max_workers=5)