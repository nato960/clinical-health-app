from datetime import date, timedelta

from pydantic import ValidationError
import pytest

from app.models.enums import Speciality
from app.schemas.doctor_schema import DoctorCreate
from app.schemas.shared import AddressSchema


def make_valid_doctor(**overrides):
    data = {
        "name": "João Silva",
        "email": "joao@email.com",
        "crm": "12345",
        "phone": "11999999999",
        "speciality": Speciality.CARDIOLOGY,
    }
    return {**data, **overrides}


# --- birth_date ---

def test_birth_date_past_is_valid():
    DoctorCreate(**make_valid_doctor(birth_date=date.today() - timedelta(days=1)))


def test_birth_date_today_raises():
    with pytest.raises(ValidationError):
        DoctorCreate(**make_valid_doctor(birth_date=date.today()))


def test_birth_date_future_raises():
    with pytest.raises(ValidationError):
        DoctorCreate(**make_valid_doctor(birth_date=date.today() + timedelta(days=1)))


def test_birth_date_none_is_valid():
    DoctorCreate(**make_valid_doctor(birth_date=None))


# --- name ---

def test_name_too_short_raises():
    with pytest.raises(ValidationError):
        DoctorCreate(**make_valid_doctor(name="A"))


def test_name_min_length_is_valid():
    DoctorCreate(**make_valid_doctor(name="Ab"))


def test_name_too_long_raises():
    with pytest.raises(ValidationError):
        DoctorCreate(**make_valid_doctor(name="A" * 101))


# --- crm ---

def test_crm_too_short_raises():
    with pytest.raises(ValidationError):
        DoctorCreate(**make_valid_doctor(crm="123"))


def test_crm_min_length_is_valid():
    DoctorCreate(**make_valid_doctor(crm="1234"))


def test_crm_too_long_raises():
    with pytest.raises(ValidationError):
        DoctorCreate(**make_valid_doctor(crm="A" * 21))


# --- AddressSchema.zip_code ---

def test_zip_code_with_dash_is_valid():
    AddressSchema(zip_code="01310-100")


def test_zip_code_without_dash_is_valid():
    AddressSchema(zip_code="01310100")


def test_zip_code_invalid_raises():
    with pytest.raises(ValidationError):
        AddressSchema(zip_code="abc-def")


# --- AddressSchema.state ---

def test_state_two_chars_is_valid():
    AddressSchema(state="SP")


def test_state_too_short_raises():
    with pytest.raises(ValidationError):
        AddressSchema(state="S")


def test_state_too_long_raises():
    with pytest.raises(ValidationError):
        AddressSchema(state="SPX")

