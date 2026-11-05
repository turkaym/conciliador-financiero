from sqlalchemy import Column, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base, Mapper

# ==========================================
# BASE DECLARATIVA AISLADA
# ==========================================
TenantBase = declarative_base()

# ==========================================
# MIXIN ARQUITECTÓNICO
# ==========================================
class AuditableMixin:
    """
    Centraliza las marcas de tiempo y auditoría.
    Prepara la base de datos para la inyección de trazas criptográficas (Fase 7).
    """
    created_at = Column(
        DateTime(timezone=True),
        default=func.now(),           # 🛡️ Defensa 1: SQLAlchemy lo inyecta en el INSERT
        server_default=func.now(),    # 🛡️ Defensa 2: PostgreSQL lo inyecta si se evade el ORM
        nullable=False                # 🛡️ Defensa 3: Sincronizado con el motor DB
    )

    updated_at = Column(
        DateTime(timezone=True),
        default=func.now(),           # 🛡️ Defensa 1: SQLAlchemy lo inyecta al crear (INSERT)
        onupdate=func.now(),          # 🛡️ Defensa 2: SQLAlchemy lo actualiza al modificar (UPDATE)
        server_default=func.now(),    # 🛡️ Defensa 3: Fallback de PostgreSQL
        nullable=False                # 🛡️ Defensa 4: Garantiza integridad estricta
    )

# ==========================================
# ESCUDO ANTI-DELETE (Inmutabilidad Global)
# ==========================================
class AccountingImmutabilityError(Exception):
    pass

def prevent_financial_delete(mapper: Mapper, connection, target):
    raise AccountingImmutabilityError(
        f"Violación de Inmutabilidad Contable: Está estrictamente prohibido eliminar "
        f"registros de la tabla '{target.__tablename__}'. Utilice anulaciones lógicas (Soft Delete) "
        f"o contra-asientos."
    )