import json
import hashlib
import logging
from typing import List
from fastapi import Request, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.api.deps import get_current_user, CachedUser
from core.database.session import get_master_db
from core.database.models_master import AuditTrail
from core.api.context import get_audit_ip_address

logger = logging.getLogger("RBAC_SECURITY")

class RoleChecker:
    """
    Dependencia Enterprise para validación estricta de privilegios.
    Bloquea el acceso a roles no autorizados y sella un registro
    de intrusión con firma criptográfica en la base de datos Maestra.
    """
    def __init__(self, allowed_roles: List[str]):
        # 🌟 FIX REAL: Normalizamos los roles requeridos a minúsculas
        self.allowed_roles = [r.lower() for r in allowed_roles]

    def __call__(
        self,
        request: Request,
        current_user: CachedUser = Depends(get_current_user),
        db_master: Session = Depends(get_master_db)
    ) -> CachedUser:

        # 🌟 FIX REAL: Normalizamos el rol del usuario para evitar falsos positivos ("ADMIN" vs "admin")
        user_role = str(current_user.role).lower() if current_user.role else ""

        if user_role not in self.allowed_roles:
            # 🛡️ INTERCEPCIÓN ACTIVA: Registro de Intrusión Silenciosa
            ip_address = get_audit_ip_address()

            try:
                changes_payload = {
                    "security_alert": "Intento de escalada de privilegios bloqueado.",
                    "required_roles": self.allowed_roles,
                    "user_role": current_user.role
                }

                raw_data = f"{current_user.tenant.id}|{current_user.id}|UNAUTHORIZED_ACCESS|{request.url.path}|{request.method}|{ip_address}|{json.dumps(changes_payload, sort_keys=True)}"
                firma = hashlib.sha256(raw_data.encode('utf-8')).hexdigest()

                audit_record = AuditTrail(
                    user_id=current_user.id,
                    tenant_id=current_user.tenant.id,
                    action="UNAUTHORIZED_ACCESS",
                    entity_name=request.url.path,
                    entity_id=request.method,
                    ip_address=ip_address,
                    changes=changes_payload,
                    hash_firma=firma
                )
                db_master.add(audit_record)
                db_master.commit()
                logger.warning(f"🛡️ [RBAC] Intrusión bloqueada de {current_user.email} hacia {request.url.path}. Hash: {firma[:8]}...")
            except Exception as e:
                db_master.rollback()
                logger.error(f"Fallo crítico al registrar intrusión de seguridad: {e}")

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes los permisos de seguridad necesarios para realizar esta acción."
            )

        return current_user