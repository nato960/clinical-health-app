from fastapi import APIRouter, Depends, status

from app.schemas.doctor_schema import DoctorCreate, DoctorPatch, DoctorResponse
from app.services.doctor_service import DoctorService, get_doctor_service


router = APIRouter(prefix="/doctors", tags=["Doctors"])

@router.get("/", response_model=list[DoctorResponse], status_code=status.HTTP_200_OK)
async def list_doctors(
    service: DoctorService = Depends(get_doctor_service)):
    return await service.list_doctors()

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