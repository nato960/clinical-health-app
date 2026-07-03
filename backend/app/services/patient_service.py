import logging
import math
from typing import Optional

from fastapi import Depends

from app.models.address import Address
from app.models.patient import Patient
from app.repositories.patient_repository import PatientRepository, get_patient_repository
from app.schemas.patient_schema import PatientCreate, PatientPatch
from app.core.exceptions import ConflictException, NotFoundException
from app.schemas.shared import PaginatedResponse

logger = logging.getLogger(__name__)

PATIENTS_LIST_MAX_LIMIT = 100

class PatientService:

    def __init__(self, repo: PatientRepository):
        self.repo = repo

    async def assert_unique_email(self, patient_email: str):
        if await self.repo.get_by_email(patient_email):
            logger.warning("Conflict: Email '%s' already registered", patient_email)
            raise ConflictException("E-mail already exists.")

    async def assert_unique_cpf(self, patient_cpf: str):
        if await self.repo.get_by_cpf(patient_cpf):
            logger.warning("Conflict: CPF '%s' already registered", patient_cpf)
            raise ConflictException("CPF already exists.")

    async def get_by_id(self, patient_id: int, active_only: bool = True) -> Patient:
        patient = await self.repo.get_by_id(patient_id, active_only)
        if not patient:
            raise NotFoundException("Patient not found.")
        return patient

    async def list_patients(
            self,
            page: int,
            size: Optional[int] = None,
            search: Optional[str] = None
    ) -> PaginatedResponse:

        effective_size = size if size is not None else PATIENTS_LIST_MAX_LIMIT
        offset = (page - 1) * effective_size

        total = await self.repo.count(search=search)
        patients = await self.repo.get_all(
            offset=offset,
            limit=effective_size,
            search=search
        )

        return PaginatedResponse(
            items=patients,
            total=total,
            page=page,
            size=effective_size,
            pages=math.ceil(total / effective_size) if total else 0,
            has_next=page * effective_size < total,
            has_prev=page > 1
        )

    async def create(self, data: PatientCreate) -> Patient:

        await self.assert_unique_email(data.email)

        await self.assert_unique_cpf(data.cpf)

        address = Address(**data.address.model_dump()) if data.address else None

        patient = Patient(
            name=data.name,
            email=data.email,
            cpf=data.cpf,
            birth_date=data.birth_date,
            phone=data.phone,
            address=address
        )

        saved = await self.repo.save(patient)

        logger.info("Patient created id=%s name=%s", saved.id, saved.name)

        return saved

    async def patch(self, patient_id: int, data: PatientPatch) -> Patient:

        patient = await self.get_by_id(patient_id)

        if data.email and data.email != patient.email:
            await self.assert_unique_email(data.email)

        return await self.repo.patch(patient, data)

    async def deactivate(self, patient_id: int) -> None:

        patient = await self.get_by_id(patient_id, active_only=False)

        if not patient.is_active:
            raise ConflictException("Patient already inactive")

        await self.repo.deactivate(patient)
        logger.info("Patient soft-deleted id=%s", patient.id)

def get_patient_service(repo: PatientRepository = Depends(get_patient_repository)) -> PatientService:
    return PatientService(repo=repo)
