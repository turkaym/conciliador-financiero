from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from core.database.models_tenant import PlanCuentas

class CRUDPlanCuentas:
    def get_multi(self, db: Session, skip: int = 0, limit: int = 100) -> List[PlanCuentas]:
        """Obtiene el plan de cuentas completo del Tenant."""
        return db.query(PlanCuentas).order_by(PlanCuentas.codigo).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in_data: dict) -> PlanCuentas:
        """Crea una nueva cuenta asegurando que NO sea de sistema."""
        # Forzamos que cualquier cuenta creada manualmente por el usuario NO sea de sistema
        obj_in_data["is_system"] = False
        db_obj = PlanCuentas(**obj_in_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, id: int) -> PlanCuentas:
        """Elimina una cuenta con validación estricta Anti-Suicidio."""
        cuenta = db.query(PlanCuentas).filter(PlanCuentas.id == id).first()

        if not cuenta:
            raise HTTPException(status_code=404, detail="Cuenta no encontrada.")

        # 🛡️ LA BARRERA ANTI-SUICIDIO
        if cuenta.is_system:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operación denegada. No se pueden eliminar las cuentas estructurales del sistema."
            )

        # Verificar que no tenga subcuentas antes de borrar (Integridad Referencial)
        subcuentas = db.query(PlanCuentas).filter(PlanCuentas.parent_id == cuenta.id).first()
        if subcuentas:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede eliminar la cuenta porque contiene subcuentas asociadas."
            )

        db.delete(cuenta)
        db.commit()
        return cuenta

crud_plan_cuentas = CRUDPlanCuentas()