import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime

from core.database.models_tenant import RazonSocialPropia, UsuarioEntidadRol
from core.api.deps import get_current_user, CachedUser, get_tenant_db_session, RoleChecker
from core.utils.enums import CondicionFiscalAFIP # 🌟 FIX FASE 11: Importar Enum

logger = logging.getLogger(__name__)

# Control de acceso base para lectura
router = APIRouter(dependencies=[Depends(RoleChecker(["admin", "dueño", "editor", "operador"]))])

# --- SCHEMAS ---
class EntidadCreate(BaseModel):
    cuit: str
    nombre_fantasia: str
    razon_social: str
    # 🌟 FIX FASE 11: Campo obligatorio al crear
    condicion_fiscal: CondicionFiscalAFIP = CondicionFiscalAFIP.NO_CATEGORIZADO

class EntidadResponse(EntidadCreate):
    id: int
    is_active: bool
    features: dict
    has_afip_credentials: bool
    afip_cert_expiration: Optional[datetime] = None
    afip_last_sync_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

# --- RUTAS ---
@router.get("/{schema_name}", response_model=List[EntidadResponse])
def get_mis_entidades(
    schema_name: str,
    current_user: CachedUser = Depends(get_current_user),
    db: Session = Depends(get_tenant_db_session)
):
    """Retorna las entidades asociadas al usuario autenticado bajo aislamiento de tenant."""
    if current_user.tenant.schema_name != schema_name:
        logger.critical(f"[SECURITY] Intento de cruce de tenant bloqueado. User: {current_user.email} -> Schema: {schema_name}")
        raise HTTPException(status_code=403, detail="Aislamiento de inquilino violado.")

    entidades_db = (
        db.query(RazonSocialPropia)
        .join(UsuarioEntidadRol, RazonSocialPropia.id == UsuarioEntidadRol.entidad_id)
        .filter(UsuarioEntidadRol.user_id == current_user.email)
        .all()
    )

    resultado = []
    for e in entidades_db:
        e_dict = {
            "id": e.id,
            "cuit": e.cuit,
            "nombre_fantasia": e.nombre_fantasia,
            "razon_social": e.razon_social,
            "condicion_fiscal": e.condicion_fiscal, # 🌟 FIX FASE 11: Inyección en el diccionario de salida
            "is_active": e.is_active,
            "features": e.features,
            "has_afip_credentials": bool(e.afip_certificate),
            "afip_cert_expiration": e.afip_cert_expiration,
            "afip_last_sync_at": e.afip_last_sync_at
        }
        resultado.append(e_dict)

    return resultado

@router.post("/{schema_name}", response_model=EntidadResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RoleChecker(["admin", "dueño"]))])
def crear_entidad_lead(
    schema_name: str,
    entidad_in: EntidadCreate,
    current_user: CachedUser = Depends(get_current_user),
    db: Session = Depends(get_tenant_db_session)
):
    """Crea una nueva entidad validando la cuota del Tenant contra el plan comercial."""
    if current_user.tenant.schema_name != schema_name:
        raise HTTPException(status_code=403, detail="Aislamiento de inquilino violado.")

    max_entidades = current_user.tenant.features.get("max_entidades", 1)

    count_actual = db.query(RazonSocialPropia).filter(RazonSocialPropia.is_active == True).count()

    if count_actual >= max_entidades:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Límite de Plan Alcanzado. Máximo permitido: {max_entidades} entidad(es)."
        )

    existente = db.query(RazonSocialPropia).filter(RazonSocialPropia.cuit == entidad_in.cuit).first()
    if existente:
        raise HTTPException(status_code=409, detail="El CUIT ya está registrado en este espacio.")

    try:
        nueva_entidad = RazonSocialPropia(**entidad_in.model_dump(), is_active=True)
        db.add(nueva_entidad)
        db.flush()

        nuevo_rol = UsuarioEntidadRol(
            user_id=current_user.email,
            entidad_id=nueva_entidad.id,
            rol="DUEÑO"
        )
        db.add(nuevo_rol)
        db.commit()
        db.refresh(nueva_entidad)

        return {
            **nueva_entidad.__dict__,
            "condicion_fiscal": nueva_entidad.condicion_fiscal, # 🌟 FIX FASE 11
            "has_afip_credentials": False,
            "afip_cert_expiration": None,
            "afip_last_sync_at": None
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Fallo transaccional al insertar entidad: {str(e)}")
        raise HTTPException(status_code=500, detail="Fallo transaccional en la creación de la entidad.")