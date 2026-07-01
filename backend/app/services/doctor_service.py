import logging
import math
from typing import Optional

from fastapi import Depends

from app.models.address import Address
from app.models.doctor import Doctor
from app.repositories.doctor_repository import DoctorRepository, get_doctor_repository
from app.schemas.doctor_schema import DoctorCreate, DoctorPatch
from app.core.exceptions import ConflictException, NotFoundException
from app.models.enums import Speciality
from app.schemas.shared import PaginatedResponse

logger = logging.getLogger(__name__)

DOCTORS_LIST_MAX_LIMIT = 100

class DoctorService:

    def __init__(self, repo: DoctorRepository):
        self.repo = repo

    async def assert_unique_email(self, doctor_email: str):
        if await self.repo.get_by_email(doctor_email):
            logger.warning("Conflict: Email '%s' already registered", doctor_email)
            raise ConflictException("E-mail already exists.")
        
    async def assert_unique_crm(self, doctor_crm: str):
        if await self.repo.get_by_crm(doctor_crm):
            logger.warning("Conflict: CRM '%s' already registered", doctor_crm)
            raise ConflictException("CRM already exists.")
        
    async def get_by_id(self, doctor_id: int) -> Doctor:
        doctor = await self.repo.get_by_id(doctor_id)
        if not doctor:
            raise NotFoundException("Doctor not found.")
        return doctor
    
    async def list_doctors(
            self,
            page: int,
            size: Optional[int] = None,
            search: Optional[str] = None,
            speciality: Optional[Speciality] = None
    ) -> PaginatedResponse:
        
        effective_size = size if size is not None else DOCTORS_LIST_MAX_LIMIT
        offset = (page - 1) * effective_size

        total = await self.repo.count(search=search, speciality=speciality)
        doctors = await self.repo.get_all(
            offset=offset,
            limit=effective_size,
            search=search,
            speciality=speciality
        )

        return PaginatedResponse(
            items=doctors,
            total=total,
            page=page,
            size=effective_size,
            pages=math.ceil(total / effective_size) if total else 0,
            has_next=page * effective_size < total,
            has_prev=page > 1
        )

    async def create(self, data: DoctorCreate) -> Doctor:

        await self.assert_unique_email(data.email)
        
        await self.assert_unique_crm(data.crm)
           
        address = Address(**data.address.model_dump()) if data.address else None

        doctor = Doctor(
            name=data.name,
            email=data.email,
            crm=data.crm,
            birth_date=data.birth_date,
            phone=data.phone,
            speciality=data.speciality,
            address=address
        )

        saved = await self.repo.save(doctor)

        logger.info("Doctor created id=%s name=%s", saved.id, saved.name)

        return saved
    
    async def patch(self, doctor_id: int, data: DoctorPatch) -> Doctor:

        doctor = await self.get_by_id(doctor_id)
        
        if data.email and data.email != doctor.email:
            await self.assert_unique_email(data.email)
        
        return await self.repo.patch(doctor, data)
    
    async def deactivate(self, doctor_id: int) -> None:

        doctor = await self.get_by_id(doctor_id)
        
        if not doctor.is_active:
            raise ConflictException("Doctor already inactive")
        
        await self.repo.deactivate(doctor)
        logger.info("Doctor soft-deleted id=%s", doctor.id)

def get_doctor_service(repo: DoctorRepository = Depends(get_doctor_repository)) -> DoctorService:
    return DoctorService(repo=repo)
