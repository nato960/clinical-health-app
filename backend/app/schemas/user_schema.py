from datetime import date
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import UserRole
from app.schemas.shared import AddressSchema


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: UserRole
    staff_id: Optional[int] = None
    doctor_id: Optional[int] = None
    patient_id: Optional[int] = None


class UserResponse(BaseModel):
    id: int
    email: str
    role: UserRole
    is_active: bool
    staff_id: Optional[int]
    doctor_id: Optional[int]
    patient_id: Optional[int]

    model_config = {"from_attributes": True}


class PatientRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    name: str = Field(..., min_length=2, max_length=100)
    cpf: str = Field(..., min_length=11, max_length=14)
    birth_date: Optional[date] = None
    phone: str = Field(..., min_length=8, max_length=20)
    address: Optional[AddressSchema] = None