from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from app.schemas.doctor_schema import DoctorCreate, DoctorPatch, DoctorResponse
from app.services.doctor_service import DoctorService, get_doctor_service
from app.services.doctor_service import DOCTORS_LIST_MAX_LIMIT
from app.models.enums import Speciality
from app.schemas.shared import PaginatedResponse


router = APIRouter(prefix="/doctors", tags=["Doctors"])

@router.get("/", response_model=PaginatedResponse[DoctorResponse], status_code=status.HTTP_200_OK)
async def list_doctors(
    page: int = Query(default=1, ge=1),
    size: Optional[int] = Query(default=None, ge=1, le=DOCTORS_LIST_MAX_LIMIT),
    search: Optional[str] = Query(default=None),
    speciality: Optional[Speciality] = Query(default=None),
    service: DoctorService = Depends(get_doctor_service)):

    return await service.list_doctors(
        page=page,
        size=size,
        search=search,
        speciality=speciality
    )

@router.post("/", response_model=DoctorResponse, status_code=status.HTTP_201_CREATED)
async def create_doctor(
    data: DoctorCreate, 
    service: DoctorService = Depends(get_doctor_service)):
    return await service.create(data)

@router.get("/{doctor_id}", response_model=DoctorResponse)
async def get_doctor_by_id(
    doctor_id: int,
    service: DoctorService = Depends(get_doctor_service)):
    doctor = await service.get_by_id(doctor_id)
    return doctor

@router.patch("/{doctor_id}", response_model=DoctorResponse)
async def patch_doctor(
    doctor_id: int,
    data: DoctorPatch,
    service: DoctorService = Depends(get_doctor_service)):
    return await service.patch(doctor_id, data)

@router.delete("/{doctor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_doctor(
    doctor_id: int,
    service: DoctorService = Depends(get_doctor_service)):
    return await service.deactivate(doctor_id)