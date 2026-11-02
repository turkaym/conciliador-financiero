from typing import List, Optional, Any, Union
from sqlalchemy.orm import Session
from sqlalchemy import desc

# 🌟 FIX FASE A: Importaciones acopladas exclusivamente al dominio
from core.domains.comprobantes.models import Comprobante, ComprobanteAsociado
from core.utils.enums import ClaseDocumento

class ComprobanteRepository:
    """
    Repositorio de Datos del Dominio de Comprobantes.
    Encapsula la persistencia y protege la instanciación de relaciones complejas.
    """

    def get_by_id(self, db: Session, id: int) -> Optional[Comprobante]:
        return db.query(Comprobante).filter(
            Comprobante.id == id,
            Comprobante.is_active == True
        ).first()

    def get_multi(
        self, db: Session, entidad_id: int, clase_documento: Optional[ClaseDocumento] = None, skip: int = 0, limit: int = 100
    ) -> List[Comprobante]:
        query = db.query(Comprobante).filter(
            Comprobante.entidad_id == entidad_id,
            Comprobante.is_active == True
        )
        if clase_documento:
            query = query.filter(Comprobante.clase_documento == clase_documento)

        return query.order_by(desc(Comprobante.fecha_emision)).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: Union[dict, Any]) -> Comprobante:
        obj_in_data = obj_in if isinstance(obj_in, dict) else obj_in.model_dump(exclude_unset=True)

        # 🌟 SALVAGUARDA FISCAL: Si el comprobante nace sin saldo explícito, se asume el total.
        if 'importe_total' in obj_in_data and 'saldo_pendiente' not in obj_in_data:
            obj_in_data['saldo_pendiente'] = obj_in_data['importe_total']

        # 🌟 FIX ORM: Extracción segura de arreglos relacionales (Evita crash de SQLAlchemy)
        asociados_data = obj_in_data.pop('comprobantes_asociados', [])

        db_obj = Comprobante(**obj_in_data)

        # Instanciación One-to-Many nativa de SQLAlchemy
        for asoc in asociados_data:
            db_obj.comprobantes_asociados.append(ComprobanteAsociado(**asoc))

        db.add(db_obj)
        return db_obj

    def update(self, db: Session, db_obj: Comprobante, obj_in: Union[dict, Any]) -> Comprobante:
        update_data = obj_in if isinstance(obj_in, dict) else obj_in.model_dump(exclude_unset=True)
        for field in update_data:
            if hasattr(db_obj, field):
                setattr(db_obj, field, update_data[field])
        db.add(db_obj)
        return db_obj

    def soft_delete(self, db: Session, db_obj: Comprobante) -> Comprobante:
        # 🌟 INMUTABILIDAD CONTABLE: Prohibido borrar la transacción
        db_obj.is_active = False
        db.add(db_obj)
        return db_obj

comprobante_repository = ComprobanteRepository()