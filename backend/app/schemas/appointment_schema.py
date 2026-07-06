from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator

from app.models.enums import CancellationReason, Speciality
from app.schemas.doctor_schema import DoctorResponse
from app.schemas.patient_schema import PatientResponse


def _reject_timezone_aware(v: Optional[datetime]) -> Optional[datetime]:
    if v is not None and v.tzinfo is not None:
        raise ValueError("date must be naive (no timezone) - appointment times are always in the clinic's local time.")
    return v


class AppointmentSchedule(BaseModel):
    patient_id: int
    doctor_id: Optional[int] = None
    date: datetime
    speciality: Optional[Speciality] = None

    @field_validator("date")
    @classmethod
    def validate_naive_date(cls, v: datetime) -> datetime:
        return _reject_timezone_aware(v)


class AppointmentReschedule(BaseModel):
    doctor_id: Optional[int] = None
    date: Optional[datetime] = None

    @field_validator("date")
    @classmethod
    def validate_naive_date(cls, v: Optional[datetime]) -> Optional[datetime]:
        return _reject_timezone_aware(v)


class AppointmentCancel(BaseModel):
    cancellation_reason: CancellationReason


class AppointmentResponse(BaseModel):
    id: int
    doctor: DoctorResponse
    patient: PatientResponse
    date: datetime
    speciality: Optional[Speciality]
    cancellation_reason: Optional[CancellationReason]

    model_config = {"from_attributes": True}
