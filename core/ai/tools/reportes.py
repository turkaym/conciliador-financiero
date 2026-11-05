import logging
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from sqlalchemy import text

from core.database.session import ai_readonly_session

logger = logging.getLogger("AI_TOOLS_REPORTES")

class ResumenImpositivoInput(BaseModel):
    mes: int = Field(..., description="Número del mes a consultar (1 al 12).")
    anio: int = Field(..., description="Año a consultar (ejemplo: 2026).")

@tool("calcular_resumen_iva", args_schema=ResumenImpositivoInput)
def tool_calcular_resumen_iva(mes: int, anio: int, config: RunnableConfig) -> str:
    """
    Calcula el resumen de IVA (Débito y Crédito Fiscal) y el saldo técnico para un mes específico.
    Úsala cuando el usuario pregunte por el saldo de IVA, los impuestos a pagar, o un reporte de IVA compras/ventas.
    """
    configurable = config.get("configurable", {})
    tenant_schema = configurable.get("tenant_schema")

    if not tenant_schema:
        return "ERROR INTERNO: Falta contexto de Tenant."

    try:
        with ai_readonly_session(tenant_schema) as db:
            # Agrupamos los comprobantes por tipo de operación para separar Débito de Crédito fiscal
            query_str = f"""
                SELECT
                    tipo_operacion,
                    COUNT(id) as cantidad_comprobantes,
                    SUM(importe_neto_gravado) as total_neto,
                    SUM(importe_iva) as total_iva,
                    SUM(importe_total) as total_bruto
                FROM "{tenant_schema}".comprobantes
                WHERE is_active = true
                  AND EXTRACT(MONTH FROM fecha_emision) = :mes
                  AND EXTRACT(YEAR FROM fecha_emision) = :anio
                  AND estado != 'ANULADA'
                GROUP BY tipo_operacion
            """

            result = db.execute(text(query_str), {"mes": mes, "anio": anio}).fetchall()

            if not result:
                return f"No hay comprobantes activos registrados en el período {mes}/{anio}."

            iva_ventas = 0.0  # Débito Fiscal
            iva_compras = 0.0 # Crédito Fiscal

            output = f"📊 RESUMEN IMPOSITIVO ({mes}/{anio}):\n\n"
            for row in result:
                if str(row.tipo_operacion).upper() == "VENTA":
                    iva_ventas = float(row.total_iva or 0)
                    output += f"▶ VENTAS (Débito Fiscal): {row.cantidad_comprobantes} comprobantes | Neto: ${row.total_neto or 0} | IVA: ${iva_ventas}\n"
                elif str(row.tipo_operacion).upper() == "COMPRA":
                    iva_compras = float(row.total_iva or 0)
                    output += f"▶ COMPRAS (Crédito Fiscal): {row.cantidad_comprobantes} comprobantes | Neto: ${row.total_neto or 0} | IVA: ${iva_compras}\n"

            saldo_tecnico = iva_ventas - iva_compras
            estado_saldo = "A PAGAR (Posición Deudora)" if saldo_tecnico > 0 else "A FAVOR (Posición Acreedora)"

            output += f"\n💡 SALDO TÉCNICO DE IVA PROYECTADO: ${abs(saldo_tecnico):.2f} -> {estado_saldo}"
            return output

    except Exception as e:
        logger.error(f"Fallo al calcular resumen de IVA: {e}", exc_info=True)
        return "ERROR AL CONSULTAR: El motor de base de datos rechazó la consulta de agrupación."