import pytest

from datetime import date

from app.repositories.patient_repository import PatientRepository
from app.models.patient import Patient


def make_patient_data(**overrides):
    data = {
        "name": "Ana Lima",
        "email": "ana@email.com",
        "cpf": "123.456.789-00",
        "phone": "11988887777",
        "birth_date": date(1985, 3, 10),
    }
    return {**data, **overrides}


@pytest.mark.integration
async def test_save_and_get_by_id(db_session):
    repo = PatientRepository(db_session)
    patient = await repo.save(Patient(**make_patient_data()))
    found = await repo.get_by_id(patient.id)
    assert found.name == "Ana Lima"


@pytest.mark.integration
async def test_get_by_email_returns_patient(db_session):
    repo = PatientRepository(db_session)
    patient = await repo.save(Patient(**make_patient_data()))
    found = await repo.get_by_email(patient.email)
    assert patient.id == found.id


@pytest.mark.integration
async def test_get_by_email_returns_none_when_not_found(db_session):
    repo = PatientRepository(db_session)
    found = await repo.get_by_email("nope@email.com")
    assert found is None


@pytest.mark.integration
async def test_get_by_cpf_returns_patient(db_session):
    repo = PatientRepository(db_session)
    patient = await repo.save(Patient(**make_patient_data()))
    found = await repo.get_by_cpf(patient.cpf)
    assert found.id == patient.id


@pytest.mark.integration
async def test_search_by_name_case_insensitive(db_session):
    repo = PatientRepository(db_session)
    await repo.save(Patient(**make_patient_data(name="Carlos Menezes")))
    results = await repo.get_all(search="carlos", offset=0, limit=10)
    assert any(p.name == "Carlos Menezes" for p in results)


@pytest.mark.integration
async def test_deactivate_sets_is_active_false(db_session):
    repo = PatientRepository(db_session)
    patient = await repo.save(Patient(**make_patient_data()))
    await repo.deactivate(patient)
    found = await repo.get_by_id(patient.id, active_only=False)
    assert found.is_active is False
