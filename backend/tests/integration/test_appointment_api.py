from datetime import datetime, timedelta

from httpx import AsyncClient
import pytest

APPOINTMENT_URL = "/api/appointments/"
DOCTOR_URL = "/api/doctors/"
PATIENT_URL = "/api/patients/"


def future_valid_datetime(extra_days: int = 2, hour: int = 10) -> datetime:
    """A datetime far enough ahead to satisfy the 30-min lead time, on a Mon-Sat business hour."""
    candidate = (datetime.now() + timedelta(days=extra_days)).replace(hour=hour, minute=0, second=0, microsecond=0)
    while candidate.weekday() == 6:  # Sunday
        candidate += timedelta(days=1)
    return candidate


def doctor_payload(**overrides):
    data = {
        "name": "Dr. Ana Ortiz",
        "email": "ana.ortiz@clinic.com",
        "crm": "CRM00001",
        "phone": "11999990000",
        "speciality": "CARDIOLOGY",
    }
    return {**data, **overrides}


def patient_payload(**overrides):
    data = {
        "name": "John Doe",
        "email": "john@doe.com",
        "cpf": "12345678900",
        "phone": "11988880000",
    }
    return {**data, **overrides}


async def seed_doctor(client: AsyncClient, **overrides) -> int:
    response = await client.post(DOCTOR_URL, json=doctor_payload(**overrides))
    assert response.status_code == 201
    return response.json()["id"]


async def seed_patient(client: AsyncClient, **overrides) -> int:
    response = await client.post(PATIENT_URL, json=patient_payload(**overrides))
    assert response.status_code == 201
    return response.json()["id"]


def iso(dt: datetime) -> str:
    return dt.isoformat()


# --- POST /api/appointments/ (schedule) ---

@pytest.mark.integration
async def test_schedule_with_explicit_doctor_returns_201(client: AsyncClient):
    doctor_id = await seed_doctor(client)
    patient_id = await seed_patient(client)

    response = await client.post(APPOINTMENT_URL, json={
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "date": iso(future_valid_datetime()),
    })

    assert response.status_code == 201
    body = response.json()
    assert body["doctor"]["id"] == doctor_id
    assert body["patient"]["id"] == patient_id


@pytest.mark.integration
async def test_schedule_with_speciality_auto_assigns_doctor(client: AsyncClient):
    doctor_id = await seed_doctor(client, email="cardio2@clinic.com", crm="CRM00002")
    patient_id = await seed_patient(client, email="jane@doe.com", cpf="11122233344")

    response = await client.post(APPOINTMENT_URL, json={
        "patient_id": patient_id,
        "date": iso(future_valid_datetime(extra_days=3)),
        "speciality": "CARDIOLOGY",
    })

    assert response.status_code == 201
    assert response.json()["doctor"]["id"] == doctor_id


@pytest.mark.integration
async def test_schedule_without_doctor_or_speciality_returns_400(client: AsyncClient):
    patient_id = await seed_patient(client, email="nospec@doe.com", cpf="22233344455")

    response = await client.post(APPOINTMENT_URL, json={
        "patient_id": patient_id,
        "date": iso(future_valid_datetime(extra_days=4)),
    })

    assert response.status_code == 400


@pytest.mark.integration
async def test_schedule_with_nonexistent_patient_returns_404(client: AsyncClient):
    doctor_id = await seed_doctor(client, email="doc404@clinic.com", crm="CRM00003")

    response = await client.post(APPOINTMENT_URL, json={
        "patient_id": 999999,
        "doctor_id": doctor_id,
        "date": iso(future_valid_datetime(extra_days=4)),
    })

    assert response.status_code == 404


@pytest.mark.integration
async def test_schedule_with_nonexistent_doctor_returns_404(client: AsyncClient):
    patient_id = await seed_patient(client, email="pat404@doe.com", cpf="33344455566")

    response = await client.post(APPOINTMENT_URL, json={
        "patient_id": patient_id,
        "doctor_id": 999999,
        "date": iso(future_valid_datetime(extra_days=4)),
    })

    assert response.status_code == 404


@pytest.mark.integration
async def test_schedule_on_sunday_returns_400(client: AsyncClient):
    doctor_id = await seed_doctor(client, email="sunday@clinic.com", crm="CRM00004")
    patient_id = await seed_patient(client, email="sunday@doe.com", cpf="44455566677")

    when = future_valid_datetime(extra_days=5)
    while when.weekday() != 6:
        when += timedelta(days=1)

    response = await client.post(APPOINTMENT_URL, json={
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "date": iso(when),
    })

    assert response.status_code == 400


@pytest.mark.integration
async def test_schedule_at_18_hour_still_succeeds(client: AsyncClient):
    doctor_id = await seed_doctor(client, email="closing@clinic.com", crm="CRM00005")
    patient_id = await seed_patient(client, email="closing@doe.com", cpf="55566677788")

    response = await client.post(APPOINTMENT_URL, json={
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "date": iso(future_valid_datetime(extra_days=6, hour=18)),
    })

    assert response.status_code == 201


@pytest.mark.integration
async def test_schedule_less_than_30_minutes_ahead_returns_400(client: AsyncClient):
    doctor_id = await seed_doctor(client, email="soon@clinic.com", crm="CRM00006")
    patient_id = await seed_patient(client, email="soon@doe.com", cpf="66677788899")

    when = datetime.now() + timedelta(minutes=5)
    response = await client.post(APPOINTMENT_URL, json={
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "date": iso(when),
    })

    assert response.status_code == 400


@pytest.mark.integration
async def test_schedule_double_booked_doctor_returns_400(client: AsyncClient):
    doctor_id = await seed_doctor(client, email="double@clinic.com", crm="CRM00007")
    patient_a = await seed_patient(client, email="doublea@doe.com", cpf="77788899900")
    patient_b = await seed_patient(client, email="doubleb@doe.com", cpf="88899900011")
    when = iso(future_valid_datetime(extra_days=7))

    first = await client.post(APPOINTMENT_URL, json={
        "patient_id": patient_a, "doctor_id": doctor_id, "date": when,
    })
    assert first.status_code == 201

    second = await client.post(APPOINTMENT_URL, json={
        "patient_id": patient_b, "doctor_id": doctor_id, "date": when,
    })
    assert second.status_code == 400


# --- PATCH /api/appointments/{id} (reschedule) ---

@pytest.mark.integration
async def test_reschedule_updates_only_provided_fields(client: AsyncClient):
    doctor_id = await seed_doctor(client, email="resched@clinic.com", crm="CRM00008")
    patient_id = await seed_patient(client, email="resched@doe.com", cpf="99900011122")

    created = await client.post(APPOINTMENT_URL, json={
        "patient_id": patient_id, "doctor_id": doctor_id, "date": iso(future_valid_datetime(extra_days=8)),
    })
    appointment_id = created.json()["id"]

    new_date = iso(future_valid_datetime(extra_days=9))
    response = await client.patch(f"{APPOINTMENT_URL}{appointment_id}", json={"date": new_date})

    assert response.status_code == 200
    assert response.json()["date"] == new_date
    assert response.json()["doctor"]["id"] == doctor_id


@pytest.mark.integration
async def test_reschedule_nonexistent_returns_404(client: AsyncClient):
    response = await client.patch(f"{APPOINTMENT_URL}999999", json={"date": iso(future_valid_datetime())})
    assert response.status_code == 404


@pytest.mark.integration
async def test_reschedule_with_unknown_doctor_returns_404(client: AsyncClient):
    doctor_id = await seed_doctor(client, email="resched2@clinic.com", crm="CRM00009")
    patient_id = await seed_patient(client, email="resched2@doe.com", cpf="10011122233")

    created = await client.post(APPOINTMENT_URL, json={
        "patient_id": patient_id, "doctor_id": doctor_id, "date": iso(future_valid_datetime(extra_days=10)),
    })
    appointment_id = created.json()["id"]

    response = await client.patch(f"{APPOINTMENT_URL}{appointment_id}", json={"doctor_id": 999999})
    assert response.status_code == 404


# --- POST /api/appointments/{id}/cancel ---

@pytest.mark.integration
async def test_cancel_returns_200_and_sets_reason(client: AsyncClient):
    doctor_id = await seed_doctor(client, email="cancel@clinic.com", crm="CRM00010")
    patient_id = await seed_patient(client, email="cancel@doe.com", cpf="20022233344")

    created = await client.post(APPOINTMENT_URL, json={
        "patient_id": patient_id, "doctor_id": doctor_id, "date": iso(future_valid_datetime(extra_days=11)),
    })
    appointment_id = created.json()["id"]

    response = await client.post(f"{APPOINTMENT_URL}{appointment_id}/cancel", json={
        "cancellation_reason": "PATIENT_CANCELED"
    })

    assert response.status_code == 200
    assert response.json()["cancellation_reason"] == "PATIENT_CANCELED"


@pytest.mark.integration
async def test_cancel_already_cancelled_returns_409(client: AsyncClient):
    doctor_id = await seed_doctor(client, email="cancel2@clinic.com", crm="CRM00011")
    patient_id = await seed_patient(client, email="cancel2@doe.com", cpf="30033344455")

    created = await client.post(APPOINTMENT_URL, json={
        "patient_id": patient_id, "doctor_id": doctor_id, "date": iso(future_valid_datetime(extra_days=12)),
    })
    appointment_id = created.json()["id"]

    await client.post(f"{APPOINTMENT_URL}{appointment_id}/cancel", json={"cancellation_reason": "OTHER"})
    response = await client.post(f"{APPOINTMENT_URL}{appointment_id}/cancel", json={"cancellation_reason": "OTHER"})

    assert response.status_code == 409


# --- GET /api/appointments/ and /{id} ---

@pytest.mark.integration
async def test_list_appointments_excludes_cancelled_by_default(client: AsyncClient):
    doctor_id = await seed_doctor(client, email="list@clinic.com", crm="CRM00012")
    patient_id = await seed_patient(client, email="list@doe.com", cpf="40044455566")

    created = await client.post(APPOINTMENT_URL, json={
        "patient_id": patient_id, "doctor_id": doctor_id, "date": iso(future_valid_datetime(extra_days=13)),
    })
    appointment_id = created.json()["id"]
    await client.post(f"{APPOINTMENT_URL}{appointment_id}/cancel", json={"cancellation_reason": "OTHER"})

    response = await client.get(f"{APPOINTMENT_URL}?patient_id={patient_id}")
    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["items"]]
    assert appointment_id not in ids

    response_all = await client.get(f"{APPOINTMENT_URL}?patient_id={patient_id}&active_only=false")
    ids_all = [item["id"] for item in response_all.json()["items"]]
    assert appointment_id in ids_all


@pytest.mark.integration
async def test_get_by_id_for_cancelled_appointment_returns_404_by_default(client: AsyncClient):
    doctor_id = await seed_doctor(client, email="getcancel@clinic.com", crm="CRM00013")
    patient_id = await seed_patient(client, email="getcancel@doe.com", cpf="50055566677")

    created = await client.post(APPOINTMENT_URL, json={
        "patient_id": patient_id, "doctor_id": doctor_id, "date": iso(future_valid_datetime(extra_days=14)),
    })
    appointment_id = created.json()["id"]
    await client.post(f"{APPOINTMENT_URL}{appointment_id}/cancel", json={"cancellation_reason": "OTHER"})

    default_response = await client.get(f"{APPOINTMENT_URL}{appointment_id}")
    assert default_response.status_code == 404

    explicit_response = await client.get(f"{APPOINTMENT_URL}{appointment_id}?active_only=false")
    assert explicit_response.status_code == 200


# --- validation/edge-case fixes from code review ---

@pytest.mark.integration
async def test_reschedule_cancelled_appointment_returns_409(client: AsyncClient):
    doctor_id = await seed_doctor(client, email="reschedcancel@clinic.com", crm="CRM00014")
    patient_id = await seed_patient(client, email="reschedcancel@doe.com", cpf="60066677788")

    created = await client.post(APPOINTMENT_URL, json={
        "patient_id": patient_id, "doctor_id": doctor_id, "date": iso(future_valid_datetime(extra_days=15)),
    })
    appointment_id = created.json()["id"]
    await client.post(f"{APPOINTMENT_URL}{appointment_id}/cancel", json={"cancellation_reason": "OTHER"})

    response = await client.patch(f"{APPOINTMENT_URL}{appointment_id}", json={
        "date": iso(future_valid_datetime(extra_days=16))
    })

    assert response.status_code == 409


@pytest.mark.integration
async def test_reschedule_with_null_date_returns_400(client: AsyncClient):
    doctor_id = await seed_doctor(client, email="nulldate@clinic.com", crm="CRM00015")
    patient_id = await seed_patient(client, email="nulldate@doe.com", cpf="70077788899")

    created = await client.post(APPOINTMENT_URL, json={
        "patient_id": patient_id, "doctor_id": doctor_id, "date": iso(future_valid_datetime(extra_days=17)),
    })
    appointment_id = created.json()["id"]

    response = await client.patch(f"{APPOINTMENT_URL}{appointment_id}", json={"date": None})

    assert response.status_code == 400


@pytest.mark.integration
async def test_schedule_with_timezone_aware_date_returns_422(client: AsyncClient):
    doctor_id = await seed_doctor(client, email="tzaware@clinic.com", crm="CRM00016")
    patient_id = await seed_patient(client, email="tzaware@doe.com", cpf="80088899900")

    response = await client.post(APPOINTMENT_URL, json={
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "date": future_valid_datetime(extra_days=18).isoformat() + "Z",
    })

    assert response.status_code == 422


@pytest.mark.integration
async def test_schedule_with_mismatched_doctor_speciality_returns_400(client: AsyncClient):
    doctor_id = await seed_doctor(client, email="mismatch@clinic.com", crm="CRM00017", speciality="CARDIOLOGY")
    patient_id = await seed_patient(client, email="mismatch@doe.com", cpf="90099900011")

    response = await client.post(APPOINTMENT_URL, json={
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "date": iso(future_valid_datetime(extra_days=19)),
        "speciality": "DERMATOLOGY",
    })

    assert response.status_code == 400


@pytest.mark.integration
async def test_list_appointments_with_doctor_id_zero_returns_422(client: AsyncClient):
    doctor_id = await seed_doctor(client, email="zeroid@clinic.com", crm="CRM00018")
    patient_id = await seed_patient(client, email="zeroid@doe.com", cpf="10100011122")

    await client.post(APPOINTMENT_URL, json={
        "patient_id": patient_id, "doctor_id": doctor_id, "date": iso(future_valid_datetime(extra_days=20)),
    })

    response = await client.get(f"{APPOINTMENT_URL}?doctor_id=0")

    assert response.status_code == 422
