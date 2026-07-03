from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["System"])


class HealthResponse(BaseModel):
    status: str


@router.get("/healthcheck", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(status="ok")
