import logging

import firebase_admin
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth, credentials

from app.core.config import settings
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.models.enums import UserRole
from app.models.user import User
from app.services.user_service import UserService, get_user_service

logger = logging.getLogger(__name__)

firebase_admin.initialize_app(credentials.Certificate(settings.firebase_credentials_path))

bearer_schema = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_schema),
    user_service: UserService = Depends(get_user_service),
) -> User:
    try:
        decoded = auth.verify_id_token(credentials.credentials)
    except Exception:
        logger.warning("Failed to verify token", exc_info=True)
        raise UnauthorizedException()
    
    user = await user_service.get_by_firebase_uid(decoded["uid"])
    if not user:
        raise UnauthorizedException("Account not registered.")
    return user

def require_roles(*roles: UserRole):
    async def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise ForbiddenException()
        return user
    return checker
    
