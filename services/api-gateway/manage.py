import sys
import click
from sqlalchemy.orm import Session

# Importamos las piezas necesarias
from alembic.config import Config as AlembicConfig
from alembic import command as alembic_command
from core.database.session import SessionLocal, engine

# Importamos Base (Maestro) y TenantBase (Clientes) correctamente separados
from core.database.base import Base
from core.database.models_master import SystemLog, Tenant
from core.database.models_tenant import TenantBase
from core.services.tenant_manager import TenantManager

# Asegurarnos de que las tablas maestras existan al arrancar el CLI
Base.metadata.create_all(bind=engine)

@click.group()
def cli():
    """
    🛠️ CLI de Administración - Conciliador SaaS ERP
    Herramienta para gestionar la infraestructura desde la terminal.
    """
    pass

# ==========================================
# GRUPO: DB (Base de Datos)
# ==========================================
@cli.group("db")
def db_group():
    """⚙️ Operaciones masivas de Base de Datos (Alembic)."""
    pass

@db_group.command("upgrade-all")
def upgrade_all_tenants():
    """
    Recorre todos los tenants activos y aplica las últimas migraciones de estructura.
    Vital para despliegues a producción (Day 2 Operations).
    """
    db_session = SessionLocal()
    try:
        tenants = db_session.query(Tenant).filter(Tenant.is_active == True).all()
        if not tenants:
            click.secho("⚠️ No hay tenants activos para migrar.", fg="yellow")
            return

        click.secho(f"🚀 Iniciando migración masiva para {len(tenants)} esquemas...", fg="cyan", bold=True)

        # Configuración base de Alembic
        alembic_cfg = AlembicConfig("alembic.ini")

        for tenant in tenants:
            schema = tenant.schema_name
            click.secho(f"  -> 🔄 Sincronizando estructura para: {schema}", fg="blue")

            try:
                # 1. Traducimos las tablas al esquema del tenant
                tenant_engine = engine.execution_options(schema_translate_map={None: schema})

                # 2. 🌟 FIX CRÍTICO: Usamos TenantBase para imprimir las tablas de los clientes
                TenantBase.metadata.create_all(bind=tenant_engine)

                # 3. Forzamos a Alembic a sellar la versión en head
                alembic_command.stamp(alembic_cfg, "head")

                click.secho(f"  -> ✅ {schema} actualizado correctamente.", fg="green")
            except Exception as e:
                click.secho(f"  -> ❌ Fallo al migrar {schema}: {str(e)}", fg="red", err=True)
                continue

        click.secho("🎉 Proceso de migración masiva finalizado.", fg="green", bold=True)
    finally:
        db_session.close()

# ==========================================
# GRUPO: TENANTS (Espacios de Trabajo)
# ==========================================
@cli.group()
def tenant():
    """🏢 Comandos para gestionar Espacios de Trabajo (Tenants)."""
    pass

# Agregamos los subcomandos de tenant al grupo principal del CLI
cli.add_command(tenant)

@tenant.command("create")
@click.option('--name', required=True, prompt='Nombre de la Empresa', help='Nombre comercial del Tenant.')
@click.option('--cuit', required=True, prompt='CUIT (11 dígitos)', help='CUIT para facturación AFIP.')
@click.option('--schema', required=False, help='Nombre del esquema (Opcional).')
def create_tenant_cmd(name: str, cuit: str, schema: str):
    """Crea un nuevo Tenant y provisiona su infraestructura."""
    db: Session = SessionLocal()
    try:
        click.secho(f"🚀 Iniciando creación del Tenant: {name}", fg="cyan")
        nuevo_tenant = TenantManager.create_tenant(db, name, cuit, schema)
        click.secho(f"\n🎉 ¡Tenant '{nuevo_tenant.name}' (esquema: {nuevo_tenant.schema_name}) creado con éxito!\n", fg="green", bold=True)
    except ValueError as ve:
        click.secho(f"❌ Error de validación: {str(ve)}", fg="red")
        sys.exit(1)
    except Exception as e:
        click.secho(f"❌ Error crítico: {str(e)}", fg="red")
        sys.exit(1)
    finally:
        db.close()

@tenant.command("list")
def list_tenants_cmd():
    """Muestra todos los Tenants registrados."""
    db: Session = SessionLocal()
    try:
        tenants = TenantManager.list_tenants(db)
        if not tenants:
            click.secho("No hay Tenants registrados actualmente.", fg="yellow")
            return

        click.secho("\n📋 Listado de Tenants Activos:", fg="cyan", bold=True)
        click.secho(f"{'ID':<5} | {'ESQUEMA':<15} | {'CUIT':<15} | {'NOMBRE'}", fg="white", bold=True)
        click.secho("-" * 60, fg="white")

        for t in tenants:
            estado = "✅" if t.is_active else "❌"
            click.echo(f"{t.id:<5} | {t.schema_name:<15} | {t.cuit:<15} | {estado} {t.name}")
        click.echo("")
    finally:
        db.close()

@tenant.command("delete")
@click.argument('schema_name')
@click.option('--hard', is_flag=True, help='Borra permanentemente el esquema y los datos físicos.')
def delete_tenant_cmd(schema_name: str, hard: bool):
    """Da de baja un Tenant (Soft Delete por defecto)."""
    db: Session = SessionLocal()
    try:
        if hard:
            click.confirm(f"🔥 PELIGRO: Vas a DESTRUIR todos los datos físicos del esquema '{schema_name}'. ¿Continuar?", abort=True)
        else:
            click.confirm(f"⚠️ Vas a desactivar el esquema '{schema_name}'. ¿Continuar?", abort=True)

        TenantManager.deprovision_tenant(db, schema_name, hard_delete=hard)

        if hard:
            click.secho(f"\n💥 Tenant '{schema_name}' destruido.", fg="red")
        else:
            click.secho(f"\n✅ Tenant '{schema_name}' desactivado correctamente.", fg="green")

    except ValueError as ve:
        click.secho(f"❌ Error: {str(ve)}", fg="red")
    except Exception as e:
        click.secho(f"❌ Error al procesar la baja: {str(e)}", fg="red")
    finally:
        db.close()

# ==========================================
# GRUPO: SYSTEM (Sistema y Logs)
# ==========================================
@cli.group()
def system():
    """⚙️ Comandos de diagnóstico y salud del sistema."""
    pass

# Agregamos el subcomando al grupo principal
cli.add_command(system)

@system.command("logs")
@click.option('--limit', default=5, help='Cantidad de logs a mostrar.')
def show_logs(limit: int):
    """Muestra los últimos errores críticos del sistema."""
    db: Session = SessionLocal()
    try:
        logs = db.query(SystemLog).order_by(SystemLog.id.desc()).limit(limit).all()
        if not logs:
            click.secho("✅ El sistema está limpio. No hay errores registrados.", fg="green")
            return

        click.secho("\n🚨 Últimos Registros de Error (System Logs):", fg="red", bold=True)
        for log in logs:
            fecha = log.created_at.strftime("%Y-%m-%d %H:%M:%S") if log.created_at else "N/A"
            click.secho(f"[{fecha}] {log.level} | {log.module} | Ref: {log.tenant_reference}", fg="yellow", bold=True)
            click.echo(f"Mensaje: {log.message}")
            click.secho("-" * 60, fg="white")
    finally:
        db.close()

if __name__ == '__main__':
    cli()