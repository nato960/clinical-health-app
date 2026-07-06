from datetime import datetime
from typing import Optional

from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.enums import CancellationReason, Speciality


class AppointmentRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(
            self,
            offset: int,
            limit: int,
            doctor_id: Optional[int] = None,
            patient_id: Optional[int] = None,
            active_only: bool = True
    ) -> list[Appointment]:

        query = (
            select(Appointment)
            .order_by(Appointment.date)
        )

        if active_only:
            query = query.where(Appointment.cancellation_reason.is_(None))

        if doctor_id is not None:
            query = query.where(Appointment.doctor_id == doctor_id)

        if patient_id is not None:
            query = query.where(Appointment.patient_id == patient_id)

        query = await self.db.execute(query.offset(offset).limit(limit))

        return query.scalars().all()

    async def count(
            self,
            doctor_id: Optional[int] = None,
            patient_id: Optional[int] = None,
            active_only: bool = True
    ) -> int:

        query = (
            select(func.count())
            .select_from(Appointment)
        )

        if active_only:
            query = query.where(Appointment.cancellation_reason.is_(None))

        if doctor_id is not None:
            query = query.where(Appointment.doctor_id == doctor_id)

        if patient_id is not None:
            query = query.where(Appointment.patient_id == patient_id)

        return await self.db.scalar(query)

    async def get_by_id(self, appointment_id: int, active_only: bool = True) -> Appointment | None:

        query = (
            select(Appointment)
            .where(Appointment.id == appointment_id)
        )

        if active_only:
            query = query.where(Appointment.cancellation_reason.is_(None))

        result = await self.db.execute(query)

        return result.scalar_one_or_none()

    async def doctor_has_conflict(
            self,
            doctor_id: int,
            when: datetime,
            exclude_id: Optional[int] = None
    ) -> bool:

        query = (
            select(Appointment.id)
            .where(
                Appointment.doctor_id == doctor_id,
                Appointment.date == when,
                Appointment.cancellation_reason.is_(None)
            )
        )

        return await self._exists(query, exclude_id)

    async def patient_has_conflict(
            self,
            patient_id: int,
            window_start: datetime,
            window_end: datetime,
            exclude_id: Optional[int] = None
    ) -> bool:

        query = (
            select(Appointment.id)
            .where(
                Appointment.patient_id == patient_id,
                Appointment.date.between(window_start, window_end),
                Appointment.cancellation_reason.is_(None)
            )
        )

        return await self._exists(query, exclude_id)

    async def _exists(self, query, exclude_id: Optional[int] = None) -> bool:
        if exclude_id is not None:
            query = query.where(Appointment.id != exclude_id)

        result = await self.db.execute(query.limit(1))

        return result.scalar_one_or_none() is not None

    async def get_available_doctors(self, speciality: Speciality, when: datetime) -> list[Doctor]:

        busy_doctor_ids = (
            select(Appointment.doctor_id)
            .where(
                Appointment.date == when,
                Appointment.cancellation_reason.is_(None)
            )
        )

        query = (
            select(Doctor)
            .where(
                Doctor.speciality == speciality,
                Doctor.is_active == True,
                Doctor.id.notin_(busy_doctor_ids)
            )
        )

        result = await self.db.execute(query)

        return list(result.scalars().all())

    async def save(self, appointment: Appointment) -> Appointment:

        self.db.add(appointment)
        await self.db.commit()
        await self.db.refresh(appointment)

        return appointment

    async def cancel(self, appointment: Appointment, reason: CancellationReason) -> Appointment:

        appointment.cancellation_reason = reason
        await self.db.commit()
        await self.db.refresh(appointment)

        return appointment


def get_appointment_repository(db: AsyncSession = Depends(get_db)) -> AppointmentRepository:
    return AppointmentRepository(db=db)
