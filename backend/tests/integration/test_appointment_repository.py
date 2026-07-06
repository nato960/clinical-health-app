from datetime import date, datetime

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.enums import CancellationReason, Speciality
from app.models.patient import Patient
from app.repositories.appointment_repository import AppointmentRepository


def make_doctor_data(**overrides):
    data = {
        "name": "Dr. Ana Ortiz",
        "email": "ana.ortiz@clinic.com",
        "crm": "CRM00001",
        "phone": "11999990000",
        "speciality": Speciality.CARDIOLOGY,
        "birth_date": date(1980, 1, 1),
    }
    return {**data, **overrides}


def make_patient_data(**overrides):
    data = {
        "name": "John Doe",
        "email": "john@doe.com",
        "cpf": "12345678900",
        "phone": "11988880000",
        "birth_date": date(1990, 1, 1),
    }
    return {**data, **overrides}


async def seed_doctor(db_session, **overrides):
    doctor = Doctor(**make_doctor_data(**overrides))
    db_session.add(doctor)
    await db_session.flush()
    return doctor


async def seed_patient(db_session, **overrides):
    patient = Patient(**make_patient_data(**overrides))
    db_session.add(patient)
    await db_session.flush()
    return patient


@pytest.mark.integration
async def test_save_and_get_by_id(db_session):
    repo = AppointmentRepository(db_session)
    doctor = await seed_doctor(db_session)
    patient = await seed_patient(db_session)

    appointment = await repo.save(Appointment(
        doctor_id=doctor.id, patient_id=patient.id, date=datetime(2026, 7, 6, 10, 0, 0)
    ))

    found = await repo.get_by_id(appointment.id)
    assert found.doctor_id == doctor.id
    assert found.patient_id == patient.id


@pytest.mark.integration
async def test_get_by_id_active_only_excludes_cancelled(db_session):
    repo = AppointmentRepository(db_session)
    doctor = await seed_doctor(db_session)
    patient = await seed_patient(db_session)

    appointment = await repo.save(Appointment(
        doctor_id=doctor.id, patient_id=patient.id, date=datetime(2026, 7, 6, 10, 0, 0)
    ))
    await repo.cancel(appointment, CancellationReason.PATIENT_CANCELED)

    assert await repo.get_by_id(appointment.id, active_only=True) is None
    assert await repo.get_by_id(appointment.id, active_only=False) is not None


@pytest.mark.integration
async def test_doctor_has_conflict_true_when_same_doctor_and_time(db_session):
    repo = AppointmentRepository(db_session)
    doctor = await seed_doctor(db_session)
    patient = await seed_patient(db_session)
    when = datetime(2026, 7, 6, 10, 0, 0)

    await repo.save(Appointment(doctor_id=doctor.id, patient_id=patient.id, date=when))

    assert await repo.doctor_has_conflict(doctor.id, when) is True
    assert await repo.doctor_has_conflict(doctor.id, datetime(2026, 7, 6, 11, 0, 0)) is False


@pytest.mark.integration
async def test_doctor_has_conflict_excludes_own_id(db_session):
    repo = AppointmentRepository(db_session)
    doctor = await seed_doctor(db_session)
    patient = await seed_patient(db_session)
    when = datetime(2026, 7, 6, 10, 0, 0)

    appointment = await repo.save(Appointment(doctor_id=doctor.id, patient_id=patient.id, date=when))

    assert await repo.doctor_has_conflict(doctor.id, when, exclude_id=appointment.id) is False


@pytest.mark.integration
async def test_doctor_has_conflict_ignores_cancelled_appointments(db_session):
    repo = AppointmentRepository(db_session)
    doctor = await seed_doctor(db_session)
    patient = await seed_patient(db_session)
    when = datetime(2026, 7, 6, 10, 0, 0)

    appointment = await repo.save(Appointment(doctor_id=doctor.id, patient_id=patient.id, date=when))
    await repo.cancel(appointment, CancellationReason.OTHER)

    assert await repo.doctor_has_conflict(doctor.id, when) is False


@pytest.mark.integration
async def test_patient_has_conflict_window_is_inclusive_at_boundaries(db_session):
    repo = AppointmentRepository(db_session)
    doctor = await seed_doctor(db_session)
    patient = await seed_patient(db_session)

    await repo.save(Appointment(doctor_id=doctor.id, patient_id=patient.id, date=datetime(2026, 7, 6, 7, 0, 0)))

    assert await repo.patient_has_conflict(
        patient.id, datetime(2026, 7, 6, 7, 0, 0), datetime(2026, 7, 6, 18, 0, 0)
    ) is True


@pytest.mark.integration
async def test_patient_has_conflict_false_outside_window(db_session):
    repo = AppointmentRepository(db_session)
    doctor = await seed_doctor(db_session)
    patient = await seed_patient(db_session)

    await repo.save(Appointment(doctor_id=doctor.id, patient_id=patient.id, date=datetime(2026, 7, 7, 10, 0, 0)))

    assert await repo.patient_has_conflict(
        patient.id, datetime(2026, 7, 6, 7, 0, 0), datetime(2026, 7, 6, 18, 0, 0)
    ) is False


@pytest.mark.integration
async def test_patient_has_conflict_excludes_own_id(db_session):
    repo = AppointmentRepository(db_session)
    doctor = await seed_doctor(db_session)
    patient = await seed_patient(db_session)
    when = datetime(2026, 7, 6, 10, 0, 0)

    appointment = await repo.save(Appointment(doctor_id=doctor.id, patient_id=patient.id, date=when))

    assert await repo.patient_has_conflict(
        patient.id, datetime(2026, 7, 6, 7, 0, 0), datetime(2026, 7, 6, 18, 0, 0), exclude_id=appointment.id
    ) is False


@pytest.mark.integration
async def test_get_available_doctors_excludes_inactive_doctor(db_session):
    repo = AppointmentRepository(db_session)
    doctor = await seed_doctor(db_session, email="inactive@clinic.com", crm="CRM00002")
    doctor.is_active = False
    await db_session.flush()

    candidates = await repo.get_available_doctors(Speciality.CARDIOLOGY, datetime(2026, 7, 6, 10, 0, 0))
    assert doctor.id not in [d.id for d in candidates]


@pytest.mark.integration
async def test_get_available_doctors_excludes_wrong_speciality(db_session):
    repo = AppointmentRepository(db_session)
    doctor = await seed_doctor(db_session, email="derm@clinic.com", crm="CRM00003", speciality=Speciality.DERMATOLOGY)

    candidates = await repo.get_available_doctors(Speciality.CARDIOLOGY, datetime(2026, 7, 6, 10, 0, 0))
    assert doctor.id not in [d.id for d in candidates]


@pytest.mark.integration
async def test_get_available_doctors_excludes_doctor_with_conflicting_appointment(db_session):
    repo = AppointmentRepository(db_session)
    doctor = await seed_doctor(db_session, email="busy@clinic.com", crm="CRM00004")
    patient = await seed_patient(db_session)
    when = datetime(2026, 7, 6, 10, 0, 0)

    await repo.save(Appointment(doctor_id=doctor.id, patient_id=patient.id, date=when))

    candidates = await repo.get_available_doctors(Speciality.CARDIOLOGY, when)
    assert doctor.id not in [d.id for d in candidates]


@pytest.mark.integration
async def test_get_available_doctors_returns_free_matching_doctor(db_session):
    repo = AppointmentRepository(db_session)
    doctor = await seed_doctor(db_session, email="free@clinic.com", crm="CRM00005")

    candidates = await repo.get_available_doctors(Speciality.CARDIOLOGY, datetime(2026, 7, 6, 10, 0, 0))
    assert doctor.id in [d.id for d in candidates]


@pytest.mark.integration
async def test_count_and_get_all_filter_by_doctor_and_patient(db_session):
    repo = AppointmentRepository(db_session)
    doctor = await seed_doctor(db_session)
    patient = await seed_patient(db_session)
    other_patient = await seed_patient(db_session, email="other@doe.com", cpf="99988877766")

    await repo.save(Appointment(doctor_id=doctor.id, patient_id=patient.id, date=datetime(2026, 7, 6, 10, 0, 0)))
    await repo.save(Appointment(doctor_id=doctor.id, patient_id=other_patient.id, date=datetime(2026, 7, 6, 11, 0, 0)))

    assert await repo.count(patient_id=patient.id) == 1
    results = await repo.get_all(offset=0, limit=10, patient_id=patient.id)
    assert all(a.patient_id == patient.id for a in results)


@pytest.mark.integration
async def test_count_and_get_all_with_doctor_id_zero_return_empty(db_session):
    repo = AppointmentRepository(db_session)
    doctor = await seed_doctor(db_session)
    patient = await seed_patient(db_session)

    await repo.save(Appointment(doctor_id=doctor.id, patient_id=patient.id, date=datetime(2026, 7, 6, 10, 0, 0)))

    assert await repo.count(doctor_id=0) == 0
    assert await repo.get_all(offset=0, limit=10, doctor_id=0) == []


@pytest.mark.integration
async def test_save_second_appointment_for_same_doctor_and_slot_raises_integrity_error(db_session):
    repo = AppointmentRepository(db_session)
    doctor = await seed_doctor(db_session)
    patient_a = await seed_patient(db_session)
    patient_b = await seed_patient(db_session, email="other@doe.com", cpf="99988877766")
    when = datetime(2026, 7, 6, 10, 0, 0)

    await repo.save(Appointment(doctor_id=doctor.id, patient_id=patient_a.id, date=when))

    with pytest.raises(IntegrityError):
        await repo.save(Appointment(doctor_id=doctor.id, patient_id=patient_b.id, date=when))
