import logging
from typing import Optional
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from langchain_core.runnables import RunnableConfig
from sqlalchemy import text

from core.database.session import ai_readonly_session

logger = logging.getLogger("AI_TOOLS_CONSULTAS")

class ConsultaFinancieraInput(BaseModel):
    entidad_objetivo: str = Field(
        ...,
        description="Qué información querés consultar. Valores permitidos: 'COMPROBANTES', 'TESORERIA' (movimientos de caja/banco), 'ORDENES_PAGO', 'PROVEEDORES', 'CLIENTES'."
    )
    filtro_id: Optional[int] = Field(None, description="Si querés ver un registro específico, provee el ID interno.")
    filtro_cuit: Optional[str] = Field(None, description="Filtra resultados por el CUIT del cliente/proveedor (11 dígitos continuos).")
    limite: int = Field(5, description="Cantidad máxima de resultados a traer. Por defecto 5 para no saturar la memoria. Máximo 20.")

@tool("consultar_entidad_financiera", args_schema=ConsultaFinancieraInput)
def tool_consultar_entidad_financiera(
    entidad_objetivo: str,
    filtro_id: Optional[int],
    filtro_cuit: Optional[str],
    limite: int,
    config: RunnableConfig
) -> str:
    """
    Herramienta Analítica (Modo Lectura Segura).
    Permite consultar el estado real en la base de datos de Comprobantes, Movimientos de Tesorería, Órdenes de Pago o Perfiles Comerciales.
    Úsala para responder preguntas como: "¿En qué estado quedó la factura X?", "¿Cuáles son los últimos pagos?", o "¿Cuánto nos debe el CUIT Y?".
    """
    configurable = config.get("configurable", {})
    tenant_schema = configurable.get("tenant_schema")

    if not tenant_schema:
        return "ERROR INTERNO: Falta contexto de Tenant para ejecutar la consulta."

    limite = min(limite, 20)
    entidad = entidad_objetivo.upper()

    try:
        with ai_readonly_session(tenant_schema) as db:

            if entidad == "COMPROBANTES":
                # 🌟 FIX DEUDA TÉCNICA: Cruce relacional correcto mediante LEFT JOIN para obtener la razón social.
                query_str = f"""
                    SELECT c.id, c.clase_documento, c.numero, c.estado, c.fecha_emision,
                           c.cuit_receptor, COALESCE(cc.razon_social, 'S/D') as razon_social_tercero,
                           c.importe_total, c.saldo_pendiente, c.comprobante_origen_id
                    FROM "{tenant_schema}".comprobantes c
                    LEFT JOIN "{tenant_schema}".contactos_comerciales cc ON c.cuit_receptor = cc.cuit
                    WHERE c.is_active = true
                """
                params = {}
                if filtro_id:
                    query_str += " AND c.id = :id"
                    params["id"] = filtro_id
                if filtro_cuit:
                    # Buscamos de ambos lados por si fue una venta o una compra
                    query_str += " AND (c.cuit_receptor = :cuit OR c.cuit_emisor = :cuit)"
                    params["cuit"] = filtro_cuit

                query_str += " ORDER BY c.fecha_emision DESC, c.id DESC LIMIT :limit"
                params["limit"] = limite

                result = db.execute(text(query_str), params).fetchall()
                if not result: return "No se encontraron comprobantes con esos filtros."

                output = "COMPROBANTES ENCONTRADOS:\n"
                for row in result:
                    origen = f" (Derivado de ID: {row.comprobante_origen_id})" if row.comprobante_origen_id else ""
                    output += f"- ID {row.id}: {row.clase_documento} N° {row.numero} | Estado: {row.estado} | Fecha: {row.fecha_emision} | CUIT: {row.cuit_receptor} ({row.razon_social_tercero}) | Total: ${row.importe_total} | Saldo a cobrar: ${row.saldo_pendiente}{origen}\n"
                return output

            elif entidad == "TESORERIA":
                query_str = f"""
                    SELECT m.id, c.nombre as caja, m.tipo, m.monto, m.concepto_crudo, m.fecha, m.saldo_resultante
                    FROM "{tenant_schema}".movimientos_tesoreria m
                    JOIN "{tenant_schema}".cuentas_tesoreria c ON m.cuenta_id = c.id
                    WHERE m.anulado = false
                """
                params = {}
                if filtro_id:
                    query_str += " AND m.id = :id"
                    params["id"] = filtro_id

                query_str += " ORDER BY m.fecha DESC, m.id DESC LIMIT :limit"
                params["limit"] = limite

                result = db.execute(text(query_str), params).fetchall()
                if not result: return "No se encontraron movimientos de tesorería."

                output = "ÚLTIMOS MOVIMIENTOS DE CAJA/BANCO:\n"
                for row in result:
                    output += f"- Mov. {row.id} ({row.caja}): {row.tipo} de ${row.monto} | Concepto: {row.concepto_crudo} | Saldo final cuenta: ${row.saldo_resultante} | Fecha: {row.fecha}\n"
                return output

            elif entidad == "ORDENES_PAGO":
                query_str = f"""
                    SELECT o.id, p.razon_social, o.estado, o.monto_total, o.fecha_emision
                    FROM "{tenant_schema}".ordenes_pago o
                    JOIN "{tenant_schema}".contactos_comerciales p ON o.proveedor_id = p.id
                    WHERE o.is_active = true
                """
                params = {}
                if filtro_id:
                    query_str += " AND o.id = :id"
                    params["id"] = filtro_id
                if filtro_cuit:
                    query_str += " AND p.cuit = :cuit"
                    params["cuit"] = filtro_cuit

                query_str += " ORDER BY o.fecha_emision DESC, o.id DESC LIMIT :limit"
                params["limit"] = limite

                result = db.execute(text(query_str), params).fetchall()
                if not result: return "No se encontraron Órdenes de Pago."

                output = "ÓRDENES DE PAGO:\n"
                for row in result:
                    output += f"- OP {row.id}: Proveedor: {row.razon_social} | Estado: {row.estado} | Monto: ${row.monto_total} | Fecha: {row.fecha_emision}\n"
                return output

            elif entidad in ["PROVEEDORES", "CLIENTES"]:
                query_str = f"""
                    SELECT id, razon_social, cuit, condicion_fiscal, is_cliente, is_proveedor
                    FROM "{tenant_schema}".contactos_comerciales
                    WHERE is_active = true
                """
                params = {}
                if filtro_cuit:
                    query_str += " AND cuit = :cuit"
                    params["cuit"] = filtro_cuit
                else:
                    filtro_tipo = "is_cliente = true" if entidad == "CLIENTES" else "is_proveedor = true"
                    query_str += f" AND {filtro_tipo}"

                query_str += " LIMIT :limit"
                params["limit"] = limite

                result = db.execute(text(query_str), params).fetchall()
                if not result: return f"No se encontraron perfiles comerciales para la búsqueda."

                output = "PERFILES ENCONTRADOS:\n"
                for row in result:
                    roles = []
                    if row.is_cliente: roles.append("Cliente")
                    if row.is_proveedor: roles.append("Proveedor")
                    str_roles = " y ".join(roles)
                    output += f"- ID {row.id}: {row.razon_social} | CUIT: {row.cuit} | Fiscal: {row.condicion_fiscal} | Rol: {str_roles}\n"
                return output

            else:
                return f"Entidad '{entidad}' no soportada por la herramienta analítica."

    except Exception as e:
        logger.error(f"Fallo en consulta analítica: {e}", exc_info=True)
        return f"ERROR AL CONSULTAR: El motor de base de datos rechazó la consulta analítica."