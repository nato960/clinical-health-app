from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from app.schemas.appointment_schema import (
    AppointmentCancel,
    AppointmentReschedule,
    AppointmentResponse,
    AppointmentSchedule,
)
from app.schemas.shared import PaginatedResponse
from app.services.appointment_service import (
    APPOINTMENTS_LIST_MAX_LIMIT,
    AppointmentService,
    get_appointment_service,
)

router = APIRouter(prefix="/appointments", tags=["Appointments"])


@router.get("/", response_model=PaginatedResponse[AppointmentResponse], status_code=status.HTTP_200_OK)
async def list_appointments(
    page: int = Query(default=1, ge=1),
    size: Optional[int] = Query(default=None, ge=1, le=APPOINTMENTS_LIST_MAX_LIMIT),
    doctor_id: Optional[int] = Query(default=None, ge=1),
    patient_id: Optional[int] = Query(default=None, ge=1),
    active_only: bool = Query(default=True),
    service: AppointmentService = Depends(get_appointment_service)):

    return await service.list_appointments(
        page=page,
        size=size,
        doctor_id=doctor_id,
        patient_id=patient_id,
        active_only=active_only
    )


@router.post("/", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def schedule_appointment(
    data: AppointmentSchedule,
    service: AppointmentService = Depends(get_appointment_service)):
    return await service.schedule(data)


@router.get("/{appointment_id}", response_model=AppointmentResponse)
async def get_appointment_by_id(
    appointment_id: int,
    active_only: bool = Query(default=True),
    service: AppointmentService = Depends(get_appointment_service)):
    return await service.get_by_id(appointment_id, active_only)


@router.patch("/{appointment_id}", response_model=AppointmentResponse)
async def reschedule_appointment(
    appointment_id: int,
    data: AppointmentReschedule,
    service: AppointmentService = Depends(get_appointment_service)):
    return await service.reschedule(appointment_id, data)


@router.post("/{appointment_id}/cancel", response_model=AppointmentResponse, status_code=status.HTTP_200_OK)
async def cancel_appointment(
    appointment_id: int,
    data: AppointmentCancel,
    service: AppointmentService = Depends(get_appointment_service)):
    return await service.cancel(appointment_id, data)
