from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.staff_service import StaffService
from app.core.exceptions import ConflictException, NotFoundException
from app.schemas.staff_schema import StaffCreate, StaffPatch
from app.models.enums import Sector

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
    return StaffService(repo)


def make_staff(**kwargs):
    staff = MagicMock()
    staff.id = 1
    staff.is_active = kwargs.get("is_active", True)
    staff.email = kwargs.get("email", "email@email.com")
    return staff



# --- assert_unique_email ---

async def test_unique_email_passes_when_not_found():
    service = make_service()
    await service.assert_unique_email("staff@email.com")


async def test_unique_email_raises_when_found():
    service = make_service()
    service.repo.get_by_email = AsyncMock(return_value=make_staff())
    with pytest.raises(ConflictException):
        await service.assert_unique_email("exists@email.com")


# --- assert_unique_cpf ---

async def test_unique_cpf_passes_when_not_found():
    service = make_service()
    await service.assert_unique_cpf("99999999999")


async def test_unique_cpf_raises_when_found():
    service = make_service()
    service.repo.get_by_cpf = AsyncMock(return_value=make_staff())
    with pytest.raises(ConflictException):
        await service.assert_unique_cpf("12345678900")


# --- get_by_id ---

async def test_get_by_id_returns_staff():
    service = make_service()
    staff = make_staff()
    service.repo.get_by_id = AsyncMock(return_value=staff)
    result = await service.get_by_id(1)
    assert result is staff


async def test_get_by_id_raises_when_not_found():
    service = make_service()
    with pytest.raises(NotFoundException):
        await service.get_by_id(999)


# --- create ---

async def test_create_calls_unique_checks_and_saves():
    service = make_service()
    data = StaffCreate(name="Ana", email="ana@ana.com", cpf="12345678900", phone="11999999999", sector=Sector.RECEPTION)
    saved_staff = make_staff()
    service.repo.save = AsyncMock(return_value=saved_staff)
    result = await service.create(data)
    service.repo.get_by_email.assert_called_once()
    service.repo.get_by_cpf.assert_called_once()
    service.repo.save.assert_called_once()
    assert result is saved_staff


# --- patch ---

async def test_patch_calls_unique_email_when_email_changes():
    service = make_service()
    staff = make_staff(email="old@email.com")
    service.repo.get_by_id = AsyncMock(return_value=staff)
    await service.patch(1, StaffPatch(email="new@email.com"))
    service.repo.get_by_email.assert_called_once()


async def test_patch_skips_unique_email_when_email_unchanged():
    service = make_service()
    staff = make_staff(email="same@email.com")
    service.repo.get_by_id = AsyncMock(return_value=staff)
    await service.patch(1, StaffPatch(name="new name"))
    service.repo.get_by_email.assert_not_called()


async def test_patch_skips_unique_email_when_email_same():
    service = make_service()
    staff = make_staff(email="same@email.com")
    service.repo.get_by_id = AsyncMock(return_value=staff)
    await service.patch(1, StaffPatch(email="same@email.com"))
    service.repo.get_by_email.assert_not_called()


# --- list_staff: cálculo de paginação ---

async def test_list_staff_empty():
    service = make_service()
    result = await service.list_staff(page=1, size=10)
    assert result.total == 0
    assert result.pages == 0
    assert result.has_next is False
    assert result.has_prev is False


async def test_list_staff_has_next():
    service = make_service()
    service.repo.count = AsyncMock(return_value=25)
    result = await service.list_staff(page=1, size=10)
    assert result.pages == 3
    assert result.has_next is True
    assert result.has_prev is False


async def test_list_staff_has_prev():
    service = make_service()
    service.repo.count = AsyncMock(return_value=25)
    result = await service.list_staff(page=3, size=10)
    assert result.has_next is False
    assert result.has_prev is True


# --- deactivate ---

async def test_deactivate_active_staff():
    service = make_service()
    staff = make_staff(is_active=True)
    service.repo.get_by_id = AsyncMock(return_value=staff)
    await service.deactivate(1)
    service.repo.deactivate.assert_called_once_with(staff)


async def test_deactivate_already_inactive_raises():
    service = make_service()
    staff = make_staff(is_active=False)
    service.repo.get_by_id = AsyncMock(return_value=staff)
    with pytest.raises(ConflictException):
        await service.deactivate(1)


async def test_deactivate_fetches_staff_ignoring_active_only():
    service = make_service()
    staff = make_staff(is_active=True)
    service.repo.get_by_id = AsyncMock(return_value=staff)
    await service.deactivate(1)
    service.repo.get_by_id.assert_called_once_with(1, False)
