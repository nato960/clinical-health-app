from typing import Optional

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from app.core.database import get_db
from app.models.address import Address
from app.models.doctor import Doctor
from app.schemas.doctor_schema import DoctorPatch
from app.models.enums import Speciality

class DoctorRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(
            self,
            offset: int,
            limit: int,
            search: Optional[str] = None,
            speciality: Optional[Speciality] = None
    ) -> list[Doctor]:

        query = (
            select(Doctor)
            .where(Doctor.is_active == True)
            .order_by(Doctor.name)
        )

        if search:
            query = query.where(Doctor.name.ilike(f"%{search}%"))

        if speciality:
            query = query.where(Doctor.speciality == speciality)
        
        query = await self.db.execute(query.offset(offset).limit(limit))

        return query.scalars().all()
    
    async def count(
            self,
            search: str,
            speciality: Optional[Speciality]
    ) -> int:
        
        query = (
            select(func.count())
            .select_from(Doctor)
            .where(Doctor.is_active == True)
        )

        if search:
            query = query.where(Doctor.name.ilike(f"%{search}%"))

        if speciality:
            query = query.where(Doctor.speciality == speciality)

        return await self.db.scalar(query)

    async def get_by_id(self, doctor_id: int) -> Doctor:

        query = await self.db.execute(
            select(Doctor)
            .where(Doctor.id == doctor_id)
        )

        return query.scalar_one_or_none()
    
    async def get_by_email(self, email: str) -> Doctor | None:
        
        query = await self.db.execute(
            select(Doctor)
            .where(Doctor.email == email)
        )

        return query.scalar_one_or_none()
    
    async def get_by_crm(self, crm: str) -> Doctor | None:

        query = await self.db.execute(
            select(Doctor)
            .where(Doctor.crm == crm)
        )

        return query.scalar_one_or_none()
    
    async def save(self, doctor: Doctor) -> Doctor:

        self.db.add(doctor)
        await self.db.commit()
        await self.db.refresh(doctor)

        return doctor
    
    async def patch(self, doctor: Doctor, data: DoctorPatch) -> Doctor:
        update_data = data.model_dump(exclude_unset=True)

        if "address" in update_data:
            address_data = update_data.pop("address")

            if address_data is None:
                doctor.address = None
            elif doctor.address:
                for key, value in address_data.items():
                    setattr(doctor.address, key, value)
            else:
                address = Address(**address_data)
                self.db.add(address)
                await self.db.flush()
                doctor.address_id = address.id
        
        for key, value in update_data.items():
            setattr(doctor, key, value)

        await self.db.commit()
        await self.db.refresh(doctor)

        return doctor
    
    async def deactivate(self, doctor: Doctor) -> None:
        doctor.is_active = False
        await self.db.commit()

def get_doctor_repository(db: AsyncSession = Depends(get_db)) -> DoctorRepository:
    return DoctorRepository(db=db)
