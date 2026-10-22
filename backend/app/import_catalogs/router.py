from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.access.security import get_current_user
from app.database import get_db
from app.errors import ApiError
from app.import_catalogs.schemas import CatalogItem, CatalogList, TemplateItem
from app.models import DataSource, ImportTemplate, TemplateField, User

router = APIRouter(prefix="/catalog", tags=["catalog"])


def _api_type(source_type: str) -> str:
    return "MOVIMIENTO" if source_type == "BANCO" else "COMPROBANTE"


@router.get("/sources", response_model=CatalogList[CatalogItem])
def list_sources(
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
    type: str | None = Query(default=None),
):
    if type is not None and type not in {"MOVIMIENTO", "COMPROBANTE"}:
        raise ApiError(400, "INVALID_SOURCE_TYPE", "Unsupported source type")
    sources = db.scalars(select(DataSource).where(DataSource.active.is_(True)).order_by(DataSource.id)).all()
    items = [
        CatalogItem(id=source.id, code=source.code, name=source.name, type=_api_type(source.source_type))
        for source in sources
        if type is None or _api_type(source.source_type) == type
    ]
    return CatalogList(total=len(items), items=items)


@router.get("/templates", response_model=CatalogList[TemplateItem])
def list_templates(
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
    source_id: int = Query(gt=0),
    type: str = Query(),
):
    if type not in {"MOVIMIENTO", "COMPROBANTE"}:
        raise ApiError(400, "INVALID_TEMPLATE_TYPE", "Unsupported template type")
    source = db.scalar(select(DataSource).where(DataSource.id == source_id, DataSource.active.is_(True)))
    if source is None:
        raise ApiError(404, "SOURCE_NOT_FOUND", "Source not found")
    if _api_type(source.source_type) != type:
        return CatalogList(total=0, items=[])
    templates = db.scalars(
        select(ImportTemplate)
        .where(ImportTemplate.source_id == source_id, ImportTemplate.template_type == type, ImportTemplate.active.is_(True))
        .order_by(ImportTemplate.id)
    ).all()
    items = []
    for template in templates:
        columns = db.scalars(
            select(TemplateField.source_column)
            .where(TemplateField.template_id == template.id)
            .order_by(TemplateField.id)
        ).all()
        items.append(TemplateItem(id=template.id, name=template.name, type=template.template_type, version=template.version, columns=columns))
    return CatalogList(total=len(items), items=items)
