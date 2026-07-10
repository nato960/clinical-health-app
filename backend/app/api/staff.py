from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from app.core.security import require_roles
from app.schemas.staff_schema import StaffCreate, StaffPatch, StaffResponse
from app.services.staff_service import StaffService, get_staff_service
from app.services.staff_service import STAFF_LIST_MAX_LIMIT
from app.models.enums import Sector, UserRole
from app.schemas.shared import PaginatedResponse


router = APIRouter(
    prefix="/staff",
    tags=["Staff"],
    dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.USER_ADMIN))],
)

@router.get("/", response_model=PaginatedResponse[StaffResponse], status_code=status.HTTP_200_OK)
async def list_staff(
    page: int = Query(default=1, ge=1),
    size: Optional[int] = Query(default=None, ge=1, le=STAFF_LIST_MAX_LIMIT),
    search: Optional[str] = Query(default=None),
    sector: Optional[Sector] = Query(default=None),
    service: StaffService = Depends(get_staff_service)):

    return await service.list_staff(
        page=page,
        size=size,
        search=search,
        sector=sector
    )

@router.post("/", response_model=StaffResponse, status_code=status.HTTP_201_CREATED)
async def create_staff(
    data: StaffCreate,
    service: StaffService = Depends(get_staff_service)):
    return await service.create(data)

@router.get("/{staff_id}", response_model=StaffResponse)
async def get_staff_by_id(
    staff_id: int,
    active_only: bool = Query(default=True),
    service: StaffService = Depends(get_staff_service)):
    staff = await service.get_by_id(staff_id, active_only)
    return staff

@router.patch("/{staff_id}", response_model=StaffResponse)
async def patch_staff(
    staff_id: int,
    data: StaffPatch,
    service: StaffService = Depends(get_staff_service)):
    return await service.patch(staff_id, data)

@router.delete("/{staff_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_staff(
    staff_id: int,
    service: StaffService = Depends(get_staff_service)):
    return await service.deactivate(staff_id)
