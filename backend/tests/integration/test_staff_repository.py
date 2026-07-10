import pytest

from datetime import date

from app.repositories.staff_repository import StaffRepository
from app.models.enums import Sector
from app.models.staff import Staff


def make_staff_data(**overrides):
    data = {
        "name": "Ana Lima",
        "email": "ana@email.com",
        "cpf": "12345678900",
        "phone": "11988887777",
        "sector": Sector.RECEPTION,
        "birth_date": date(1985, 3, 10),
    }
    return {**data, **overrides}


@pytest.mark.integration
async def test_save_and_get_by_id(db_session):
    repo = StaffRepository(db_session)
    staff = await repo.save(Staff(**make_staff_data()))
    found = await repo.get_by_id(staff.id)
    assert found.name == "Ana Lima"


@pytest.mark.integration
async def test_get_by_email_returns_staff(db_session):
    repo = StaffRepository(db_session)
    staff = await repo.save(Staff(**make_staff_data()))
    found = await repo.get_by_email(staff.email)
    assert staff.id == found.id


@pytest.mark.integration
async def test_get_by_email_returns_none_when_not_found(db_session):
    repo = StaffRepository(db_session)
    found = await repo.get_by_email("nope@email.com")
    assert found is None


@pytest.mark.integration
async def test_get_by_cpf_returns_staff(db_session):
    repo = StaffRepository(db_session)
    staff = await repo.save(Staff(**make_staff_data()))
    found = await repo.get_by_cpf(staff.cpf)
    assert found.id == staff.id


@pytest.mark.integration
async def test_search_by_name_case_insensitive(db_session):
    repo = StaffRepository(db_session)
    await repo.save(Staff(**make_staff_data(name="Carlos Menezes", email="c@c.com", cpf="11111111111")))
    results = await repo.get_all(search="carlos", sector=None, offset=0, limit=10)
    assert any(s.name == "Carlos Menezes" for s in results)


@pytest.mark.integration
async def test_filter_by_sector(db_session):
    repo = StaffRepository(db_session)
    staff = await repo.save(Staff(**make_staff_data(sector=Sector.FINANCE, cpf="22222222222", email="b@b.com")))
    results = await repo.get_all(search=None, sector=Sector.FINANCE, offset=0, limit=10)
    assert any(s.id == staff.id for s in results)
    assert all(s.sector == Sector.FINANCE for s in results)


@pytest.mark.integration
async def test_deactivate_sets_is_active_false(db_session):
    repo = StaffRepository(db_session)
    staff = await repo.save(Staff(**make_staff_data()))
    await repo.deactivate(staff)
    found = await repo.get_by_id(staff.id, active_only=False)
    assert found.is_active is False
