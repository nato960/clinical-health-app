from datetime import date, timedelta

from pydantic import ValidationError
import pytest

from app.schemas.patient_schema import PatientCreate


def make_valid_patient(**overrides):
    data = {
        "name": "Maria Souza",
        "email": "maria@email.com",
        "cpf": "123.456.789-00",
        "phone": "11999999999",
    }
    return {**data, **overrides}


# --- birth_date ---

def test_patient_birth_date_past_is_valid():
    PatientCreate(**make_valid_patient(birth_date=date.today() - timedelta(days=1)))


def test_patient_birth_date_today_raises():
    with pytest.raises(ValidationError):
        PatientCreate(**make_valid_patient(birth_date=date.today()))


def test_patient_birth_date_future_raises():
    with pytest.raises(ValidationError):
        PatientCreate(**make_valid_patient(birth_date=date.today() + timedelta(days=1)))


def test_patient_birth_date_none_is_valid():
    PatientCreate(**make_valid_patient(birth_date=None))


# --- name ---

def test_patient_name_too_short_raises():
    with pytest.raises(ValidationError):
        PatientCreate(**make_valid_patient(name="A"))


def test_patient_name_min_length_is_valid():
    PatientCreate(**make_valid_patient(name="Ab"))


def test_patient_name_too_long_raises():
    with pytest.raises(ValidationError):
        PatientCreate(**make_valid_patient(name="A" * 101))


# --- cpf ---

def test_patient_cpf_with_punctuation_is_valid():
    PatientCreate(**make_valid_patient(cpf="123.456.789-00"))


def test_patient_cpf_without_punctuation_is_valid():
    PatientCreate(**make_valid_patient(cpf="12345678900"))


def test_patient_cpf_invalid_raises():
    with pytest.raises(ValidationError):
        PatientCreate(**make_valid_patient(cpf="abc-def-ghi"))
