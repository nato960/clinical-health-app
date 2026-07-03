import logging
import sys

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.api.doctor import router as doctor_router
from app.api.health import router as health_router
from app.api.patient import router as patient_router
from app.core.exceptions import AppException
from sqlalchemy.exc import SQLAlchemyError

logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Clinical Health API",
    description="REST API for managing clinical staff records (doctors and their addresses).",
    version="0.1.0",
)

app.include_router(health_router)
app.include_router(doctor_router, prefix="/api")
app.include_router(patient_router, prefix="/api")

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    logger.warning("AppException [%d] %s: %s", exc.status_code, request.url.path, exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning("Validation error on %s: %s", request.url.path, exc.errors())
    return JSONResponse(
        status_code=422,
        content=jsonable_encoder({"error": "Invalid data", "detail": exc.errors()})
    )

@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.error("Database error on %s: %s", request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Database error"}
    )