import hashlib
import uuid
import logging
from datetime import date
from decimal import Decimal

# 🌟 FIX PEP 8: Centralización de Excepciones SQLAlchemy
from sqlalchemy import union_all, literal_column, desc
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from core.database.models.contabilidad import AsientoContable, LineaAsiento
from core.database.models_tenant import PlanCuentas
from core.database.models.tesoreria import CuentaTesoreria, MovimientoTesoreria, SolicitudMovimientoTesoreria
from core.schemas.banco import CuentaBancariaCreate, MovimientoBancarioCreate
from core.services.periodo_service import periodo_service
from core.services.trazabilidad_service import trazabilidad_service
from core.utils.enums import TipoComprobanteInterno
from core.api.deps import redis_client

logger = logging.getLogger("API_BANCOS")

class BancoService:

    def obtener_cuentas(self, db: Session, entidad_id: int):
        cajas_nuevas = db.query(CuentaTesoreria).filter(
            CuentaTesoreria.entidad_id == entidad_id,
            CuentaTesoreria.is_active == True
        ).all()

        cajas_adaptadas = []
        for caja in cajas_nuevas:
            tipo_real = caja.tipo_cuenta.value if hasattr(caja.tipo_cuenta, 'value') else str(caja.tipo_cuenta)
            canal_inferido = 'PASARELA' if tipo_real in ['BILLETERA_VIRTUAL', 'CLEARING_VIRTUAL'] else 'BANCO'

            if tipo_real == "BANCO":
                 tipo_real = "CC_USD" if "USD" in str(caja.moneda) else "CC_ARS"

            banco_limpio = str(caja.nombre)

            caja_mock = {
                'id': caja.id,
                'banco': banco_limpio,
                'numero_cuenta': caja.numero_cuenta or "S/N",
                'cbu': caja.cbu_cvu,
                'alias': caja.alias,
                'tipo_cuenta': tipo_real,
                'moneda': caja.moneda.value if hasattr(caja.moneda, 'value') else str(caja.moneda),
                'saldo_actual': caja.saldo_actual,
                'saldo_retenido': getattr(caja, 'saldo_retenido', 0.0),
                'is_active': caja.is_active,
                'is_syncing': getattr(caja, 'is_syncing', False),
                'last_task_id': getattr(caja, 'last_task_id', None),
                'is_virtual_clearing': getattr(caja, 'is_virtual_clearing', False),
                'tipo_canal': canal_inferido,
                'proveedor_clearing_id': getattr(caja, 'proveedor_clearing_id', None),
                'cuenta_contable_id': getattr(caja, 'cuenta_contable_id', None),
                'progress': None,
                'status_msg': None
            }
            cajas_adaptadas.append(caja_mock)

        return cajas_adaptadas

    def crear_cuenta(self, db: Session, cuenta_in: CuentaBancariaCreate, user_id: int):
        banco_str = cuenta_in.banco.value if hasattr(cuenta_in.banco, 'value') else str(cuenta_in.banco)
        moneda_str = cuenta_in.moneda.value if hasattr(cuenta_in.moneda, 'value') else str(cuenta_in.moneda)

        canal_frontend = cuenta_in.tipo_canal.value if hasattr(cuenta_in.tipo_canal, 'value') else str(cuenta_in.tipo_canal)
        tipo_db = "BILLETERA_VIRTUAL" if canal_frontend == "PASARELA" else "BANCO"
        saldo_inicial = getattr(cuenta_in, 'saldo_actual', 0.0)

        # 🌟 FIX ARQUITECTURA: Mapeo inteligente de cuenta contable con fallback
        cuenta_contable_id = getattr(cuenta_in, 'cuenta_contable_id', None)

        if not cuenta_contable_id:
            codigo_inferido = "BANCOS"
            if canal_frontend == "PASARELA":
                codigo_inferido = "BILLETERAS_VIRTUALES"
            elif moneda_str != "ARS":
                codigo_inferido = f"BANCOS_{moneda_str}"

            cuenta_contable = db.query(PlanCuentas).filter(
                PlanCuentas.codigo_sistema == codigo_inferido
            ).first()

            # Fallback estricto a la cuenta ancla del sistema
            if not cuenta_contable:
                cuenta_contable = db.query(PlanCuentas).filter(PlanCuentas.codigo_sistema == "BANCOS").first()

            if not cuenta_contable:
                raise ValueError("Rotura de Configuración: No existe la cuenta contable ancla 'BANCOS' en el plan de cuentas.")

            cuenta_contable_id = cuenta_contable.id

        nueva_caja = CuentaTesoreria(
            entidad_id=cuenta_in.entidad_id,
            cuenta_contable_id=cuenta_contable_id,
            nombre=banco_str,
            tipo_cuenta=tipo_db,
            moneda=moneda_str,
            cbu_cvu=cuenta_in.cbu,
            alias=cuenta_in.alias,
            numero_cuenta=cuenta_in.numero_cuenta,
            saldo_actual=saldo_inicial,
            is_active=True,
            is_virtual_clearing=getattr(cuenta_in, 'is_virtual_clearing', False)
        )

        db.add(nueva_caja)
        try:
            db.commit()
            db.refresh(nueva_caja)
        # 🌟 FIX DEUDA TÉCNICA: Captura de clase estricta y eliminación del Except genérico
        except IntegrityError as e:
            db.rollback()
            logger.error(f"Fallo de integridad persistiendo cuenta en Tesorería: {e}")
            raise ValueError("Error de integridad de datos al unificar la cuenta bancaria en tesorería.")
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Fallo de base de datos no esperado: {e}")
            raise ValueError("Fallo sistémico al crear la cuenta bancaria.")

        tipo_frontend = cuenta_in.tipo_cuenta.value if hasattr(cuenta_in.tipo_cuenta, 'value') else str(cuenta_in.tipo_cuenta)

        cuenta_mock = {
            "id": nueva_caja.id,
            "entidad_id": nueva_caja.entidad_id,
            "banco": banco_str,
            "numero_cuenta": nueva_caja.numero_cuenta or "S/N",
            "cbu": nueva_caja.cbu_cvu,
            "alias": nueva_caja.alias,
            "tipo_cuenta": tipo_frontend,
            "moneda": moneda_str,
            "saldo_actual": saldo_inicial,
            "saldo_retenido": 0.0,
            "is_active": True,
            "is_syncing": False,
            "is_virtual_clearing": nueva_caja.is_virtual_clearing,
            "last_task_id": None,
            "tipo_canal": canal_frontend,
            "cuenta_contable_id": nueva_caja.cuenta_contable_id
        }

        return cuenta_mock

    def registrar_movimiento_con_saldo(
        self,
        db: Session,
        mov_in: MovimientoBancarioCreate,
        entidad_id: int,
        user_id: int,
        user_role: str = "operator",
        umbral_aprobacion: float = 0.0
    ):
        if redis_client:
            lock_key = f"idempotency:mov:{mov_in.cuenta_id}:{mov_in.monto:.2f}:{mov_in.fecha}"
            if not redis_client.set(lock_key, "locked", nx=True, ex=3):
                raise ValueError("Transacción en proceso. Aguarde un instante para evitar duplicados.")

        periodo_service.validar_fecha_operacion(db, mov_in.fecha)

        cuenta = db.query(CuentaTesoreria).filter(
            CuentaTesoreria.id == mov_in.cuenta_id,
            CuentaTesoreria.entidad_id == entidad_id,
            CuentaTesoreria.is_active == True
        ).with_for_update().first()

        if not cuenta:
            raise PermissionError("Cuenta de Tesorería no encontrada o no pertenece a la entidad activa.")

        mov_dict = mov_in.model_dump()

        if "concepto" in mov_dict:
            mov_dict["concepto_crudo"] = mov_dict.pop("concepto")

        concepto_safe = mov_dict.get("concepto_crudo", "MOVIMIENTO MANUAL")
        ref_banco = mov_in.referencia_banco

        if not ref_banco or not str(ref_banco).strip():
            ref_banco = trazabilidad_service.generar_trace_id(
                db=db, tenant_id=entidad_id, tipo_cbte_interno=TipoComprobanteInterno.MOVIMIENTO_MANUAL, prefijo="MAN"
            )

        raw_hash = f"{mov_in.fecha}_{concepto_safe}_{mov_in.monto:.2f}_{cuenta.id}_{ref_banco}"
        hash_final = hashlib.sha256(raw_hash.encode('utf-8')).hexdigest()

        monto_transaccion = Decimal(str(mov_in.monto))
        monto_absoluto = abs(monto_transaccion)
        es_egreso = monto_transaccion < 0
        tipo_mov = "INGRESO" if monto_transaccion >= 0 else "EGRESO"

        saldo_actual_dec = Decimal(str(cuenta.saldo_actual))
        saldo_retenido_dec = Decimal(str(getattr(cuenta, 'saldo_retenido', 0.0)))
        saldo_disponible = saldo_actual_dec - saldo_retenido_dec

        requiere_aprobacion = (umbral_aprobacion > 0) and (monto_absoluto >= Decimal(str(umbral_aprobacion))) and (user_role != "admin" and user_role != "dueño")

        if es_egreso and monto_absoluto > saldo_disponible:
            raise ValueError(f"Fondos insuficientes. Saldo disponible: ${saldo_disponible:.2f}")

        try:
            if requiere_aprobacion:
                if es_egreso:
                    cuenta.saldo_retenido = saldo_retenido_dec + monto_absoluto

                nueva_solicitud = SolicitudMovimientoTesoreria(
                    cuenta_id=cuenta.id, tipo=tipo_mov, fecha=mov_in.fecha, monto=monto_absoluto,
                    moneda=cuenta.moneda, concepto_crudo=concepto_safe, referencia_externa=ref_banco,
                    hash_transaccional=hash_final, estado="PENDING_APPROVAL"
                )
                db.add(nueva_solicitud)
                db.add(cuenta)
                db.commit()
                db.refresh(nueva_solicitud)

                setattr(nueva_solicitud, "concepto_bancario_crudo", nueva_solicitud.concepto_crudo)
                setattr(nueva_solicitud, "referencia_banco", nueva_solicitud.referencia_externa)
                return nueva_solicitud

            else:
                nuevo_saldo_exacto = saldo_actual_dec + monto_transaccion
                cuenta.saldo_actual = nuevo_saldo_exacto

                nuevo_movimiento = MovimientoTesoreria(
                    cuenta_id=cuenta.id, tipo=tipo_mov, fecha=mov_in.fecha, monto=monto_absoluto,
                    moneda=cuenta.moneda, saldo_resultante=nuevo_saldo_exacto, concepto_crudo=concepto_safe,
                    referencia_externa=ref_banco, hash_transaccional=hash_final, comprobante_id=None
                )
                db.add(nuevo_movimiento)
                db.add(cuenta)
                db.flush()

                if mov_in.cuenta_contable_id:
                    cuenta_origen_contable_id = cuenta.cuenta_contable_id

                    if not cuenta_origen_contable_id:
                        raise ValueError(f"Rotura de Configuración: La caja '{cuenta.nombre}' no tiene una cuenta contable asociada para la Partida Doble.")

                    nuevo_asiento = AsientoContable(
                        fecha=mov_in.fecha,
                        concepto=f"{tipo_mov} Directo | Ref: {ref_banco} | Caja ID: {cuenta.id}"
                    )
                    db.add(nuevo_asiento)
                    db.flush()

                    if es_egreso:
                        linea_debe = LineaAsiento(asiento_id=nuevo_asiento.id, cuenta_id=mov_in.cuenta_contable_id, debe=monto_absoluto, haber=0)
                        linea_haber = LineaAsiento(asiento_id=nuevo_asiento.id, cuenta_id=cuenta_origen_contable_id, debe=0, haber=monto_absoluto)
                    else:
                        linea_debe = LineaAsiento(asiento_id=nuevo_asiento.id, cuenta_id=cuenta_origen_contable_id, debe=monto_absoluto, haber=0)
                        linea_haber = LineaAsiento(asiento_id=nuevo_asiento.id, cuenta_id=mov_in.cuenta_contable_id, debe=0, haber=monto_absoluto)

                    db.add_all([linea_debe, linea_haber])
                    nuevo_movimiento.asiento_id = nuevo_asiento.id

                db.commit()
                db.refresh(nuevo_movimiento)

                setattr(nuevo_movimiento, "concepto_bancario_crudo", nuevo_movimiento.concepto_crudo)
                setattr(nuevo_movimiento, "referencia_banco", nuevo_movimiento.referencia_externa)
                setattr(nuevo_movimiento, "estado", "APROBADO")
                return nuevo_movimiento

        # 🌟 FIX DEUDA TÉCNICA: Captura explícita de IntegrityError evadiendo parsing de strings
        except IntegrityError:
            db.rollback()
            raise ValueError("Esta transacción ya fue registrada previamente en la base de datos (Colisión de Integridad).")
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Error relacional en tesorería: {e}")
            raise e

    def obtener_extracto_inteligente(self, db: Session, cuenta_id: int, skip: int, limit: int, entidad_id: int):

        cuenta = db.query(CuentaTesoreria).filter(
            CuentaTesoreria.id == cuenta_id, CuentaTesoreria.entidad_id == entidad_id
        ).first()

        if not cuenta:
            raise PermissionError("Acceso denegado. La cuenta no existe en Tesorería.")

        query_movimientos = db.query(
            MovimientoTesoreria.id.label('id_original'),
            literal_column("'MOVIMIENTO'").label('tipo_registro'),
            MovimientoTesoreria.fecha.label('fecha'),
            MovimientoTesoreria.monto.label('monto'),
            MovimientoTesoreria.tipo.label('tipo'),
            MovimientoTesoreria.moneda.label('moneda'),
            MovimientoTesoreria.concepto_crudo.label('concepto_crudo'),
            MovimientoTesoreria.referencia_externa.label('referencia_externa'),
            literal_column("NULL").label('creado_por_id'),
            MovimientoTesoreria.comprobante_id.label('comprobante_id'),
            MovimientoTesoreria.anulado.label('anulado')
        ).filter(MovimientoTesoreria.cuenta_id == cuenta_id)

        query_solicitudes = db.query(
            SolicitudMovimientoTesoreria.id.label('id_original'),
            literal_column("'SOLICITUD'").label('tipo_registro'),
            SolicitudMovimientoTesoreria.fecha.label('fecha'),
            SolicitudMovimientoTesoreria.monto.label('monto'),
            SolicitudMovimientoTesoreria.tipo.label('tipo'),
            SolicitudMovimientoTesoreria.moneda.label('moneda'),
            SolicitudMovimientoTesoreria.concepto_crudo.label('concepto_crudo'),
            SolicitudMovimientoTesoreria.referencia_externa.label('referencia_externa'),
            literal_column("NULL").label('creado_por_id'),
            literal_column("NULL").label('comprobante_id'),
            literal_column("FALSE").label('anulado')
        ).filter(
            SolicitudMovimientoTesoreria.cuenta_id == cuenta_id,
            SolicitudMovimientoTesoreria.movimiento_definitivo_id == None
        )

        extracto_unificado = union_all(query_movimientos, query_solicitudes).alias('extracto')
        total_count = db.query(extracto_unificado).count()

        resultados_crudos = db.query(extracto_unificado).order_by(
            desc(extracto_unificado.c.fecha),
            desc(extracto_unificado.c.id_original)
        ).offset(skip).limit(limit).all()

        movimientos = []
        for row in resultados_crudos:
            row_map = row._mapping if hasattr(row, '_mapping') else row

            tipo_registro = row_map['tipo_registro']
            id_original = int(row_map['id_original'])

            monto_final = row_map['monto'] if row_map['tipo'] == "INGRESO" else -row_map['monto']

            if tipo_registro == 'SOLICITUD':
                estado_real = "PENDING_APPROVAL"
            elif row_map['comprobante_id'] is not None:
                estado_real = "CONCILIADO"
            elif row_map['anulado']:
                estado_real = "ANULADO"
            else:
                estado_real = "APROBADO"

            creador = "Sistema" if not row_map['creado_por_id'] else str(row_map['creado_por_id'])
            if tipo_registro == 'MOVIMIENTO':
                creador_nombre = "Operador Interno" if "MAN-" in str(row_map['referencia_externa'] or "") else "Motor de Extracción"
            else:
                creador_nombre = "Operador"

            mov_mock = {
                'id': id_original,
                'cuenta_id': cuenta_id,
                'fecha': row_map['fecha'],
                'monto': monto_final,
                'moneda': row_map['moneda'],
                'concepto_bancario_crudo': row_map['concepto_crudo'] or "SIN CONCEPTO",
                'hash_transaccional': "",
                'referencia_banco': row_map['referencia_externa'] or "",
                'usuario_creador_id': creador,
                'estado': estado_real,
                'ocurrencia_diaria': 1,
                'usuario_creador_nombre': creador_nombre,
                'usuario_resolutor_nombre': None,
                'tipo_registro': tipo_registro,
                'motivo_rechazo': None
            }
            movimientos.append(mov_mock)

        page = skip // limit if limit > 0 else 0
        has_more = (skip + limit) < total_count

        return {
            "items": movimientos,
            "total_count": total_count,
            "page": page,
            "has_more": has_more
        }

    def resolver_aprobacion_movimiento(
        self,
        db: Session,
        registro_id: int,
        tipo_registro: str,
        entidad_id: int,
        accion: str,
        admin_id: int,
        motivo_rechazo: str = None
    ):
        if tipo_registro != "SOLICITUD":
            raise ValueError(f"Inconsistencia de capa de red: Se intentó {accion} un registro de tipo {tipo_registro}. Solo las SOLICITUDES admiten resolución 4-Ojos.")

        solicitud = db.query(SolicitudMovimientoTesoreria).filter(
            SolicitudMovimientoTesoreria.id == registro_id
        ).with_for_update().first()

        if not solicitud:
            raise PermissionError("Solicitud de movimiento no encontrada.")

        if solicitud.estado != "PENDING_APPROVAL":
            raise ValueError(f"Transacción inválida. La solicitud actual tiene estado: {solicitud.estado}")

        creador_id = getattr(solicitud, "creado_por_id", None)
        if creador_id and str(creador_id) == str(admin_id):
            raise PermissionError("Violación 4-Ojos: No puedes aprobar una transacción creada por ti mismo.")

        cuenta = db.query(CuentaTesoreria).filter(
            CuentaTesoreria.id == solicitud.cuenta_id,
            CuentaTesoreria.entidad_id == entidad_id
        ).with_for_update().first()

        if not cuenta:
            raise PermissionError("Acceso denegado: La cuenta no pertenece a la entidad activa.")

        es_egreso = getattr(solicitud, 'tipo', "INGRESO") == "EGRESO"
        monto_absoluto = Decimal(str(solicitud.monto))
        monto_transaccional = -monto_absoluto if es_egreso else monto_absoluto

        solicitud.usuario_resolutor_id = str(admin_id)

        try:
            if accion == "aprobar":
                saldo_actual = Decimal(str(cuenta.saldo_actual))
                nuevo_saldo = saldo_actual + monto_transaccional

                if nuevo_saldo < 0:
                    raise ValueError(f"Fondos insuficientes. Saldo actual: ${saldo_actual:.2f}")

                cuenta.saldo_actual = nuevo_saldo
                if es_egreso:
                    cuenta.saldo_retenido = Decimal(str(getattr(cuenta, 'saldo_retenido', 0.0))) - monto_absoluto

                nuevo_movimiento = MovimientoTesoreria(
                    cuenta_id=cuenta.id,
                    tipo=solicitud.tipo,
                    fecha=solicitud.fecha,
                    monto=monto_absoluto,
                    moneda=solicitud.moneda,
                    saldo_resultante=nuevo_saldo,
                    concepto_crudo=solicitud.concepto_crudo,
                    referencia_externa=solicitud.referencia_externa,
                    hash_transaccional=solicitud.hash_transaccional
                )
                db.add(nuevo_movimiento)
                db.flush()

                solicitud.estado = "APROBADO"
                solicitud.movimiento_definitivo_id = nuevo_movimiento.id

            elif accion == "rechazar":
                if not motivo_rechazo or not str(motivo_rechazo).strip():
                    raise ValueError("El motivo de rechazo es estrictamente obligatorio.")

                solicitud.estado = "RECHAZADO"
                solicitud.motivo_rechazo = str(motivo_rechazo).strip()

                if es_egreso:
                    cuenta.saldo_retenido = Decimal(str(getattr(cuenta, 'saldo_retenido', 0.0))) - monto_absoluto
            else:
                raise ValueError("Acción no soportada.")

            db.commit()
            db.refresh(solicitud)

            setattr(solicitud, "tipo_registro", "SOLICITUD")
            return solicitud

        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Fallo relacional al resolver la aprobación: {e}")
            raise e

    def anular_movimiento(self, db: Session, movimiento_id: int, motivo: str = "Extorno por anulación de operación original"):
        movimiento = db.query(MovimientoTesoreria).filter(
            MovimientoTesoreria.id == movimiento_id
        ).with_for_update().first()

        if not movimiento:
            raise ValueError("Movimiento de Tesorería no encontrado.")

        if movimiento.anulado:
            raise ValueError("El movimiento ya se encuentra anulado o compensado.")

        cuenta = db.query(CuentaTesoreria).filter(
            CuentaTesoreria.id == movimiento.cuenta_id
        ).with_for_update().first()

        if not cuenta:
            raise ValueError("Cuenta de Tesorería asociada no encontrada.")

        monto_absoluto = Decimal(str(movimiento.monto))
        saldo_actual = Decimal(str(cuenta.saldo_actual))
        tipo_mov = getattr(movimiento, 'tipo', 'INGRESO')
        es_egreso = (tipo_mov == "EGRESO")

        if es_egreso:
            nuevo_saldo = saldo_actual + monto_absoluto
            tipo_extorno = "INGRESO"
        else:
            nuevo_saldo = saldo_actual - monto_absoluto
            tipo_extorno = "EGRESO"

        hash_extorno = hashlib.sha256(f"{movimiento.hash_transaccional}_EXTORNO_{uuid.uuid4().hex}".encode()).hexdigest()

        movimiento_extorno = MovimientoTesoreria(
            cuenta_id=cuenta.id,
            tipo=tipo_extorno,
            fecha=date.today(),
            monto=monto_absoluto,
            moneda=movimiento.moneda,
            saldo_pendiente=Decimal("0.00"),
            saldo_resultante=nuevo_saldo,
            concepto_crudo=f"[EXTORNO] {movimiento.concepto_crudo}",
            referencia_externa=movimiento.referencia_externa,
            hash_transaccional=hash_extorno,
            comprobante_id=movimiento.comprobante_id,
            anulado=False
        )
        db.add(movimiento_extorno)

        cuenta.saldo_actual = nuevo_saldo
        movimiento.anulado = True
        movimiento.motivo_anulacion = motivo

        if movimiento.asiento_id:
            asiento = db.query(AsientoContable).filter(AsientoContable.id == movimiento.asiento_id).with_for_update().first()
            if asiento:
                if hasattr(asiento, 'is_active'):
                    asiento.is_active = False
                asiento.concepto = f"[ANULADO] {asiento.concepto}"

        db.flush()
        return movimiento

banco_service = BancoService()