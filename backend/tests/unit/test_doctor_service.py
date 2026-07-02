from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.doctor_service import DoctorService
from app.core.exceptions import ConflictException, NotFoundException
from app.schemas.doctor_schema import DoctorCreate, DoctorPatch
from app.models.enums import Speciality

def make_service():
    repo = MagicMock()
    repo.get_by_email = AsyncMock(return_value=None)
    repo.get_by_crm = AsyncMock(return_value=None)
    repo.get_by_id = AsyncMock(return_value=None)
    repo.save = AsyncMock()
    repo.patch = AsyncMock()
    repo.deactivate = AsyncMock()
    repo.get_all = AsyncMock(return_value=[])
    repo.count = AsyncMock(return_value=0)
    return DoctorService(repo)


def make_doctor(**kwargs):
    doctor = MagicMock()
    doctor.id = 1
    doctor.is_active = kwargs.get("is_active", True)
    doctor.email = kwargs.get("email", "email@email.com")
    return doctor



# --- assert_unique_email ---

async def test_unique_email_passes_when_not_found():
    service = make_service()
    await service.assert_unique_email("doctor@email.com")


async def test_unique_email_raises_when_found():
    service = make_service()
    service.repo.get_by_email = AsyncMock(return_value=make_doctor())
    with pytest.raises(ConflictException):
        await service.assert_unique_email("exists@email.com")


# --- assert_unique_crm ---

async def test_unique_crm_passes_when_not_found():
    service = make_service()
    await service.assert_unique_crm("99999")


async def test_unique_crm_raises_when_found():
    service = make_service()
    service.repo.get_by_crm = AsyncMock(return_value=make_doctor())
    with pytest.raises(ConflictException):
        await service.assert_unique_crm("12345")


# --- get_by_id ---

async def test_get_by_id_returns_doctor():
    service = make_service()
    doctor = make_doctor()
    service.repo.get_by_id = AsyncMock(return_value=doctor)
    result = await service.get_by_id(1)
    assert result is doctor


async def test_get_by_id_raises_when_not_found():
    service = make_service()
    with pytest.raises(NotFoundException):
        await service.get_by_id(999)


 # --- create ---

async def test_create_calls_unique_checks_and_saves():
    service = make_service()
    data = DoctorCreate(name="João", email="j@j.com", crm="1234", phone="11999999999", speciality=Speciality.CARDIOLOGY)
    saved_doctor = make_doctor()
    service.repo.save = AsyncMock(return_value=saved_doctor)
    result = await service.create(data)
    service.repo.get_by_email.assert_called_once()
    service.repo.get_by_crm.assert_called_once()
    service.repo.save.assert_called_once()
    assert result is saved_doctor


 # --- patch ---  

async def test_patch_calls_unique_email_when_email_changes():
    service = make_service()
    doctor = make_doctor(email="old@email.com")
    service.repo.get_by_id = AsyncMock(return_value=doctor)
    await service.patch(1, DoctorPatch(email="new@email.com"))
    service.repo.get_by_email.assert_called_once()


async def test_patch_skips_unique_email_when_email_unchanged():
    service = make_service()
    doctor = make_doctor(email="same@email.com")
    service.repo.get_by_id = AsyncMock(return_value=doctor)
    await service.patch(1, DoctorPatch(name="new name"))
    service.repo.get_by_email.assert_not_called()


async def test_patch_skips_unique_email_when_email_same():
    service = make_service()
    doctor = make_doctor(email="same@email.com")
    service.repo.get_by_id = AsyncMock(return_value=doctor)
    await service.patch(1, DoctorPatch(email="same@email.com"))
    service.repo.get_by_email.assert_not_called()



# --- list_doctors: cálculo de paginação ---

async def test_list_doctors_empty():
    service = make_service()
    result = await service.list_doctors(page=1, size=10)
    assert result.total == 0
    assert result.pages == 0
    assert result.has_next is False
    assert result.has_prev is False


async def test_list_doctors_has_next():
    service = make_service()
    service.repo.count = AsyncMock(return_value=25)
    result = await service.list_doctors(page=1, size=10)
    assert result.pages == 3
    assert result.has_next is True
    assert result.has_prev is False


async def test_list_doctors_has_prev():
    service = make_service()
    service.repo.count = AsyncMock(return_value=25)
    result = await service.list_doctors(page=3, size=10)
    assert result.has_next is False
    assert result.has_prev is True


# --- deactivate ---

async def test_deactivate_active_doctor():
    service = make_service()
    doctor = make_doctor(is_active=True)
    service.repo.get_by_id = AsyncMock(return_value=doctor)
    await service.deactivate(1)
    service.repo.deactivate.assert_called_once_with(doctor)


async def test_deactivate_already_inactive_raises():
    service = make_service()
    doctor = make_doctor(is_active=False)
    service.repo.get_by_id = AsyncMock(return_value=doctor)
    with pytest.raises(ConflictException):
        await service.deactivate(1)