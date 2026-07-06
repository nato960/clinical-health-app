from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import BusinessException, ConflictException, NotFoundException
from app.models.enums import CancellationReason, Speciality
from app.schemas.appointment_schema import AppointmentCancel, AppointmentReschedule, AppointmentSchedule
from app.services.appointment_service import AppointmentService


def future_valid_datetime(extra_days: int = 2, hour: int = 10, minute: int = 0, second: int = 0) -> datetime:
    """A datetime far enough ahead to satisfy the 30-min lead time, on a Mon-Sat business hour."""
    candidate = (datetime.now() + timedelta(days=extra_days)).replace(
        hour=hour, minute=minute, second=second, microsecond=0
    )
    while candidate.weekday() == 6:  # Sunday
        candidate += timedelta(days=1)
    return candidate


def make_doctor(**kwargs):
    doctor = MagicMock()
    doctor.id = kwargs.get("id", 10)
    doctor.is_active = kwargs.get("is_active", True)
    return doctor


def make_patient(**kwargs):
    patient = MagicMock()
    patient.id = kwargs.get("id", 20)
    patient.is_active = kwargs.get("is_active", True)
    return patient


def make_appointment(**kwargs):
    appointment = MagicMock()
    appointment.id = kwargs.get("id", 1)
    appointment.doctor_id = kwargs.get("doctor_id", 10)
    appointment.patient_id = kwargs.get("patient_id", 20)
    appointment.date = kwargs.get("date", future_valid_datetime())
    appointment.cancellation_reason = kwargs.get("cancellation_reason", None)
    return appointment


def make_service():
    repo = MagicMock()
    doctor_repo = MagicMock()
    patient_repo = MagicMock()

    repo.get_by_id = AsyncMock(return_value=None)
    repo.save = AsyncMock(side_effect=lambda appt: appt)
    repo.cancel = AsyncMock()
    repo.doctor_has_conflict = AsyncMock(return_value=False)
    repo.patient_has_conflict = AsyncMock(return_value=False)
    repo.get_available_doctors = AsyncMock(return_value=[])
    repo.get_all = AsyncMock(return_value=[])
    repo.count = AsyncMock(return_value=0)

    doctor_repo.get_by_id = AsyncMock(return_value=make_doctor())
    patient_repo.get_by_id = AsyncMock(return_value=make_patient())

    return AppointmentService(repo, doctor_repo, patient_repo)


# --- schedule ---

async def test_schedule_with_explicit_doctor_succeeds():
    service = make_service()
    data = AppointmentSchedule(patient_id=20, doctor_id=10, date=future_valid_datetime())
    result = await service.schedule(data)
    assert result.doctor_id == 10
    assert result.patient_id == 20
    service.repo.save.assert_called_once()


async def test_schedule_missing_patient_raises_not_found():
    service = make_service()
    service.patient_repo.get_by_id = AsyncMock(return_value=None)
    data = AppointmentSchedule(patient_id=999, doctor_id=10, date=future_valid_datetime())
    with pytest.raises(NotFoundException):
        await service.schedule(data)


async def test_schedule_missing_doctor_raises_not_found():
    service = make_service()
    service.doctor_repo.get_by_id = AsyncMock(return_value=None)
    data = AppointmentSchedule(patient_id=20, doctor_id=999, date=future_valid_datetime())
    with pytest.raises(NotFoundException):
        await service.schedule(data)


async def test_schedule_without_doctor_or_speciality_raises_business_exception():
    service = make_service()
    data = AppointmentSchedule(patient_id=20, date=future_valid_datetime())
    with pytest.raises(BusinessException):
        await service.schedule(data)


async def test_schedule_without_doctor_and_no_available_candidates_raises_business_exception():
    service = make_service()
    service.repo.get_available_doctors = AsyncMock(return_value=[])
    data = AppointmentSchedule(patient_id=20, date=future_valid_datetime(), speciality=Speciality.CARDIOLOGY)
    with pytest.raises(BusinessException):
        await service.schedule(data)


async def test_schedule_without_doctor_auto_assigns_from_candidates():
    service = make_service()
    candidate = make_doctor(id=42)
    service.repo.get_available_doctors = AsyncMock(return_value=[candidate])
    data = AppointmentSchedule(patient_id=20, date=future_valid_datetime(), speciality=Speciality.CARDIOLOGY)
    result = await service.schedule(data)
    assert result.doctor_id == 42


# --- validators (schedule failure paths) ---

async def test_schedule_on_sunday_raises_business_exception():
    service = make_service()
    when = future_valid_datetime()
    while when.weekday() != 6:
        when += timedelta(days=1)
    data = AppointmentSchedule(patient_id=20, doctor_id=10, date=when)
    with pytest.raises(BusinessException):
        await service.schedule(data)


async def test_schedule_before_opening_hour_raises_business_exception():
    service = make_service()
    when = future_valid_datetime(hour=6)
    data = AppointmentSchedule(patient_id=20, doctor_id=10, date=when)
    with pytest.raises(BusinessException):
        await service.schedule(data)


async def test_schedule_after_closing_hour_raises_business_exception():
    service = make_service()
    when = future_valid_datetime(hour=19)
    data = AppointmentSchedule(patient_id=20, doctor_id=10, date=when)
    with pytest.raises(BusinessException):
        await service.schedule(data)


async def test_schedule_at_exactly_18_hour_is_allowed():
    # Preserves the original Java quirk: hour == 18 passes even though the clinic "closes" at 18:00.
    service = make_service()
    when = future_valid_datetime(hour=18)
    data = AppointmentSchedule(patient_id=20, doctor_id=10, date=when)
    await service.schedule(data)


# --- time slot rounding ---

async def test_schedule_rounds_down_minute_between_0_and_30():
    service = make_service()
    when = future_valid_datetime(minute=15)
    data = AppointmentSchedule(patient_id=20, doctor_id=10, date=when)
    result = await service.schedule(data)
    assert result.date.minute == 0


async def test_schedule_rounds_down_minute_above_30():
    service = make_service()
    when = future_valid_datetime(minute=45)
    data = AppointmentSchedule(patient_id=20, doctor_id=10, date=when)
    result = await service.schedule(data)
    assert result.date.minute == 30


async def test_schedule_keeps_exact_hour_slot_unchanged():
    service = make_service()
    when = future_valid_datetime(minute=0)
    data = AppointmentSchedule(patient_id=20, doctor_id=10, date=when)
    result = await service.schedule(data)
    assert result.date.minute == 0


async def test_schedule_keeps_exact_half_hour_slot_unchanged():
    service = make_service()
    when = future_valid_datetime(minute=30)
    data = AppointmentSchedule(patient_id=20, doctor_id=10, date=when)
    result = await service.schedule(data)
    assert result.date.minute == 30


async def test_schedule_strips_seconds_and_microseconds():
    service = make_service()
    when = future_valid_datetime(minute=0, second=45)
    data = AppointmentSchedule(patient_id=20, doctor_id=10, date=when)
    result = await service.schedule(data)
    assert result.date.second == 0
    assert result.date.microsecond == 0


async def test_reschedule_rounds_down_new_date():
    service = make_service()
    appointment = make_appointment()
    service.repo.get_by_id = AsyncMock(return_value=appointment)
    when = future_valid_datetime(extra_days=3, minute=20)
    result = await service.reschedule(1, AppointmentReschedule(date=when))
    assert result.date.minute == 0


async def test_schedule_less_than_30_minutes_ahead_raises_business_exception():
    service = make_service()
    when = (datetime.now() + timedelta(minutes=10)).replace(second=0, microsecond=0)
    if when.hour < 7 or when.hour > 18 or when.weekday() == 6:
        pytest.skip("current time makes this an unreliable window for this specific check")
    data = AppointmentSchedule(patient_id=20, doctor_id=10, date=when)
    with pytest.raises(BusinessException):
        await service.schedule(data)


async def test_schedule_with_inactive_doctor_raises_business_exception():
    service = make_service()
    service.doctor_repo.get_by_id = AsyncMock(return_value=make_doctor(is_active=False))
    data = AppointmentSchedule(patient_id=20, doctor_id=10, date=future_valid_datetime())
    with pytest.raises(BusinessException):
        await service.schedule(data)


async def test_schedule_with_inactive_patient_raises_business_exception():
    service = make_service()
    service.patient_repo.get_by_id = AsyncMock(return_value=make_patient(is_active=False))
    data = AppointmentSchedule(patient_id=20, doctor_id=10, date=future_valid_datetime())
    with pytest.raises(BusinessException):
        await service.schedule(data)


async def test_schedule_with_doctor_conflict_raises_business_exception():
    service = make_service()
    service.repo.doctor_has_conflict = AsyncMock(return_value=True)
    data = AppointmentSchedule(patient_id=20, doctor_id=10, date=future_valid_datetime())
    with pytest.raises(BusinessException):
        await service.schedule(data)


async def test_schedule_with_patient_day_conflict_raises_business_exception():
    service = make_service()
    service.repo.patient_has_conflict = AsyncMock(return_value=True)
    data = AppointmentSchedule(patient_id=20, doctor_id=10, date=future_valid_datetime())
    with pytest.raises(BusinessException):
        await service.schedule(data)


async def test_schedule_converts_integrity_error_into_conflict_exception():
    service = make_service()
    service.repo.save = AsyncMock(side_effect=IntegrityError("stmt", {}, Exception("unique violation")))
    data = AppointmentSchedule(patient_id=20, doctor_id=10, date=future_valid_datetime())
    with pytest.raises(ConflictException):
        await service.schedule(data)


async def test_schedule_computes_full_day_window_for_patient_conflict_check():
    service = make_service()
    when = future_valid_datetime(minute=30)
    data = AppointmentSchedule(patient_id=20, doctor_id=10, date=when)
    await service.schedule(data)
    args = service.repo.patient_has_conflict.call_args.args
    window_start, window_end = args[1], args[2]
    assert (window_start.hour, window_start.minute) == (7, 0)
    assert (window_end.hour, window_end.minute) == (18, 0)


async def test_schedule_with_mismatched_doctor_speciality_raises_business_exception():
    service = make_service()
    doctor = make_doctor(id=10)
    doctor.speciality = Speciality.CARDIOLOGY
    service.doctor_repo.get_by_id = AsyncMock(return_value=doctor)
    data = AppointmentSchedule(
        patient_id=20, doctor_id=10, date=future_valid_datetime(), speciality=Speciality.DERMATOLOGY
    )
    with pytest.raises(BusinessException):
        await service.schedule(data)


async def test_schedule_with_matching_doctor_speciality_succeeds():
    service = make_service()
    doctor = make_doctor(id=10)
    doctor.speciality = Speciality.CARDIOLOGY
    service.doctor_repo.get_by_id = AsyncMock(return_value=doctor)
    data = AppointmentSchedule(
        patient_id=20, doctor_id=10, date=future_valid_datetime(), speciality=Speciality.CARDIOLOGY
    )
    result = await service.schedule(data)
    assert result.doctor_id == 10


# --- reschedule ---

async def test_reschedule_fetches_appointment_ignoring_cancellation_state():
    service = make_service()
    appointment = make_appointment()
    service.repo.get_by_id = AsyncMock(return_value=appointment)
    await service.reschedule(1, AppointmentReschedule(date=future_valid_datetime(extra_days=3)))
    service.repo.get_by_id.assert_called_once_with(1, False)


async def test_reschedule_with_unknown_doctor_raises_not_found():
    service = make_service()
    service.repo.get_by_id = AsyncMock(return_value=make_appointment())
    service.doctor_repo.get_by_id = AsyncMock(return_value=None)
    with pytest.raises(NotFoundException):
        await service.reschedule(1, AppointmentReschedule(doctor_id=999))


async def test_reschedule_only_updates_provided_fields():
    service = make_service()
    appointment = make_appointment(doctor_id=10)
    service.repo.get_by_id = AsyncMock(return_value=appointment)
    new_date = future_valid_datetime(extra_days=3)
    result = await service.reschedule(1, AppointmentReschedule(date=new_date))
    assert result.date == new_date
    assert result.doctor_id == 10


async def test_reschedule_excludes_own_id_from_conflict_checks():
    service = make_service()
    appointment = make_appointment(id=99)
    service.repo.get_by_id = AsyncMock(return_value=appointment)
    await service.reschedule(99, AppointmentReschedule(date=future_valid_datetime(extra_days=3)))
    args = service.repo.doctor_has_conflict.call_args.args
    assert args[-1] == 99


async def test_reschedule_already_cancelled_raises_conflict():
    service = make_service()
    appointment = make_appointment(cancellation_reason=CancellationReason.OTHER)
    service.repo.get_by_id = AsyncMock(return_value=appointment)
    with pytest.raises(ConflictException):
        await service.reschedule(1, AppointmentReschedule(date=future_valid_datetime(extra_days=3)))
    service.repo.save.assert_not_called()


async def test_reschedule_with_explicit_null_date_raises_business_exception():
    service = make_service()
    appointment = make_appointment()
    service.repo.get_by_id = AsyncMock(return_value=appointment)
    with pytest.raises(BusinessException):
        await service.reschedule(1, AppointmentReschedule(date=None))


async def test_reschedule_with_explicit_null_doctor_id_raises_business_exception():
    service = make_service()
    appointment = make_appointment()
    service.repo.get_by_id = AsyncMock(return_value=appointment)
    with pytest.raises(BusinessException):
        await service.reschedule(1, AppointmentReschedule(doctor_id=None))


# --- cancel ---

async def test_cancel_already_cancelled_raises_conflict():
    service = make_service()
    appointment = make_appointment(cancellation_reason=CancellationReason.OTHER)
    service.repo.get_by_id = AsyncMock(return_value=appointment)
    with pytest.raises(ConflictException):
        await service.cancel(1, AppointmentCancel(cancellation_reason=CancellationReason.PATIENT_CANCELED))


async def test_cancel_success_calls_repo_cancel():
    service = make_service()
    appointment = make_appointment(cancellation_reason=None)
    service.repo.get_by_id = AsyncMock(return_value=appointment)
    service.repo.cancel = AsyncMock(return_value=appointment)
    await service.cancel(1, AppointmentCancel(cancellation_reason=CancellationReason.DOCTOR_CANCELED))
    service.repo.cancel.assert_called_once_with(appointment, CancellationReason.DOCTOR_CANCELED)


# --- list_appointments: pagination ---

async def test_list_appointments_empty():
    service = make_service()
    result = await service.list_appointments(page=1, size=10)
    assert result.total == 0
    assert result.pages == 0
    assert result.has_next is False
    assert result.has_prev is False


async def test_list_appointments_has_next():
    service = make_service()
    service.repo.count = AsyncMock(return_value=25)
    result = await service.list_appointments(page=1, size=10)
    assert result.pages == 3
    assert result.has_next is True
    assert result.has_prev is False


async def test_list_appointments_has_prev():
    service = make_service()
    service.repo.count = AsyncMock(return_value=25)
    result = await service.list_appointments(page=3, size=10)
    assert result.has_next is False
    assert result.has_prev is True
