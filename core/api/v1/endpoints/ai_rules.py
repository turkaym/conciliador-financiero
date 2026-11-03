from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from core.api.deps import CachedUser, RoleChecker, get_current_user, get_tenant_db_session
from core.schemas.ai_rules import RuleCreate, RuleList, RuleResponse, RuleUpdate
from core.services.ai_rules_service import (
    RuleConflict, RuleNotFound, RuleStorageError, ai_rules_service, serialize_rule,
)


router = APIRouter(
    prefix="/ai-rules",
    tags=["Reglas determinísticas"],
    dependencies=[Depends(RoleChecker(["admin", "dueño"]))],
)
EntityId = Annotated[int, Header(alias="X-Entity-ID", ge=1)]


def parse_payload(model, payload: dict):
    try:
        return model.model_validate(payload)
    except ValidationError:
        raise HTTPException(status_code=400, detail="Datos de regla inválidos.")


def translate_errors(operation):
    try:
        return operation()
    except RuleNotFound:
        raise HTTPException(status_code=404, detail="Regla no encontrada.")
    except RuleConflict:
        raise HTTPException(status_code=409, detail="La regla fue modificada por otra operación.")
    except RuleStorageError:
        raise HTTPException(status_code=500, detail="No se pudo completar la operación.")


@router.get("", response_model=RuleList)
def list_rules(
    x_entity_id: EntityId,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    activa: bool | None = None,
    buscar: str | None = Query(None, min_length=1, max_length=100),
    db: Session = Depends(get_tenant_db_session),
):
    items, total = ai_rules_service.list(db, x_entity_id, limit, offset, activa, buscar)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/{rule_id}", response_model=RuleResponse)
def get_rule(rule_id: int, x_entity_id: EntityId,
             db: Session = Depends(get_tenant_db_session)):
    return translate_errors(lambda: serialize_rule(ai_rules_service.get(db, x_entity_id, rule_id)))


@router.post("", response_model=RuleResponse, status_code=status.HTTP_201_CREATED)
def create_rule(
    x_entity_id: EntityId,
    payload: dict = Body(...),
    db: Session = Depends(get_tenant_db_session),
    current_user: CachedUser = Depends(get_current_user),
):
    data = parse_payload(RuleCreate, payload)
    return translate_errors(
        lambda: ai_rules_service.create(db, x_entity_id, data, current_user.sub)
    )


@router.patch("/{rule_id}", response_model=RuleResponse)
def update_rule(
    rule_id: int,
    x_entity_id: EntityId,
    payload: dict = Body(...),
    db: Session = Depends(get_tenant_db_session),
    current_user: CachedUser = Depends(get_current_user),
):
    data = parse_payload(RuleUpdate, payload)
    return translate_errors(
        lambda: ai_rules_service.update(db, x_entity_id, rule_id, data, current_user.sub)
    )


@router.delete("/{rule_id}", response_model=RuleResponse)
def deactivate_rule(
    rule_id: int,
    x_entity_id: EntityId,
    expected_updated_at: datetime,
    db: Session = Depends(get_tenant_db_session),
    current_user: CachedUser = Depends(get_current_user),
):
    return translate_errors(lambda: ai_rules_service.deactivate(
        db, x_entity_id, rule_id, expected_updated_at, current_user.sub
    ))
