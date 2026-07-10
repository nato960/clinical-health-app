from datetime import date, timedelta

from httpx import AsyncClient
import pytest

from app.core.security import get_current_user
from app.main import app
from app.models.enums import UserRole
from app.models.user import User
from tests.conftest import make_current_user_override

def doctor_payload(**overrides):
    data = {
        "name": "Pedro Alves",
        "email": "pedro@email.com",
        "crm": "CRM-100",
        "phone": "11977776666",
        "speciality": "CARDIOLOGY",
        "birth_date": "1990-05-15",
    }
    return {**data, **overrides}

DOCTOR_URL = "/api/doctors/"


# --- POST /api/doctors/ ---

@pytest.mark.integration
async def test_create_doctor_return_201(client: AsyncClient):
    payload = doctor_payload()
    response = await client.post(DOCTOR_URL, json=payload)
    assert response.status_code == 201
    assert response.json()["email"] == payload["email"]


@pytest.mark.integration
async def test_create_doctor_with_address(client: AsyncClient):
    payload = doctor_payload(address={
        "street": "Rua das Flores, 100",
        "city": "São Paulo",
        "state": "SP",
        "zip_code": "01310-100",
    })
    response = await client.post(DOCTOR_URL, json=payload)
    assert response.status_code == 201
    assert response.json()["address"] == payload["address"]


@pytest.mark.integration
async def test_create_duplicate_email_returns_409(client: AsyncClient):
    await client.post(DOCTOR_URL, json=doctor_payload())
    response = await client.post(DOCTOR_URL, json=doctor_payload(crm="CRM-999"))
    assert response.status_code == 409


@pytest.mark.integration
async def test_create_duplicate_crm_returns_409(client: AsyncClient):
    await client.post(DOCTOR_URL, json=doctor_payload())
    response = await client.post(DOCTOR_URL, json=doctor_payload(email="another@email.com"))
    assert response.status_code == 409


@pytest.mark.integration
async def test_create_missing_required_field_returns_422(client: AsyncClient):
    response = await client.post(DOCTOR_URL, json={"name": "No other field"})
    assert response.status_code == 422


@pytest.mark.integration
async def test_create_future_birth_date_returns_422(client: AsyncClient):
    future_date = (date.today() + timedelta(days=1)).isoformat()
    response = await client.post(DOCTOR_URL, json=doctor_payload(birth_date=future_date))
    assert response.status_code == 422



# --- GET /api/doctors/ ---

@pytest.mark.integration
async def test_list_doctors_returns_200(client: AsyncClient):
    response = await client.get(DOCTOR_URL)
    assert response.status_code == 200
    assert "items" in response.json()


@pytest.mark.integration
async def test_list_doctors_size_above_max_returns_422(client: AsyncClient):
    response = await client.get(f"{DOCTOR_URL}?size=200")
    assert response.status_code == 422



# --- GET /api/doctors/{id} ---

@pytest.mark.integration
async def test_get_doctor_by_id_returns_200(client: AsyncClient):
    created = await client.post(DOCTOR_URL, json=doctor_payload())
    doctor_id = created.json()["id"]
    response = await client.get(f"{DOCTOR_URL}{doctor_id}")
    assert response.status_code == 200
    assert response.json()["id"] == doctor_id


@pytest.mark.integration
async def test_get_nonexistent_doctor_returns_404(client: AsyncClient):
    response = await client.get(f"{DOCTOR_URL}99999")
    assert response.status_code == 404



# --- PATCH /api/doctors/{id} ---

@pytest.mark.integration
async def test_patch_doctor_returns_200(client: AsyncClient):
    created = await client.post(DOCTOR_URL, json=doctor_payload())
    doctor_id = created.json()["id"]
    response = await client.patch(f"{DOCTOR_URL}{doctor_id}", json={"name": "new name"})
    assert response.status_code == 200
    assert response.json()["name"] == "new name"


@pytest.mark.integration
async def test_patch_nonexistent_doctor_returns_404(client: AsyncClient):
    response = await client.patch(f"{DOCTOR_URL}999999", json={"name": "XX"})
    assert response.status_code == 404



# --- DELETE /api/doctors/{id} ---

@pytest.mark.integration
async def test_deactivate_doctor_returns_204(client: AsyncClient):
    created = await client.post(DOCTOR_URL, json=doctor_payload())
    doctor_id = created.json()["id"]
    response = await client.delete(f"{DOCTOR_URL}{doctor_id}")
    doctor_get = await client.get(f"{DOCTOR_URL}{doctor_id}")
    assert response.status_code == 204
    assert doctor_get.status_code == 404


@pytest.mark.integration
async def test_deactivate_nonexistent_returns_404(client: AsyncClient):
    response = await client.delete(f"{DOCTOR_URL}9999999")
    assert response.status_code == 404


@pytest.mark.integration
async def test_deactivate_already_inactive_returns_409(client: AsyncClient):
    created = await client.post(DOCTOR_URL, json=doctor_payload())
    doctor_id = created.json()["id"]
    await client.delete(f"{DOCTOR_URL}{doctor_id}")
    response = await client.delete(f"{DOCTOR_URL}{doctor_id}")
    assert response.status_code == 409


# --- controle de acesso (ADMIN/USER_ADMIN only) ---

@pytest.mark.integration
async def test_non_admin_role_is_forbidden(client: AsyncClient):
    app.dependency_overrides[get_current_user] = make_current_user_override(
        User(id=2, firebase_uid="patient-uid", email="patient@test.com", role=UserRole.USER_PATIENT)
    )
    response = await client.get(DOCTOR_URL)
    assert response.status_code == 403


@pytest.mark.integration
async def test_user_admin_role_is_allowed(client: AsyncClient):
    app.dependency_overrides[get_current_user] = make_current_user_override(
        User(id=3, firebase_uid="useradmin-uid", email="useradmin@test.com", role=UserRole.USER_ADMIN)
    )
    response = await client.get(DOCTOR_URL)
    assert response.status_code == 200