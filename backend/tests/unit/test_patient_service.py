from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.patient_service import PatientService
from app.core.exceptions import ConflictException, NotFoundException
from app.schemas.patient_schema import PatientCreate, PatientPatch

def make_service():
    repo = MagicMock()
    repo.get_by_email = AsyncMock(return_value=None)
    repo.get_by_cpf = AsyncMock(return_value=None)
    repo.get_by_id = AsyncMock(return_value=None)
    repo.save = AsyncMock()
    repo.patch = AsyncMock()
    repo.deactivate = AsyncMock()
    repo.get_all = AsyncMock(return_value=[])
    repo.count = AsyncMock(return_value=0)
    return PatientService(repo)


def make_patient(**kwargs):
    patient = MagicMock()
    patient.id = 1
    patient.is_active = kwargs.get("is_active", True)
    patient.email = kwargs.get("email", "email@email.com")
    return patient



# --- assert_unique_email ---

async def test_unique_email_passes_when_not_found():
    service = make_service()
    await service.assert_unique_email("patient@email.com")


async def test_unique_email_raises_when_found():
    service = make_service()
    service.repo.get_by_email = AsyncMock(return_value=make_patient())
    with pytest.raises(ConflictException):
        await service.assert_unique_email("exists@email.com")


# --- assert_unique_cpf ---

async def test_unique_cpf_passes_when_not_found():
    service = make_service()
    await service.assert_unique_cpf("99999999999")


async def test_unique_cpf_raises_when_found():
    service = make_service()
    service.repo.get_by_cpf = AsyncMock(return_value=make_patient())
    with pytest.raises(ConflictException):
        await service.assert_unique_cpf("12345678900")


# --- get_by_id ---

async def test_get_by_id_returns_patient():
    service = make_service()
    patient = make_patient()
    service.repo.get_by_id = AsyncMock(return_value=patient)
    result = await service.get_by_id(1)
    assert result is patient


async def test_get_by_id_raises_when_not_found():
    service = make_service()
    with pytest.raises(NotFoundException):
        await service.get_by_id(999)


 # --- create ---

async def test_create_calls_unique_checks_and_saves():
    service = make_service()
    data = PatientCreate(name="João", email="j@j.com", cpf="12345678900", phone="11999999999")
    saved_patient = make_patient()
    service.repo.save = AsyncMock(return_value=saved_patient)
    result = await service.create(data)
    service.repo.get_by_email.assert_called_once()
    service.repo.get_by_cpf.assert_called_once()
    service.repo.save.assert_called_once()
    assert result is saved_patient


 # --- patch ---

async def test_patch_calls_unique_email_when_email_changes():
    service = make_service()
    patient = make_patient(email="old@email.com")
    service.repo.get_by_id = AsyncMock(return_value=patient)
    await service.patch(1, PatientPatch(email="new@email.com"))
    service.repo.get_by_email.assert_called_once()


async def test_patch_skips_unique_email_when_email_unchanged():
    service = make_service()
    patient = make_patient(email="same@email.com")
    service.repo.get_by_id = AsyncMock(return_value=patient)
    await service.patch(1, PatientPatch(name="new name"))
    service.repo.get_by_email.assert_not_called()


async def test_patch_skips_unique_email_when_email_same():
    service = make_service()
    patient = make_patient(email="same@email.com")
    service.repo.get_by_id = AsyncMock(return_value=patient)
    await service.patch(1, PatientPatch(email="same@email.com"))
    service.repo.get_by_email.assert_not_called()


async def test_patch_fetches_patient_including_inactive():
    service = make_service()
    patient = make_patient()
    service.repo.get_by_id = AsyncMock(return_value=patient)
    await service.patch(1, PatientPatch(name="Novo Nome"))
    service.repo.get_by_id.assert_called_once_with(1, True)


# --- list_patients: cálculo de paginação ---

async def test_list_patients_empty():
    service = make_service()
    result = await service.list_patients(page=1, size=10)
    assert result.total == 0
    assert result.pages == 0
    assert result.has_next is False
    assert result.has_prev is False


async def test_list_patients_has_next():
    service = make_service()
    service.repo.count = AsyncMock(return_value=25)
    result = await service.list_patients(page=1, size=10)
    assert result.pages == 3
    assert result.has_next is True
    assert result.has_prev is False


async def test_list_patients_has_prev():
    service = make_service()
    service.repo.count = AsyncMock(return_value=25)
    result = await service.list_patients(page=3, size=10)
    assert result.has_next is False
    assert result.has_prev is True


# --- deactivate ---

async def test_deactivate_active_patient():
    service = make_service()
    patient = make_patient(is_active=True)
    service.repo.get_by_id = AsyncMock(return_value=patient)
    await service.deactivate(1)
    service.repo.deactivate.assert_called_once_with(patient)


async def test_deactivate_already_inactive_raises():
    service = make_service()
    patient = make_patient(is_active=False)
    service.repo.get_by_id = AsyncMock(return_value=patient)
    with pytest.raises(ConflictException):
        await service.deactivate(1)


async def test_deactivate_fetches_patient_ignoring_active_only():
    service = make_service()
    patient = make_patient(is_active=True)
    service.repo.get_by_id = AsyncMock(return_value=patient)
    await service.deactivate(1)
    service.repo.get_by_id.assert_called_once_with(1, False)
