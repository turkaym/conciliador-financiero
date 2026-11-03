import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from core.api.context import get_audit_ip_address
from core.database.models.contabilidad import ReglaAprendizaje
from core.database.models.entidades import RazonSocialPropia
from core.database.models.sistema import LogAuditoria
from core.schemas.ai_rules import RuleCreate, RuleUpdate


class RuleNotFound(Exception):
    pass


class RuleConflict(Exception):
    pass


class RuleStorageError(Exception):
    pass


def serialize_rule(rule: ReglaAprendizaje) -> dict:
    return {
        "id": rule.id,
        "tipo_regla": "concepto_cuit",
        "entidad_id": rule.entidad_id,
        "patron_concepto": rule.patron_concepto,
        "cuit_asociado": rule.cuit_asociado,
        "tipo_cbte_asociado": rule.tipo_cbte_asociado,
        "frecuencia_uso": rule.frecuencia_uso,
        "activa": rule.activa,
        "created_at": rule.created_at,
        "updated_at": rule.updated_at,
    }


class AiRulesService:
    def list(self, db: Session, entidad_id: int, limit: int, offset: int,
             activa: bool | None = None, buscar: str | None = None):
        query = db.query(ReglaAprendizaje).filter(ReglaAprendizaje.entidad_id == entidad_id)
        if activa is not None:
            query = query.filter(ReglaAprendizaje.activa == activa)
        if buscar:
            query = query.filter(ReglaAprendizaje.patron_concepto.ilike(f"%{buscar.strip()}%"))
        total = query.count()
        rules = query.order_by(ReglaAprendizaje.id).offset(offset).limit(limit).all()
        return [serialize_rule(rule) for rule in rules], total

    def get(self, db: Session, entidad_id: int, rule_id: int):
        rule = db.query(ReglaAprendizaje).filter(
            ReglaAprendizaje.id == rule_id,
            ReglaAprendizaje.entidad_id == entidad_id,
        ).first()
        if not rule:
            raise RuleNotFound
        return rule

    def create(self, db: Session, entidad_id: int, data: RuleCreate, user_id: str):
        if not db.query(RazonSocialPropia.id).filter(RazonSocialPropia.id == entidad_id).first():
            raise RuleNotFound
        duplicate = db.query(ReglaAprendizaje.id).filter(
            ReglaAprendizaje.entidad_id == entidad_id,
            ReglaAprendizaje.patron_concepto == data.patron_concepto,
        ).first()
        if duplicate:
            raise RuleConflict
        rule = ReglaAprendizaje(
            entidad_id=entidad_id,
            patron_concepto=data.patron_concepto,
            cuit_asociado=data.cuit_asociado,
            tipo_cbte_asociado=data.tipo_cbte_asociado,
            frecuencia_uso=0,
            activa=True,
        )
        return self._commit(db, rule, "REGLA_MANUAL_CREADA", user_id)

    def update(self, db: Session, entidad_id: int, rule_id: int,
               data: RuleUpdate, user_id: str, action: str = "REGLA_ACTUALIZADA"):
        rule = self.get(db, entidad_id, rule_id)
        expected = data.expected_updated_at
        current = rule.updated_at
        if current.tzinfo is None and expected.tzinfo is not None:
            expected = expected.replace(tzinfo=None)
        if current != expected:
            raise RuleConflict
        version_filter = ReglaAprendizaje.updated_at == current
        if db.bind.dialect.name == "sqlite":
            version_filter = func.datetime(ReglaAprendizaje.updated_at) == current.strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        changed = db.query(ReglaAprendizaje).filter(
            ReglaAprendizaje.id == rule_id,
            ReglaAprendizaje.entidad_id == entidad_id,
            version_filter,
        ).update({"activa": data.activa, "updated_at": datetime.now(timezone.utc)})
        if changed != 1:
            raise RuleConflict
        rule = self.get(db, entidad_id, rule_id)
        return self._commit(db, rule, action, user_id)

    def deactivate(self, db: Session, entidad_id: int, rule_id: int,
                   expected_updated_at: datetime, user_id: str):
        return self.update(
            db, entidad_id, rule_id,
            RuleUpdate(activa=False, expected_updated_at=expected_updated_at), user_id,
            "REGLA_DESACTIVADA",
        )

    def _commit(self, db: Session, rule: ReglaAprendizaje, action: str, user_id: str):
        try:
            db.add(rule)
            db.flush()
            details = json.dumps({"regla_id": rule.id, "accion": action}, sort_keys=True)
            db.add(LogAuditoria(
                entidad="ReglaAprendizaje", entidad_id=rule.id, accion=action,
                usuario_id=user_id, ip_origen=get_audit_ip_address(), detalles=details,
                hash_firma=hashlib.sha256(details.encode("utf-8")).hexdigest(),
            ))
            db.commit()
            db.refresh(rule)
            return serialize_rule(rule)
        except Exception as exc:
            db.rollback()
            raise RuleStorageError from exc


ai_rules_service = AiRulesService()
