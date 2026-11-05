from typing import List, Optional, Set
from sqlalchemy import desc
from sqlalchemy.orm import Session, joinedload

# Local imports
from core.database.models_tenant import CuentaBancaria, MovimientoBancario, MatchDetalleMovimiento
from core.schemas.banco import CuentaBancariaCreate

class CRUDBanco:

    # ==========================================
    # C U E N T A S   B A N C A R I A S
    # ==========================================
    def get_cuentas_activas(self, db: Session, entidad_id: int):
        return db.query(CuentaBancaria).filter(
            CuentaBancaria.is_active == True,
            CuentaBancaria.entidad_id == entidad_id
        ).all()

    def get_cuenta(self, db: Session, cuenta_id: int, entidad_id: int) -> Optional[CuentaBancaria]:
        # 🌟 FIX: Aislamiento estricto por entidad en todas las lecturas
        return db.query(CuentaBancaria).filter(
            CuentaBancaria.id == cuenta_id,
            CuentaBancaria.entidad_id == entidad_id,
            CuentaBancaria.is_active == True
        ).first()

    def existe_cbu(self, db: Session, cbu: str):
        if not cbu:
            return False
        return db.query(CuentaBancaria).filter(CuentaBancaria.cbu == cbu).first() is not None

    def create_cuenta(self, db: Session, obj_in: CuentaBancariaCreate) -> CuentaBancaria:
        db_obj = CuentaBancaria(**obj_in.model_dump())
        db.add(db_obj)
        # 🌟 FIX: Quitamos db.commit() para mantener la atomicidad transaccional en el Servicio
        db.flush()
        db.refresh(db_obj)
        return db_obj

    # ==========================================
    # M O V I M I E N T O S
    # ==========================================
    def get_movimientos(
        self, db: Session, cuenta_id: int, entidad_id: int, skip: int = 0, limit: int = 100
    ) -> List[MovimientoBancario]:
        """
        🌟 FIX ZERO-TRUST: Exigimos el entidad_id y cruzamos con la cuenta para evitar IDOR.
        Retorna movimientos con 'joinedload' para evitar el problema de N+1 queries.
        """
        return db.query(MovimientoBancario).join(
            CuentaBancaria, MovimientoBancario.cuenta_id == CuentaBancaria.id
        ).options(
            joinedload(MovimientoBancario.detalles_match)
        ).filter(
            MovimientoBancario.cuenta_id == cuenta_id,
            CuentaBancaria.entidad_id == entidad_id # 🛡️ Blindaje Perimetral
        ).order_by(
            desc(MovimientoBancario.fecha),
            desc(MovimientoBancario.id)
        ).offset(skip).limit(limit).all()

    def count_movimientos(self, db: Session, cuenta_id: int, entidad_id: int) -> int:
        """
        🌟 FIX ZERO-TRUST: Cuenta el total de registros respetando el perímetro de la entidad.
        """
        return db.query(MovimientoBancario).join(
            CuentaBancaria, MovimientoBancario.cuenta_id == CuentaBancaria.id
        ).filter(
            MovimientoBancario.cuenta_id == cuenta_id,
            CuentaBancaria.entidad_id == entidad_id, # 🛡️ Blindaje Perimetral
            MovimientoBancario.anulado == False
        ).count()

    def create_movimiento_sync(self, db: Session, obj_in: dict) -> MovimientoBancario:
        db_obj = MovimientoBancario(**obj_in)
        db.add(db_obj)
        # 🌟 FIX: Delegamos el manejo de excepciones a las capas superiores. Solo hacemos flush.
        db.flush()
        db.refresh(db_obj)
        return db_obj

    # ==========================================
    # C O N C I L I A C I O N E S
    # ==========================================
    def is_movimiento_conciliado(self, db: Session, movimiento_id: int) -> bool:
        # 🌟 FIX: Consulta sobre la tabla pivot de detalles
        return db.query(MatchDetalleMovimiento).filter(
            MatchDetalleMovimiento.movimiento_id == movimiento_id
        ).first() is not None

    def get_conciliados_bulk(self, db: Session, movimiento_ids: List[int]) -> Set[int]:
        if not movimiento_ids:
            return set()

        # 🌟 FIX: Consulta sobre la tabla pivot de detalles
        registros = db.query(MatchDetalleMovimiento.movimiento_id).filter(
            MatchDetalleMovimiento.movimiento_id.in_(movimiento_ids)
        ).all()
        return {r[0] for r in registros}

crud_banco = CRUDBanco()