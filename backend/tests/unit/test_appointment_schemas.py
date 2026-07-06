from datetime import datetime, timedelta, timezone

from pydantic import ValidationError
import pytest

from app.models.enums import CancellationReason, Speciality
from app.schemas.appointment_schema import (
    AppointmentCancel,
    AppointmentReschedule,
    AppointmentSchedule,
)


def make_valid_schedule(**overrides):
    data = {
        "patient_id": 1,
        "date": datetime(2026, 7, 6, 10, 0, 0),
    }
    return {**data, **overrides}


# --- AppointmentSchedule ---

def test_schedule_requires_patient_id():
    data = make_valid_schedule()
    del data["patient_id"]
    with pytest.raises(ValidationError):
        AppointmentSchedule(**data)


def test_schedule_requires_date():
    data = make_valid_schedule()
    del data["date"]
    with pytest.raises(ValidationError):
        AppointmentSchedule(**data)


def test_schedule_doctor_id_and_speciality_are_optional():
    AppointmentSchedule(**make_valid_schedule())


def test_schedule_with_doctor_id_only_is_valid():
    AppointmentSchedule(**make_valid_schedule(doctor_id=5))


def test_schedule_with_speciality_only_is_valid():
    AppointmentSchedule(**make_valid_schedule(speciality=Speciality.CARDIOLOGY))


def test_schedule_rejects_timezone_aware_date():
    aware_date = datetime(2026, 7, 6, 10, 0, 0, tzinfo=timezone.utc)
    with pytest.raises(ValidationError):
        AppointmentSchedule(**make_valid_schedule(date=aware_date))


def test_schedule_keeps_naive_date_unchanged():
    naive_date = datetime(2026, 7, 6, 10, 0, 0)
    schedule = AppointmentSchedule(**make_valid_schedule(date=naive_date))
    assert schedule.date == naive_date


# --- AppointmentReschedule ---

def test_reschedule_allows_empty_payload():
    AppointmentReschedule()


def test_reschedule_allows_date_only():
    AppointmentReschedule(date=datetime(2026, 7, 6, 11, 0, 0))


def test_reschedule_allows_doctor_id_only():
    AppointmentReschedule(doctor_id=7)


def test_reschedule_allows_both():
    AppointmentReschedule(doctor_id=7, date=datetime(2026, 7, 6, 11, 0, 0))


def test_reschedule_rejects_timezone_aware_date():
    aware_date = datetime(2026, 7, 6, 11, 0, 0, tzinfo=timezone.utc)
    with pytest.raises(ValidationError):
        AppointmentReschedule(date=aware_date)


def test_reschedule_has_no_patient_id_field():
    reschedule = AppointmentReschedule(doctor_id=7)
    assert not hasattr(reschedule, "patient_id")


# --- AppointmentCancel ---

def test_cancel_accepts_valid_reason():
    AppointmentCancel(cancellation_reason=CancellationReason.PATIENT_CANCELED)


def test_cancel_rejects_invalid_reason():
    with pytest.raises(ValidationError):
        AppointmentCancel(cancellation_reason="NOT_A_REASON")


def test_cancel_requires_reason():
    with pytest.raises(ValidationError):
        AppointmentCancel()
