import os
import sys
import logging

# Agregamos la raíz del proyecto al path para que Python encuentre 'core'
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.database.session import SessionLocal
from core.database.models_master import User, Tenant
from core.security.auth import get_password_hash
from core.services.tenant_manager import TenantManager

# Configuración básica de logging para ver qué pasa en la consola
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("INIT_DB")

def initialize_system():
    logger.info("🚀 Iniciando Proceso de Aprovisionamiento Maestro...")

    db = SessionLocal()
    try:
        # ---------------------------------------------------------
        # 1. CREACIÓN DEL SUPER ADMIN (Idempotente)
        # ---------------------------------------------------------
        admin_email = os.environ.get("ADMIN_EMAIL", "hugo_martin_1@yahoo.com.ar")
        admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")

        logger.info(f"🔍 Verificando existencia del Super Admin: {admin_email}")
        user = db.query(User).filter(User.email == admin_email).first()

        if not user:
            # ---------------------------------------------------------
            # 2. CREACIÓN DEL TENANT DE PRUEBA
            # ---------------------------------------------------------
            schema_name = "tenant_001"
            logger.info(f"🔍 Verificando existencia del Tenant Maestro: {schema_name}")
            tenant = db.query(Tenant).filter(Tenant.schema_name == schema_name).first()

            if not tenant:
                logger.info(f"🏗️ Creando Tenant Maestro: {schema_name}")
                # El TenantManager se encarga de todo el proceso de creación y sembrado de cuentas
                tenant = TenantManager.create_tenant(
                    db=db,
                    name="Tribu Canales Digitales",
                    cuit="30712345678",
                    schema_name=schema_name
                )

            logger.info("👤 Creando cuenta de Super Admin...")
            user = User(
                email=admin_email,
                hashed_password=get_password_hash(admin_password),
                full_name="Hugo Tcach",
                role="admin",
                is_active=True,
                tenant_id=tenant.id # Lo atamos al tenant maestro
            )
            db.add(user)
            db.commit()
            logger.info("✅ Super Admin creado con éxito.")
        else:
            logger.info("✅ El Super Admin ya existe. Sistema previamente inicializado.")

        logger.info("🏁 Aprovisionamiento finalizado con éxito.")

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error crítico inicializando la base de datos: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    initialize_system()