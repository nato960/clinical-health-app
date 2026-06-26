from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.address import Address
from app.models.doctor import Doctor
from app.schemas.doctor_schema import DoctorPatch

class DoctorRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self) -> list[Doctor]:
        
        result = await self.db.execute(
            select(Doctor)
            .where(Doctor.is_active == True)
        )

        return result.scalars().all()

    async def get_by_id(self, doctor_id: int) -> Doctor:

        result = await self.db.execute(
            select(Doctor)
            .where(Doctor.id == doctor_id)
        )

        return result.scalar_one_or_none()
    
    async def get_by_email(self, email: str) -> Doctor | None:
        
        result = await self.db.execute(
            select(Doctor)
            .where(Doctor.email == email)
        )

        return result.scalar_one_or_none()
    
    async def get_by_crm(self, crm: str) -> Doctor | None:

        result = await self.db.execute(
            select(Doctor)
            .where(Doctor.crm == crm)
        )

        return result.scalar_one_or_none()
    
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
