import logging
import math
import random
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import BusinessException, ConflictException, NotFoundException
from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.enums import Speciality
from app.models.patient import Patient
from app.repositories.appointment_repository import AppointmentRepository, get_appointment_repository
from app.repositories.doctor_repository import DoctorRepository, get_doctor_repository
from app.repositories.patient_repository import PatientRepository, get_patient_repository
from app.schemas.appointment_schema import AppointmentCancel, AppointmentReschedule, AppointmentSchedule
from app.schemas.shared import PaginatedResponse

logger = logging.getLogger(__name__)

APPOINTMENTS_LIST_MAX_LIMIT = 100

OPENING_HOUR = 7
CLOSING_HOUR = 18
MIN_LEAD_TIME_MINUTES = 30
SLOT_INTERVAL_MINUTES = 30


class AppointmentService:

    def __init__(self, repo: AppointmentRepository, doctor_repo: DoctorRepository, patient_repo: PatientRepository):
        self.repo = repo
        self.doctor_repo = doctor_repo
        self.patient_repo = patient_repo

    async def get_by_id(self, appointment_id: int, active_only: bool = True) -> Appointment:
        appointment = await self.repo.get_by_id(appointment_id, active_only)
        if not appointment:
            raise NotFoundException("Appointment not found.")
        return appointment

    async def list_appointments(
            self,
            page: int,
            size: Optional[int] = None,
            doctor_id: Optional[int] = None,
            patient_id: Optional[int] = None,
            active_only: bool = True
    ) -> PaginatedResponse:

        effective_size = size if size is not None else APPOINTMENTS_LIST_MAX_LIMIT
        offset = (page - 1) * effective_size

        total = await self.repo.count(doctor_id=doctor_id, patient_id=patient_id, active_only=active_only)
        appointments = await self.repo.get_all(
            offset=offset,
            limit=effective_size,
            doctor_id=doctor_id,
            patient_id=patient_id,
            active_only=active_only
        )

        return PaginatedResponse(
            items=appointments,
            total=total,
            page=page,
            size=effective_size,
            pages=math.ceil(total / effective_size) if total else 0,
            has_next=page * effective_size < total,
            has_prev=page > 1
        )

    async def schedule(self, data: AppointmentSchedule) -> Appointment:

        patient = await self.patient_repo.get_by_id(data.patient_id, active_only=False)
        if not patient:
            raise NotFoundException("Patient not found.")

        rounded_date = self._round_to_slot(data.date)
        doctor = await self._resolve_doctor(data.doctor_id, data.speciality, rounded_date)

        appointment = Appointment(
            patient_id=patient.id,
            doctor_id=doctor.id,
            date=rounded_date,
            speciality=data.speciality
        )

        await self._validate(appointment, exclude_id=appointment.id, doctor=doctor, patient=patient)

        saved = await self._save(appointment)

        logger.info(
            "Appointment scheduled id=%s doctor_id=%s patient_id=%s date=%s",
            saved.id, saved.doctor_id, saved.patient_id, saved.date
        )

        return saved

    async def _resolve_doctor(
            self,
            doctor_id: Optional[int],
            speciality: Optional[Speciality],
            when: datetime
    ) -> Doctor:

        if doctor_id is not None:
            doctor = await self.doctor_repo.get_by_id(doctor_id, active_only=False)
            if not doctor:
                raise NotFoundException("Doctor not found.")
            if speciality is not None and doctor.speciality != speciality:
                raise BusinessException("Doctor's speciality does not match the requested speciality.")
            return doctor

        if speciality is None:
            raise BusinessException("Speciality must be chosen when there is no chosen doctor.")

        candidates = await self.repo.get_available_doctors(speciality, when)
        if not candidates:
            raise BusinessException("There is no doctor available on the chosen date.")

        return random.choice(candidates)

    async def reschedule(self, appointment_id: int, data: AppointmentReschedule) -> Appointment:

        appointment = await self.get_by_id(appointment_id, active_only=False)

        if appointment.cancellation_reason is not None:
            raise ConflictException("Cannot reschedule a cancelled appointment.")

        update_data = data.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            if value is None:
                raise BusinessException(f"'{key}' cannot be null.")

        if update_data.get("date") is not None:
            update_data["date"] = self._round_to_slot(update_data["date"])

        doctor = appointment.doctor
        if update_data.get("doctor_id") is not None:
            doctor = await self.doctor_repo.get_by_id(update_data["doctor_id"], active_only=False)
            if not doctor:
                raise NotFoundException("Doctor not found.")

        for key, value in update_data.items():
            setattr(appointment, key, value)

        await self._validate(appointment, exclude_id=appointment.id, doctor=doctor, patient=appointment.patient)

        saved = await self._save(appointment)

        logger.info("Appointment rescheduled id=%s doctor_id=%s date=%s", saved.id, saved.doctor_id, saved.date)

        return saved

    async def cancel(self, appointment_id: int, data: AppointmentCancel) -> Appointment:

        appointment = await self.get_by_id(appointment_id, active_only=False)

        if appointment.cancellation_reason is not None:
            logger.warning("Conflict: appointment id=%s already cancelled", appointment.id)
            raise ConflictException("Appointment already cancelled.")

        cancelled = await self.repo.cancel(appointment, data.cancellation_reason)

        logger.info("Appointment cancelled id=%s reason=%s", cancelled.id, cancelled.cancellation_reason)

        return cancelled

    async def _save(self, appointment: Appointment) -> Appointment:
        try:
            return await self.repo.save(appointment)
        except IntegrityError as exc:
            raise ConflictException("Doctor already has an appointment at this time.") from exc

    async def _validate(
            self,
            appointment: Appointment,
            exclude_id: Optional[int],
            doctor: Optional[Doctor] = None,
            patient: Optional[Patient] = None
    ) -> None:
        self._assert_opening_hours(appointment.date)
        self._assert_lead_time(appointment.date)
        await self._assert_active_doctor(appointment.doctor_id, doctor)
        await self._assert_active_patient(appointment.patient_id, patient)
        await self._assert_no_doctor_conflict(appointment.doctor_id, appointment.date, exclude_id)
        await self._assert_no_patient_day_conflict(appointment.patient_id, appointment.date, exclude_id)

    def _round_to_slot(self, when: datetime) -> datetime:
        floored_minute = (when.minute // SLOT_INTERVAL_MINUTES) * SLOT_INTERVAL_MINUTES
        return when.replace(minute=floored_minute, second=0, microsecond=0)

    def _assert_opening_hours(self, when: datetime) -> None:
        is_sunday = when.weekday() == 6
        is_before_opening = when.hour < OPENING_HOUR
        is_after_closing = when.hour > CLOSING_HOUR

        if is_sunday or is_before_opening or is_after_closing:
            raise BusinessException(
                "Consultations are allowed only from Monday to Saturday, between 07:00 and 18:00."
            )

    def _assert_lead_time(self, when: datetime) -> None:
        if when - datetime.now() < timedelta(minutes=MIN_LEAD_TIME_MINUTES):
            raise BusinessException("The appointment must be scheduled at least 30 minutes in advance.")

    async def _assert_active_doctor(self, doctor_id: int, doctor: Optional[Doctor] = None) -> None:
        if doctor is None:
            doctor = await self.doctor_repo.get_by_id(doctor_id, active_only=False)
        if not doctor or not doctor.is_active:
            raise BusinessException("An appointment can not be scheduled without an active doctor.")

    async def _assert_active_patient(self, patient_id: int, patient: Optional[Patient] = None) -> None:
        if patient is None:
            patient = await self.patient_repo.get_by_id(patient_id, active_only=False)
        if not patient or not patient.is_active:
            raise BusinessException("An appointment can not be scheduled without an active patient.")

    async def _assert_no_doctor_conflict(self, doctor_id: int, when: datetime, exclude_id: Optional[int]) -> None:
        if await self.repo.doctor_has_conflict(doctor_id, when, exclude_id):
            raise BusinessException("Doctor already has an appointment at this time.")

    async def _assert_no_patient_day_conflict(self, patient_id: int, when: datetime, exclude_id: Optional[int]) -> None:
        window_start = when.replace(hour=OPENING_HOUR, minute=0, second=0, microsecond=0)
        window_end = when.replace(hour=CLOSING_HOUR, minute=0, second=0, microsecond=0)

        if await self.repo.patient_has_conflict(patient_id, window_start, window_end, exclude_id):
            raise BusinessException("The patient already has an appointment on the date.")


def get_appointment_service(
        repo: AppointmentRepository = Depends(get_appointment_repository),
        doctor_repo: DoctorRepository = Depends(get_doctor_repository),
        patient_repo: PatientRepository = Depends(get_patient_repository)
) -> AppointmentService:
    return AppointmentService(repo=repo, doctor_repo=doctor_repo, patient_repo=patient_repo)
