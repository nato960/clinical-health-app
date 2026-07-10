from fastapi import APIRouter, Depends, status

from app.core.security import get_current_user, require_roles
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.user_schema import UserCreate, UserResponse
from app.services.user_service import UserService, get_user_service

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    creator: User = Depends(require_roles(UserRole.ADMIN, UserRole.USER_ADMIN)),
    service: UserService = Depends(get_user_service),
):
    return await service.create_user(creator, data)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
