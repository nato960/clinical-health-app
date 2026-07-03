from typing import Optional

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from app.core.database import get_db
from app.models.address import Address
from app.models.patient import Patient
from app.schemas.patient_schema import PatientPatch

class PatientRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(
            self,
            offset: int,
            limit: int,
            search: Optional[str] = None
    ) -> list[Patient]:

        query = (
            select(Patient)
            .where(Patient.is_active == True)
            .order_by(Patient.name)
        )

        if search:
            query = query.where(Patient.name.ilike(f"%{search}%"))

        query = await self.db.execute(query.offset(offset).limit(limit))

        return query.scalars().all()

    async def count(
            self,
            search: Optional[str]
    ) -> int:

        query = (
            select(func.count())
            .select_from(Patient)
            .where(Patient.is_active == True)
        )

        if search:
            query = query.where(Patient.name.ilike(f"%{search}%"))

        return await self.db.scalar(query)

    async def get_by_id(self, patient_id: int, active_only: bool = True) -> Patient:

        query = (
            select(Patient)
            .where(Patient.id == patient_id)
        )

        if active_only:
            query = query.where(Patient.is_active == True)

        result = await self.db.execute(query)

        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Patient | None:

        query = await self.db.execute(
            select(Patient)
            .where(Patient.email == email)
        )

        return query.scalar_one_or_none()

    async def get_by_cpf(self, cpf: str) -> Patient | None:

        query = await self.db.execute(
            select(Patient)
            .where(Patient.cpf == cpf)
        )

        return query.scalar_one_or_none()

    async def save(self, patient: Patient) -> Patient:

        self.db.add(patient)
        await self.db.commit()
        await self.db.refresh(patient)

        return patient

    async def patch(self, patient: Patient, data: PatientPatch) -> Patient:
        update_data = data.model_dump(exclude_unset=True)

        if "address" in update_data:
            address_data = update_data.pop("address")

            if address_data is None:
                patient.address = None
            elif patient.address:
                for key, value in address_data.items():
                    setattr(patient.address, key, value)
            else:
                address = Address(**address_data)
                self.db.add(address)
                await self.db.flush()
                patient.address_id = address.id

        for key, value in update_data.items():
            setattr(patient, key, value)

        await self.db.commit()
        await self.db.refresh(patient)

        return patient

    async def deactivate(self, patient: Patient) -> None:
        patient.is_active = False
        await self.db.commit()

def get_patient_repository(db: AsyncSession = Depends(get_db)) -> PatientRepository:
    return PatientRepository(db=db)
