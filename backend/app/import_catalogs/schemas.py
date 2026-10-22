from typing import Generic, TypeVar

from pydantic import BaseModel


class CatalogItem(BaseModel):
    id: int
    code: str
    name: str
    type: str


class TemplateItem(BaseModel):
    id: int
    name: str
    type: str
    version: int
    columns: list[str]


Item = TypeVar("Item")


class CatalogList(BaseModel, Generic[Item]):
    page: int = 1
    page_size: int = 25
    total: int
    items: list[Item]
