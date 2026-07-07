from datetime import date
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.enums import Sector
from app.schemas.shared import AddressSchema


class StaffCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    cpf: str = Field(..., pattern=r"^\d{3}\.?\d{3}\.?\d{3}-?\d{2}$")
    birth_date: Optional[date] = None
    phone: str = Field(..., min_length=8, max_length=20)
    sector: Sector
    address: Optional[AddressSchema] = None

    @field_validator("birth_date")
    @classmethod
    def birth_date_must_be_past(cls, v: Optional[date]) -> Optional[date]:
        if v and v >= date.today():
            raise ValueError("Birth date must be a past date")
        return v

class StaffPatch(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, min_length=8, max_length=20)
    address: Optional[AddressSchema] = None

class StaffResponse(BaseModel):
    id: int
    name: str
    email: str
    cpf: str
    birth_date: Optional[date]
    phone: Optional[str]
    sector: Sector
    is_active: bool
    address: Optional[AddressSchema]

    model_config = {"from_attributes": True}
