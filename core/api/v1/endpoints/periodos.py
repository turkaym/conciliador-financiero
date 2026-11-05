from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session

# 🌟 FIX: Importamos RoleChecker
from core.api.deps import get_tenant_db_session, get_current_user, CachedUser, RoleChecker
from core.services.periodo_service import periodo_service
from core.schemas.periodo import PeriodoCierreRequest, PeriodoResponse

# 🌟 FIX RBAC: Permiso base para leer los periodos (para que la UI deshabilite inputs a los operadores)
router = APIRouter(dependencies=[Depends(RoleChecker(["admin", "dueño", "editor", "operador"]))])

# 🌟 MICRO-SEGMENTACIÓN: Acción destructiva. Solo el dueño sella la contabilidad.
@router.post("/cierre", status_code=status.HTTP_201_CREATED, dependencies=[Depends(RoleChecker(["admin", "dueño"]))])
def cerrar_periodo_contable(
    request: PeriodoCierreRequest,
    x_entity_id: int = Header(..., alias="X-Entity-ID"),
    db: Session = Depends(get_tenant_db_session),
    current_user: CachedUser = Depends(get_current_user)
):
    """
    Sella un mes contable. A partir de este momento, cualquier intento de
    crear, modificar o anular comprobantes o asientos en este mes será
    rechazado por la base de datos o el servicio.
    """
    try:
        periodo = periodo_service.cerrar_periodo(
            db=db,
            anio=request.anio,
            mes=request.mes,
            usuario_id=current_user.id
        )
        return {
            "status": "success",
            "message": f"Período {request.mes}/{request.anio} cerrado exitosamente y sellado."
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno al cerrar el período.")

@router.get("/", response_model=List[PeriodoResponse])
def listar_periodos_cerrados(
    x_entity_id: int = Header(..., alias="X-Entity-ID"),
    db: Session = Depends(get_tenant_db_session),
    current_user: CachedUser = Depends(get_current_user)
):
    """
    Lista todos los períodos que ya fueron liquidados/cerrados en este Tenant.
    Ideal para el Frontend (para deshabilitar botones de edición en meses cerrados).
    """
    return periodo_service.obtener_periodos(db)