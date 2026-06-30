from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")

class AddressSchema(BaseModel):
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None

    model_config = {'from_attributes': True}

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    size: int
    pages: Optional[int]
    has_next: Optional[bool]
    has_prev: Optional[bool]