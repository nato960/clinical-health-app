from datetime import date, timedelta

from httpx import AsyncClient
import pytest

from app.core.security import get_current_user
from app.main import app
from app.models.enums import UserRole
from app.models.user import User
from tests.conftest import make_current_user_override

def staff_payload(**overrides):
    data = {
        "name": "Pedro Alves",
        "email": "pedro@email.com",
        "cpf": "12345678900",
        "phone": "11977776666",
        "sector": "RECEPTION",
        "birth_date": "1990-05-15",
    }
    return {**data, **overrides}

STAFF_URL = "/api/staff/"


# --- POST /api/staff/ ---

@pytest.mark.integration
async def test_create_staff_return_201(client: AsyncClient):
    payload = staff_payload()
    response = await client.post(STAFF_URL, json=payload)
    assert response.status_code == 201
    assert response.json()["email"] == payload["email"]


@pytest.mark.integration
async def test_create_staff_with_address(client: AsyncClient):
    payload = staff_payload(address={
        "street": "Rua das Flores, 100",
        "city": "São Paulo",
        "state": "SP",
        "zip_code": "01310-100",
    })
    response = await client.post(STAFF_URL, json=payload)
    assert response.status_code == 201
    assert response.json()["address"] == payload["address"]


@pytest.mark.integration
async def test_create_duplicate_email_returns_409(client: AsyncClient):
    await client.post(STAFF_URL, json=staff_payload())
    response = await client.post(STAFF_URL, json=staff_payload(cpf="99999999999"))
    assert response.status_code == 409


@pytest.mark.integration
async def test_create_duplicate_cpf_returns_409(client: AsyncClient):
    await client.post(STAFF_URL, json=staff_payload())
    response = await client.post(STAFF_URL, json=staff_payload(email="another@email.com"))
    assert response.status_code == 409


@pytest.mark.integration
async def test_create_missing_required_field_returns_422(client: AsyncClient):
    response = await client.post(STAFF_URL, json={"name": "No other field"})
    assert response.status_code == 422


@pytest.mark.integration
async def test_create_future_birth_date_returns_422(client: AsyncClient):
    future_date = (date.today() + timedelta(days=1)).isoformat()
    response = await client.post(STAFF_URL, json=staff_payload(birth_date=future_date))
    assert response.status_code == 422


# --- GET /api/staff/ ---

@pytest.mark.integration
async def test_list_staff_returns_200(client: AsyncClient):
    response = await client.get(STAFF_URL)
    assert response.status_code == 200
    assert "items" in response.json()


@pytest.mark.integration
async def test_list_staff_size_above_max_returns_422(client: AsyncClient):
    response = await client.get(f"{STAFF_URL}?size=200")
    assert response.status_code == 422


# --- GET /api/staff/{id} ---

@pytest.mark.integration
async def test_get_staff_by_id_returns_200(client: AsyncClient):
    created = await client.post(STAFF_URL, json=staff_payload())
    staff_id = created.json()["id"]
    response = await client.get(f"{STAFF_URL}{staff_id}")
    assert response.status_code == 200
    assert response.json()["id"] == staff_id


@pytest.mark.integration
async def test_get_nonexistent_staff_returns_404(client: AsyncClient):
    response = await client.get(f"{STAFF_URL}99999")
    assert response.status_code == 404


# --- PATCH /api/staff/{id} ---

@pytest.mark.integration
async def test_patch_staff_returns_200(client: AsyncClient):
    created = await client.post(STAFF_URL, json=staff_payload())
    staff_id = created.json()["id"]
    response = await client.patch(f"{STAFF_URL}{staff_id}", json={"name": "new name"})
    assert response.status_code == 200
    assert response.json()["name"] == "new name"


@pytest.mark.integration
async def test_patch_nonexistent_staff_returns_404(client: AsyncClient):
    response = await client.patch(f"{STAFF_URL}999999", json={"name": "XX"})
    assert response.status_code == 404


# --- DELETE /api/staff/{id} ---

@pytest.mark.integration
async def test_deactivate_staff_returns_204(client: AsyncClient):
    created = await client.post(STAFF_URL, json=staff_payload())
    staff_id = created.json()["id"]
    response = await client.delete(f"{STAFF_URL}{staff_id}")
    staff_get = await client.get(f"{STAFF_URL}{staff_id}")
    assert response.status_code == 204
    assert staff_get.status_code == 404


@pytest.mark.integration
async def test_deactivate_nonexistent_returns_404(client: AsyncClient):
    response = await client.delete(f"{STAFF_URL}9999999")
    assert response.status_code == 404


@pytest.mark.integration
async def test_deactivate_already_inactive_returns_409(client: AsyncClient):
    created = await client.post(STAFF_URL, json=staff_payload())
    staff_id = created.json()["id"]
    await client.delete(f"{STAFF_URL}{staff_id}")
    response = await client.delete(f"{STAFF_URL}{staff_id}")
    assert response.status_code == 409


# --- controle de acesso (ADMIN/USER_ADMIN only) ---

@pytest.mark.integration
async def test_non_admin_role_is_forbidden(client: AsyncClient):
    app.dependency_overrides[get_current_user] = make_current_user_override(
        User(id=2, firebase_uid="doctor-uid", email="doctor@test.com", role=UserRole.USER_DOCTOR)
    )
    response = await client.get(STAFF_URL)
    assert response.status_code == 403


@pytest.mark.integration
async def test_user_admin_role_is_allowed(client: AsyncClient):
    app.dependency_overrides[get_current_user] = make_current_user_override(
        User(id=3, firebase_uid="useradmin-uid", email="useradmin@test.com", role=UserRole.USER_ADMIN)
    )
    response = await client.get(STAFF_URL)
    assert response.status_code == 200
