from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.doctor_service import DoctorService
from app.core.exceptions import ConflictException, NotFoundException

def make_service(mocker):
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

async def test_unique_email_passes_when_not_found(mocker):
    service = make_service(mocker)
    await service.assert_unique_email("doctor@email.com")


async def test_unique_email_raises_when_found(mocker):
    service = make_service(mocker)
    service.repo.get_by_email = AsyncMock(return_value=make_doctor())
    with pytest.raises(ConflictException):
        await service.assert_unique_email("exists@email.com")


# --- assert_unique_crm ---

async def test_unique_crm_passes_when_not_found(mocker):
    service = make_service(mocker)
    await service.assert_unique_crm("99999")


async def test_unique_crm_raises_when_found(mocker):
    service = make_service(mocker)
    service.repo.get_by_crm = AsyncMock(return_value=make_doctor())
    with pytest.raises(ConflictException):
        await service.assert_unique_crm("12345")


# --- get_by_id ---

async def test_get_by_id_returns_doctor(mocker):
    service = make_service(mocker)
    doctor = make_doctor()
    service.repo.get_by_id = AsyncMock(return_value=doctor)
    result = await service.get_by_id(1)
    assert result is doctor


async def test_get_by_id_raises_when_not_found(mocker):
    service = make_service(mocker)
    with pytest.raises(NotFoundException):
        await service.get_by_id(999)


# --- list_doctors: cálculo de paginação ---

async def test_list_doctors_empty(mocker):
    service = make_service(mocker)
    result = await service.list_doctors(page=1, size=10)
    assert result.total == 0
    assert result.pages == 0
    assert result.has_next is False
    assert result.has_prev is False

