import logging
import itertools
import time
import hashlib
from datetime import date
from typing import Optional, Dict, Tuple, Callable, Any
from decimal import Decimal
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import func

from core.database.models_tenant import CuentaBancaria, MovimientoBancario, ContactoComercial, Comprobante
from core.database.models.tesoreria import CuentaTesoreria, MovimientoTesoreria
from core.parsers.bancos.factory import BancosFactory
import core.utils.enums as enums

logger = logging.getLogger("BANK_INGEST")
logger.setLevel(logging.INFO)

def ingest_file(
    db: Session,
    file_stream: Any,
    file_extension: str,
    parser_code: str,
    cuenta_id: int,
    entidad_id: int,
    cuenta_contable_id: int,
    progress_cb: Optional[Callable[[int, str], None]] = None,
    column_mapping: Optional[Dict[str, int]] = None
) -> dict:
    logger.info(f"📂 Iniciando flujo Zero-Disk con parser {parser_code} para Cuenta {cuenta_id}")

    # =================================================================
    # 🌟 FIX FASE 12: Detección Polimórfica (Strangler Fig Pattern)
    # =================================================================
    is_tesoreria = False

    # 1. Buscamos en el nuevo Ecosistema B2C/Clearing
    cuenta = db.query(CuentaTesoreria).filter(
        CuentaTesoreria.id == cuenta_id, CuentaTesoreria.entidad_id == entidad_id
    ).first()

    if cuenta:
        is_tesoreria = True
        TargetModel = MovimientoTesoreria
        # 🌟 FIX DEUDA TECNICA: Obtenemos la cuenta CON su proveedor en un solo viaje
        cuenta = db.query(CuentaTesoreria).options(joinedload(CuentaTesoreria.proveedor_clearing)).filter(
            CuentaTesoreria.id == cuenta_id, CuentaTesoreria.entidad_id == entidad_id
        ).first()
    else:
        # 2. Fallback a Bancos Legacy
        cuenta = db.query(CuentaBancaria).options(joinedload(CuentaBancaria.proveedor_clearing)).filter(
            CuentaBancaria.id == cuenta_id, CuentaBancaria.entidad_id == entidad_id
        ).first()
        TargetModel = MovimientoBancario

    if not cuenta:
        raise ValueError("La cuenta bancaria o de tesorería no existe o no pertenece a esta entidad.")

    parser = BancosFactory.get_parser(
        parser_code,
        cuenta_id=cuenta_id,
        cuenta_contable_id=cuenta_contable_id,
        column_mapping=column_mapping,
        file_extension=file_extension
    )

    # =================================================================
    # 🌟 FIX DEUDA TECNICA: Auto-Emisión Fiscal Dinámica (Sin Hardcoding)
    # =================================================================
    cuit_procesadora = None
    if cuenta.proveedor_clearing and cuenta.is_virtual_clearing:
        cuit_procesadora = cuenta.proveedor_clearing.cuit
        is_clearing_parser = True
        logger.info(f"Auto-Emisión habilitada. Proveedor asociado: {cuenta.proveedor_clearing.razon_social} (CUIT: {cuit_procesadora})")
    else:
        is_clearing_parser = False
        logger.info("Auto-Emisión deshabilitada. La cuenta no tiene un proveedor_clearing asociado.")


    total_estimado = 1000
    try:
        if hasattr(file_stream, 'headers'):
            size_bytes = int(file_stream.headers.get('Content-Length', 100000))
            if file_extension in ['.csv', '.txt']:
                total_estimado = max(1, size_bytes // 120)
            else:
                total_estimado = max(1, size_bytes // 50)
    except Exception as e:
        logger.warning(f"No se pudo estimar tamaño exacto del stream, usando default: {e}")

    chunk_size = 5000
    insertados_totales = 0
    procesados_totales = 0
    ultimo_saldo_detectado: Optional[Decimal] = None

    last_sse_time = 0.0

    # Aquí ocurre el "Desempaquetado" en RAM
    movement_generator = parser.parse_generator(file_stream)

    # 🌟 FIX AMNESIA: El estado debe persistir durante TODA la lectura del archivo
    conteo_local = {}

    while True:
        batch = list(itertools.islice(movement_generator, chunk_size))
        if not batch:
            break

        movs_dicts = []

        for i, mov in enumerate(batch):
            # 🌟 FIX TRUNCAMIENTO: Mantenemos el concepto original para cálculos criptográficos
            concepto_original = mov.concepto.strip() if mov.concepto and str(mov.concepto).strip() else "MOVIMIENTO SIN DESCRIPCION"

            # Recorte seguro exclusivo para el motor de base de datos (límite de columna VARCHAR)
            safe_concepto_db = concepto_original[:255]
            safe_ref = mov.referencia_banco.strip()[:100] if mov.referencia_banco else None

            # En Tesorería el monto es siempre absoluto. Para la idempotencia debemos estandarizarlo.
            monto_para_hash = abs(mov.monto) if is_tesoreria else mov.monto

            # 🌟 FIX IDEMPOTENCIA: El hash DEBE ser inmutable y usar la cadena ORIGINAL sin recortar
            base_key = f"{mov.fecha}_{concepto_original.upper()}_{monto_para_hash:.2f}"
            conteo_local[base_key] = conteo_local.get(base_key, 0) + 1

            mov.ocurrencia_diaria = conteo_local[base_key]
            mov.concepto = safe_concepto_db

            # 🌟 FIX COLISIÓN: Inyectamos el cuenta_id en la semilla para aislar sucursales y terminales
            raw_hash_seed = f"CTA{cuenta_id}_{mov.fecha}_{concepto_original.upper()}_{monto_para_hash:.2f}_{mov.ocurrencia_diaria}"
            mov.hash_transaccional = hashlib.sha256(raw_hash_seed.encode('utf-8')).hexdigest()

            # Adaptador Estructural DDL (Restaurado)
            if is_tesoreria:
                monto_absoluto = abs(mov.monto)
                movs_dicts.append({
                    "cuenta_id": cuenta_id,
                    "hash_transaccional": mov.hash_transaccional,
                    "referencia_externa": safe_ref,
                    "fecha": mov.fecha,
                    "concepto_crudo": safe_concepto_db,
                    "tipo": "INGRESO" if mov.monto >= 0 else "EGRESO",
                    "monto": monto_absoluto, # Tesorería requiere monto absoluto
                    "saldo_pendiente": monto_absoluto,
                    "saldo_resultante": mov.saldo_resultante
                })
            else:
                movs_dicts.append({
                    "cuenta_id": cuenta_id,
                    "hash_transaccional": mov.hash_transaccional,
                    "referencia_banco": safe_ref,
                    "fecha": mov.fecha,
                    "concepto_bancario_crudo": safe_concepto_db,
                    "monto": mov.monto,
                    "saldo_pendiente": mov.monto,
                    "saldo_resultante": mov.saldo_resultante
                })

            if not is_tesoreria and mov.saldo_resultante is not None:
                ultimo_saldo_detectado = mov.saldo_resultante

            if progress_cb:
                current_time = time.time()
                if current_time - last_sse_time >= 0.5:
                    avance_actual = procesados_totales + i
                    porcentaje = min(int((avance_actual / total_estimado) * 100), 99)
                    progress_cb(porcentaje, f"Desempaquetando: {avance_actual} registros...")
                    last_sse_time = current_time

        procesados_totales += len(batch)
        movs_dicts.sort(key=lambda x: x['hash_transaccional'])

        # Validación de seguridad: no ejecutar si el bloque está vacío
        inserted_rows = []
        if movs_dicts:
            stmt = insert(TargetModel).values(movs_dicts)
            stmt = stmt.on_conflict_do_nothing(index_elements=['cuenta_id', 'hash_transaccional'])

            # 🌟 FIX IDEMPOTENCIA: Extraemos únicamente los registros que superaron la restricción de unicidad
            if is_tesoreria:
                stmt = stmt.returning(TargetModel.id, TargetModel.fecha, TargetModel.concepto_crudo, TargetModel.monto, TargetModel.tipo)
            else:
                stmt = stmt.returning(TargetModel.id, TargetModel.fecha, TargetModel.concepto_bancario_crudo, TargetModel.monto)

            result = db.execute(stmt)
            inserted_rows = result.fetchall()
            insertados_totales += len(inserted_rows)

        db.flush()
        logger.info(f"🌊 Chunk Polimórfico de {len(batch)} procesado. RAM liberada.")

        # =================================================================
        # 🌟 FIX FASE 13.2: Auto-Emisión Fiscal (Secuencia Nativa de Tenant)
        # =================================================================
        if is_clearing_parser and is_tesoreria and inserted_rows:
            comprobantes_a_emitir = []

            for row in inserted_rows:
                tipo_mov = str(row.tipo).upper()
                concepto_crudo = str(row.concepto_crudo).upper()

                if "EGRESO" in tipo_mov and ("COMISION" in concepto_crudo or "RETENCION" in concepto_crudo):
                    monto_absoluto = Decimal(str(row.monto))

                    nuevo_cbte = Comprobante(
                        entidad_id=entidad_id,
                        clase_documento=enums.ClaseDocumento.FACTURA.name if hasattr(enums.ClaseDocumento.FACTURA, 'name') else "FACTURA",
                        tipo_operacion="COMPRA",
                        estado="PAGADA",
                        fecha_emision=row.fecha,
                        punto_venta=9000,
                        # 🌟 FIX DEFINITIVO: Generación atómica delegada a PostgreSQL.
                        # Como la sesión de SQLAlchemy ya tiene seteado el search_path del tenant, no colisionan.
                        numero=func.nextval('clearing_cbte_seq'),
                        cuit_emisor=cuit_procesadora,
                        cuit_receptor="00000000000",
                        importe_neto_gravado=Decimal("0.0"),
                        importe_no_gravado=monto_absoluto,
                        importe_exento=Decimal("0.0"),
                        importe_neto=Decimal("0.0"),
                        importe_iva=Decimal("0.0"),
                        importe_tributos=Decimal("0.0"),
                        importe_total=monto_absoluto,
                        moneda="ARS",
                        saldo_pendiente=Decimal("0.0")
                    )
                    comprobantes_a_emitir.append(nuevo_cbte)

            if comprobantes_a_emitir:
                db.add_all(comprobantes_a_emitir)
                db.flush()
                logger.info(f"🧾 Auto-Emisión Fiscal: {len(comprobantes_a_emitir)} facturas generadas nativamente vía secuencia.")

        if progress_cb:
            porcentaje = min(int((procesados_totales / total_estimado) * 100), 99)
            progress_cb(porcentaje, f"Volcando {len(batch)} registros a disco...")

    if not is_tesoreria and ultimo_saldo_detectado is not None:
        cuenta.saldo_actual = ultimo_saldo_detectado

    db.commit()

    if progress_cb:
        progress_cb(100, "Consolidando Clearing Sintético...")

    logger.info(f"✅ Ingesta finalizada. Insertados: {insertados_totales}, Omitidos: {procesados_totales - insertados_totales}")

    return {
        "status": "success",
        "procesados": procesados_totales,
        "insertados": insertados_totales,
        "omitidos": procesados_totales - insertados_totales
    }