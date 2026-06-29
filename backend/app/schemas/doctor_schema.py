from datetime import date
from typing import Optional
from pydantic import BaseModel

from app.models.enums import Speciality
from app.schemas.shared import AddressSchema


class DoctorCreate(BaseModel):
    name: str
    email: str
    crm: str
    birth_date: Optional[date] = None
    phone: str
    speciality: Speciality
    address: Optional[AddressSchema] = None

class DoctorPatch(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[AddressSchema] = None

class DoctorResponse(BaseModel):
    id: int
    name: str
    email: str
    crm: str
    birth_date: Optional[date]
    phone: Optional[str]
    speciality: Speciality
    is_active: bool
    address: Optional[AddressSchema]

    model_config = {"from_attributes": True}
