from fastapi import APIRouter, Depends, status

from app.schemas.user_schema import PatientRegisterRequest, UserResponse
from app.services.user_service import UserService, get_user_service

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_patient(
    data: PatientRegisterRequest,
    service: UserService = Depends(get_user_service),
):
    return await service.register_patient(data)
