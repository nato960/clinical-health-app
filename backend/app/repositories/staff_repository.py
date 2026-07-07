from typing import Optional

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from app.core.database import get_db
from app.models.address import Address
from app.models.staff import Staff
from app.schemas.staff_schema import StaffPatch
from app.models.enums import Sector

class StaffRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(
            self,
            offset: int,
            limit: int,
            search: Optional[str] = None,
            sector: Optional[Sector] = None
    ) -> list[Staff]:

        query = (
            select(Staff)
            .where(Staff.is_active == True)
            .order_by(Staff.name)
        )

        if search:
            query = query.where(Staff.name.ilike(f"%{search}%"))

        if sector:
            query = query.where(Staff.sector == sector)

        query = await self.db.execute(query.offset(offset).limit(limit))

        return query.scalars().all()

    async def count(
            self,
            search: Optional[str],
            sector: Optional[Sector]
    ) -> int:

        query = (
            select(func.count())
            .select_from(Staff)
            .where(Staff.is_active == True)
        )

        if search:
            query = query.where(Staff.name.ilike(f"%{search}%"))

        if sector:
            query = query.where(Staff.sector == sector)

        return await self.db.scalar(query)

    async def get_by_id(self, staff_id: int, active_only: bool = True) -> Staff:

        query = (
            select(Staff)
            .where(Staff.id == staff_id)
        )

        if active_only:
            query = query.where(Staff.is_active == True)

        result = await self.db.execute(query)

        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Staff | None:

        query = await self.db.execute(
            select(Staff)
            .where(Staff.email == email)
        )

        return query.scalar_one_or_none()

    async def get_by_cpf(self, cpf: str) -> Staff | None:

        query = await self.db.execute(
            select(Staff)
            .where(Staff.cpf == cpf)
        )

        return query.scalar_one_or_none()

    async def save(self, staff: Staff) -> Staff:

        self.db.add(staff)
        await self.db.commit()
        await self.db.refresh(staff)

        return staff

    async def patch(self, staff: Staff, data: StaffPatch) -> Staff:
        update_data = data.model_dump(exclude_unset=True)

        if "address" in update_data:
            address_data = update_data.pop("address")

            if address_data is None:
                staff.address = None
            elif staff.address:
                for key, value in address_data.items():
                    setattr(staff.address, key, value)
            else:
                address = Address(**address_data)
                self.db.add(address)
                await self.db.flush()
                staff.address_id = address.id

        for key, value in update_data.items():
            setattr(staff, key, value)

        await self.db.commit()
        await self.db.refresh(staff)

        return staff

    async def deactivate(self, staff: Staff) -> None:
        staff.is_active = False
        await self.db.commit()

def get_staff_repository(db: AsyncSession = Depends(get_db)) -> StaffRepository:
    return StaffRepository(db=db)
