import logging
from sqlalchemy.orm import Session
from core.database.models_tenant import PlanCuentas
from core.database.models.tesoreria import CuentaTesoreria
from core.utils.enums import TipoCuentaTesoreria, MonedaISO
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("SEEDER")

# ==========================================
# CONSTANTES DE NEGOCIO (DATOS SEMILLA)
# ==========================================
PLAN_DE_CUENTAS_ARGENTINO = [
    {"codigo": "1", "nombre": "ACTIVO", "tipo": "ACTIVO", "imputable": False, "parent": None},
    {"codigo": "1.1", "nombre": "ACTIVO CORRIENTE", "tipo": "ACTIVO", "imputable": False, "parent": "1"},

    # Disponibilidades (Ancladas al sistema)
    {"codigo": "1.1.1", "nombre": "CAJA Y BANCOS", "tipo": "ACTIVO", "imputable": False, "parent": "1.1"},
    {"codigo": "1.1.1.01", "nombre": "Caja Fija", "tipo": "ACTIVO", "imputable": True, "parent": "1.1.1", "codigo_sistema": "CAJA_FIJA"},
    {"codigo": "1.1.1.02", "nombre": "Bancos Cuenta Corriente (ARS)", "tipo": "ACTIVO", "imputable": True, "parent": "1.1.1", "codigo_sistema": "BANCOS"},
    {"codigo": "1.1.1.03", "nombre": "Valores a Depositar", "tipo": "ACTIVO", "imputable": True, "parent": "1.1.1", "codigo_sistema": "VALORES_DEPOSITAR"},
    {"codigo": "1.1.1.04", "nombre": "Bancos Moneda Extranjera (USD)", "tipo": "ACTIVO", "imputable": True, "parent": "1.1.1", "codigo_sistema": "BANCOS_USD"},
    {"codigo": "1.1.1.05", "nombre": "Bancos Moneda Extranjera (EUR)", "tipo": "ACTIVO", "imputable": True, "parent": "1.1.1", "codigo_sistema": "BANCOS_EUR"},
    {"codigo": "1.1.1.06", "nombre": "Billeteras Virtuales", "tipo": "ACTIVO", "imputable": True, "parent": "1.1.1", "codigo_sistema": "BILLETERAS_VIRTUALES"},

    # Créditos
    {"codigo": "1.1.2", "nombre": "CRÉDITOS", "tipo": "ACTIVO", "imputable": False, "parent": "1.1"},
    {"codigo": "1.1.2.01", "nombre": "Deudores por Ventas", "tipo": "ACTIVO", "imputable": True, "parent": "1.1.2", "codigo_sistema": "CLIENTES"},
    {"codigo": "1.1.2.02", "nombre": "IVA Crédito Fiscal", "tipo": "ACTIVO", "imputable": True, "parent": "1.1.2", "codigo_sistema": "IVA_CREDITO"},
    {"codigo": "1.1.2.03", "nombre": "Retenciones Sufridas", "tipo": "ACTIVO", "imputable": True, "parent": "1.1.2", "codigo_sistema": "RETENCIONES_ACTIVO"},

    {"codigo": "2", "nombre": "PASIVO", "tipo": "PASIVO", "imputable": False, "parent": None},
    {"codigo": "2.1", "nombre": "PASIVO CORRIENTE", "tipo": "PASIVO", "imputable": False, "parent": "2"},

    # Deudas
    {"codigo": "2.1.1", "nombre": "DEUDAS COMERCIALES", "tipo": "PASIVO", "imputable": False, "parent": "2.1"},
    {"codigo": "2.1.1.01", "nombre": "Proveedores", "tipo": "PASIVO", "imputable": True, "parent": "2.1.1", "codigo_sistema": "PROVEEDORES"},
    {"codigo": "2.1.2", "nombre": "DEUDAS FISCALES", "tipo": "PASIVO", "imputable": False, "parent": "2.1"},
    {"codigo": "2.1.2.01", "nombre": "IVA Débito Fiscal", "tipo": "PASIVO", "imputable": True, "parent": "2.1.2", "codigo_sistema": "IVA_DEBITO"},
    {"codigo": "2.1.2.02", "nombre": "IVA Saldo a Pagar", "tipo": "PASIVO", "imputable": True, "parent": "2.1.2", "codigo_sistema": "IVA_PAGAR"},
    {"codigo": "2.1.2.03", "nombre": "Retenciones a Pagar", "tipo": "PASIVO", "imputable": True, "parent": "2.1.2", "codigo_sistema": "RETENCIONES_PASIVO"},

    {"codigo": "3", "nombre": "PATRIMONIO NETO", "tipo": "PATRIMONIO", "imputable": False, "parent": None},
    {"codigo": "3.1", "nombre": "CAPITAL", "tipo": "PATRIMONIO", "imputable": False, "parent": "3"},
    {"codigo": "3.1.1", "nombre": "Capital Social", "tipo": "PATRIMONIO", "imputable": True, "parent": "3.1"},
    {"codigo": "3.2", "nombre": "RESULTADOS", "tipo": "PATRIMONIO", "imputable": False, "parent": "3"},
    {"codigo": "3.2.1", "nombre": "Resultados Acumulados", "tipo": "PATRIMONIO", "imputable": True, "parent": "3.2"},

    {"codigo": "4", "nombre": "RESULTADOS POSITIVOS", "tipo": "INGRESO", "imputable": False, "parent": None},
    {"codigo": "4.1", "nombre": "INGRESOS OPERATIVOS", "tipo": "INGRESO", "imputable": False, "parent": "4"},
    {"codigo": "4.1.1", "nombre": "Ventas", "tipo": "INGRESO", "imputable": True, "parent": "4.1", "codigo_sistema": "VENTAS"},
    {"codigo": "4.2", "nombre": "OTROS INGRESOS", "tipo": "INGRESO", "imputable": False, "parent": "4"},
    {"codigo": "4.2.1", "nombre": "Diferencia de Cambio Positiva", "tipo": "INGRESO", "imputable": True, "parent": "4.2", "codigo_sistema": "DIF_CAMBIO_POS"},

    {"codigo": "5", "nombre": "RESULTADOS NEGATIVOS", "tipo": "EGRESO", "imputable": False, "parent": None},
    {"codigo": "5.1", "nombre": "EGRESOS OPERATIVOS", "tipo": "EGRESO", "imputable": False, "parent": "5"},
    {"codigo": "5.1.1", "nombre": "Costo de Mercadería Vendida (CMV)", "tipo": "EGRESO", "imputable": True, "parent": "5.1", "codigo_sistema": "CMV"},
    {"codigo": "5.1.2", "nombre": "Gastos Bancarios", "tipo": "EGRESO", "imputable": True, "parent": "5.1", "codigo_sistema": "GASTOS_BANCARIOS"},
    {"codigo": "5.1.3", "nombre": "Impuestos (IIBB)", "tipo": "EGRESO", "imputable": True, "parent": "5.1", "codigo_sistema": "IIBB"},
    {"codigo": "5.2", "nombre": "OTROS EGRESOS", "tipo": "EGRESO", "imputable": False, "parent": "5"},
    {"codigo": "5.2.1", "nombre": "Diferencia de Cambio Negativa", "tipo": "EGRESO", "imputable": True, "parent": "5.2", "codigo_sistema": "DIF_CAMBIO_NEG"},
]

class DataSeeder:
    @staticmethod
    def seed_tenant_defaults(db: Session, entidad_id: int = None):
        """Punto de entrada único e idempotente para datos de Tenant."""
        try:
            DataSeeder._seed_plan_cuentas(db)
            # 🌟 FIX FASE 12: Inyección de la Caja Principal
            if entidad_id:
                DataSeeder._seed_tesoreria_inicial(db, entidad_id)

            db.flush()
            logger.info("✅ Seeding de cortesía completado exitosamente.")
        except Exception as e:
            logger.error(f"❌ Fallo crítico en el proceso de Seeding: {str(e)}")
            raise e

    @staticmethod
    def _seed_plan_cuentas(db: Session):
        """
        Sincroniza el Plan de Cuentas usando 'codigo' como llave primaria de negocio.
        Implementa lógica de protección para no duplicar jerarquías.
        """
        logger.info("🌱 Sincronizando Plan de Cuentas Argentino...")

        # Mapa para reconstruir la jerarquía de IDs en tiempo real
        codigo_to_id = {}

        for item in PLAN_DE_CUENTAS_ARGENTINO:
            cuenta = db.query(PlanCuentas).filter_by(codigo=item["codigo"]).first()

            # 🌟 LOGICA NUEVA: Si tiene código de sistema, es inborrable
            es_cuenta_sistema = True if item.get("codigo_sistema") else False

            if cuenta:
                if item.get("codigo_sistema"):
                    cuenta.codigo_sistema = item["codigo_sistema"]
                cuenta.imputable = item["imputable"]
                cuenta.tipo = item["tipo"]
                cuenta.is_system = es_cuenta_sistema # Aseguramos el candado en cuentas viejas
            else:
                parent_id = codigo_to_id.get(item["parent"]) if item["parent"] else None

                cuenta = PlanCuentas(
                    codigo=item["codigo"],
                    nombre=item["nombre"],
                    tipo=item["tipo"],
                    imputable=item["imputable"],
                    parent_id=parent_id,
                    codigo_sistema=item.get("codigo_sistema"),
                    is_system=es_cuenta_sistema # Le ponemos el candado al nacer
                )
                db.add(cuenta)
                db.flush()

            codigo_to_id[item["codigo"]] = cuenta.id

        logger.info(f"📊 Plan de Cuentas: {len(PLAN_DE_CUENTAS_ARGENTINO)} cuentas procesadas.")

    @staticmethod
    def _seed_tesoreria_inicial(db: Session, entidad_id: int):
        """
        Aprovisiona la Caja Principal (Efectivo) para operaciones B2C por mostrador.
        Operación Idempotente.
        """
        logger.info("🏦 Aprovisionando Ecosistema de Tesorería...")

        caja_existente = db.query(CuentaTesoreria).filter(
            CuentaTesoreria.entidad_id == entidad_id,
            CuentaTesoreria.is_default_cash == True
        ).first()

        if not caja_existente:
            ahora = datetime.utcnow() - timedelta(hours=3)

            # Buscamos la cuenta contable ancla para Caja Fija
            cuenta_contable = db.query(PlanCuentas).filter_by(codigo_sistema="CAJA_FIJA").first()

            caja_principal = CuentaTesoreria(
                entidad_id=entidad_id,
                cuenta_contable_id=cuenta_contable.id if cuenta_contable else None,
                nombre="Caja Fuerte (Principal)",
                tipo_cuenta=TipoCuentaTesoreria.EFECTIVO.value if hasattr(TipoCuentaTesoreria.EFECTIVO, 'value') else "EFECTIVO",
                moneda=MonedaISO.ARS.value if hasattr(MonedaISO.ARS, 'value') else "ARS",
                is_default_cash=True,
                # 🌟 FIX: Forzamos los timestamps para evadir el paso de 'None' del Mixin
                created_at=ahora,
                updated_at=ahora
            )
            db.add(caja_principal)
            db.flush()
            logger.info("💵 Caja Fuerte Principal creada exitosamente.")