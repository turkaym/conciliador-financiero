from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

# 🌟 FIX ARQUITECTURA: Usamos el inyector Multi-Tenant exacto de tu deps.py
from core.api.deps import get_tenant_db_session
from core.database.models.contabilidad import PlanCuentas
from core.domains.contabilidad.schemas import PlanCuentasResponse

router = APIRouter()

@router.get("/cuentas/imputables", response_model=List[PlanCuentasResponse])
def listar_cuentas_imputables(
    skip: int = 0,
    limit: int = 500,
    # 🌟 FIX: Inyectamos la sesión del esquema aislado de la empresa actual
    db: Session = Depends(get_tenant_db_session)
):
    """
    Retorna exclusivamente las cuentas contables de último nivel (imputables),
    ideales para rellenar los selectores (dropdowns) en el frontend.
    """
    cuentas = db.query(PlanCuentas)\
        .filter(PlanCuentas.imputable == True)\
        .order_by(PlanCuentas.codigo)\
        .offset(skip).limit(limit).all()
    return cuentas