from typing import Any, Generic, List, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class APIResponse(BaseModel):
    message: str
    data: Any | None


class PagedData(BaseModel, Generic[T]):
    """Standard paginated payload — always lives inside APIResponse.data."""
    items: List[T]
    total: int
    skip: int
    limit: int