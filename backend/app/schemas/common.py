"""Shared schema primitives."""

from typing import Generic, List, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ORMModel(BaseModel):
    """Base for every response model read straight off an ORM object."""

    model_config = ConfigDict(from_attributes=True)


class Message(BaseModel):
    message: str
    ok: bool = True


class Page(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int = 1
    page_size: int = 50
