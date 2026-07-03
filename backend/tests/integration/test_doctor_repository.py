import pytest

from datetime import date

from app.repositories.doctor_repository import DoctorRepository
from app.models.enums import Speciality
from app.models.doctor import Doctor


def make_doctor_data(**overrides):
    data = {
        "name": "Ana Lima",
        "email": "ana@email.com",
        "crm": "CRM-001",
        "phone": "11988887777",
        "speciality": Speciality.CARDIOLOGY,
        "birth_date": date(1985, 3, 10),
    }
    return {**data, **overrides}


@pytest.mark.integration
async def test_save_and_get_by_id(db_session):
    repo = DoctorRepository(db_session)
    doctor = await repo.save(Doctor(**make_doctor_data()))
    found = await repo.get_by_id(doctor.id)
    assert found.name == "Ana Lima"


@pytest.mark.integration
async def test_get_by_email_returns_doctor(db_session):
    repo = DoctorRepository(db_session)
    doctor = await repo.save(Doctor(**make_doctor_data()))
    found = await repo.get_by_email(doctor.email)
    assert doctor.id == found.id


@pytest.mark.integration
async def test_get_by_email_returns_none_when_not_found(db_session):
    repo = DoctorRepository(db_session)
    found = await repo.get_by_email("nope@email.com")
    assert found is None


@pytest.mark.integration
async def test_get_by_crm_returns_doctor(db_session):
    repo = DoctorRepository(db_session)
    doctor = await repo.save(Doctor(**make_doctor_data()))
    found = await repo.get_by_crm(doctor.crm)
    assert found.id == doctor.id


@pytest.mark.integration
async def test_search_by_name_case_insensitive(db_session):
    repo = DoctorRepository(db_session)
    await repo.save(Doctor(**make_doctor_data(name="Carlos Menezes")))
    results = await repo.get_all(search="carlos", speciality=None, offset=0, limit=10)
    assert any(d.name == "Carlos Menezes" for d in results)


@pytest.mark.integration
async def test_filter_by_speciality(db_session):
    repo = DoctorRepository(db_session)
    doctor = await repo.save(Doctor(**make_doctor_data(speciality=Speciality.DERMATOLOGY, crm="CRM-002", email="b@b.com")))
    results = await repo.get_all(search=None, speciality=Speciality.DERMATOLOGY, offset=0, limit=10)
    assert any(d.id == doctor.id for d in results)
    assert all(d.speciality == Speciality.DERMATOLOGY for d in results)


@pytest.mark.integration
async def test_deactivate_sets_is_active_false(db_session):
    repo = DoctorRepository(db_session)
    doctor = await repo.save(Doctor(**make_doctor_data()))
    await repo.deactivate(doctor)
    found = await repo.get_by_id(doctor.id, active_only=False)
    assert found.is_active is False
