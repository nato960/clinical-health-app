from datetime import date, timedelta

from httpx import AsyncClient
import pytest

def patient_payload(**overrides):
    data = {
        "name": "Pedro Alves",
        "email": "pedro@email.com",
        "cpf": "987.654.321-00",
        "phone": "11977776666",
        "birth_date": "1990-05-15",
    }
    return {**data, **overrides}

PATIENT_URL = "/api/patients/"


# --- POST /api/patients/ ---

@pytest.mark.integration
async def test_create_patient_return_201(client: AsyncClient):
    payload = patient_payload()
    response = await client.post(PATIENT_URL, json=payload)
    assert response.status_code == 201
    assert response.json()["email"] == payload["email"]


@pytest.mark.integration
async def test_create_patient_with_address(client: AsyncClient):
    payload = patient_payload(address={
        "street": "Rua das Flores, 100",
        "city": "São Paulo",
        "state": "SP",
        "zip_code": "01310-100",
    })
    response = await client.post(PATIENT_URL, json=payload)
    assert response.status_code == 201
    assert response.json()["address"] == payload["address"]


@pytest.mark.integration
async def test_create_duplicate_email_returns_409(client: AsyncClient):
    await client.post(PATIENT_URL, json=patient_payload())
    response = await client.post(PATIENT_URL, json=patient_payload(cpf="111.222.333-44"))
    assert response.status_code == 409


@pytest.mark.integration
async def test_create_duplicate_cpf_returns_409(client: AsyncClient):
    await client.post(PATIENT_URL, json=patient_payload())
    response = await client.post(PATIENT_URL, json=patient_payload(email="another@email.com"))
    assert response.status_code == 409


@pytest.mark.integration
async def test_create_missing_required_field_returns_422(client: AsyncClient):
    response = await client.post(PATIENT_URL, json={"name": "No other field"})
    assert response.status_code == 422


@pytest.mark.integration
async def test_create_future_birth_date_returns_422(client: AsyncClient):
    future_date = (date.today() + timedelta(days=1)).isoformat()
    response = await client.post(PATIENT_URL, json=patient_payload(birth_date=future_date))
    assert response.status_code == 422


@pytest.mark.integration
async def test_create_invalid_cpf_returns_422(client: AsyncClient):
    response = await client.post(PATIENT_URL, json=patient_payload(cpf="not-a-cpf"))
    assert response.status_code == 422



# --- GET /api/patients/ ---

@pytest.mark.integration
async def test_list_patients_returns_200(client: AsyncClient):
    response = await client.get(PATIENT_URL)
    assert response.status_code == 200
    assert "items" in response.json()


@pytest.mark.integration
async def test_list_patients_size_above_max_returns_422(client: AsyncClient):
    response = await client.get(f"{PATIENT_URL}?size=200")
    assert response.status_code == 422



# --- GET /api/patients/{id} ---

@pytest.mark.integration
async def test_get_patient_by_id_returns_200(client: AsyncClient):
    created = await client.post(PATIENT_URL, json=patient_payload())
    patient_id = created.json()["id"]
    response = await client.get(f"{PATIENT_URL}{patient_id}")
    assert response.status_code == 200
    assert response.json()["id"] == patient_id


@pytest.mark.integration
async def test_get_nonexistent_patient_returns_404(client: AsyncClient):
    response = await client.get(f"{PATIENT_URL}99999")
    assert response.status_code == 404



# --- PATCH /api/patients/{id} ---

@pytest.mark.integration
async def test_patch_patient_returns_200(client: AsyncClient):
    created = await client.post(PATIENT_URL, json=patient_payload())
    patient_id = created.json()["id"]
    response = await client.patch(f"{PATIENT_URL}{patient_id}", json={"name": "new name"})
    assert response.status_code == 200
    assert response.json()["name"] == "new name"


@pytest.mark.integration
async def test_patch_nonexistent_patient_returns_404(client: AsyncClient):
    response = await client.patch(f"{PATIENT_URL}999999", json={"name": "XX"})
    assert response.status_code == 404



# --- DELETE /api/patients/{id} ---

@pytest.mark.integration
async def test_deactivate_patient_returns_204(client: AsyncClient):
    created = await client.post(PATIENT_URL, json=patient_payload())
    patient_id = created.json()["id"]
    response = await client.delete(f"{PATIENT_URL}{patient_id}")
    patient_get = await client.get(f"{PATIENT_URL}{patient_id}")
    assert response.status_code == 204
    assert patient_get.status_code == 404


@pytest.mark.integration
async def test_deactivate_nonexistent_returns_404(client: AsyncClient):
    response = await client.delete(f"{PATIENT_URL}9999999")
    assert response.status_code == 404


@pytest.mark.integration
async def test_deactivate_already_inactive_returns_409(client: AsyncClient):
    created = await client.post(PATIENT_URL, json=patient_payload())
    patient_id = created.json()["id"]
    await client.delete(f"{PATIENT_URL}{patient_id}")
    response = await client.delete(f"{PATIENT_URL}{patient_id}")
    assert response.status_code == 409
