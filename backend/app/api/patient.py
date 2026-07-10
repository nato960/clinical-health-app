from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from app.core.security import require_roles
from app.models.enums import UserRole
from app.schemas.patient_schema import PatientCreate, PatientPatch, PatientResponse
from app.services.patient_service import PatientService, get_patient_service
from app.services.patient_service import PATIENTS_LIST_MAX_LIMIT
from app.schemas.shared import PaginatedResponse


router = APIRouter(
    prefix="/patients",
    tags=["Patients"],
    dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.USER_ADMIN))],
)

@router.get("/", response_model=PaginatedResponse[PatientResponse], status_code=status.HTTP_200_OK)
async def list_patients(
    page: int = Query(default=1, ge=1),
    size: Optional[int] = Query(default=None, ge=1, le=PATIENTS_LIST_MAX_LIMIT),
    search: Optional[str] = Query(default=None),
    service: PatientService = Depends(get_patient_service)):

    return await service.list_patients(
        page=page,
        size=size,
        search=search
    )

@router.post("/", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(
    data: PatientCreate,
    service: PatientService = Depends(get_patient_service)):
    return await service.create(data)

@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient_by_id(
    patient_id: int,
    active_only: bool = Query(default=True),
    service: PatientService = Depends(get_patient_service)):
    patient = await service.get_by_id(patient_id, active_only)
    return patient

@router.patch("/{patient_id}", response_model=PatientResponse)
async def patch_patient(
    patient_id: int,
    data: PatientPatch,
    service: PatientService = Depends(get_patient_service)):
    return await service.patch(patient_id, data)

@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_patient(
    patient_id: int,
    service: PatientService = Depends(get_patient_service)):
    return await service.deactivate(patient_id)
