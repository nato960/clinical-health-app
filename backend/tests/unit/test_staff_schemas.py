from datetime import date, timedelta

from pydantic import ValidationError
import pytest

from app.models.enums import Sector
from app.schemas.staff_schema import StaffCreate


def make_valid_staff(**overrides):
    data = {
        "name": "Ana Souza",
        "email": "ana@email.com",
        "cpf": "123.456.789-00",
        "phone": "11999999999",
        "sector": Sector.RECEPTION,
    }
    return {**data, **overrides}


# --- birth_date ---

def test_staff_birth_date_past_is_valid():
    StaffCreate(**make_valid_staff(birth_date=date.today() - timedelta(days=1)))


def test_staff_birth_date_today_raises():
    with pytest.raises(ValidationError):
        StaffCreate(**make_valid_staff(birth_date=date.today()))


def test_staff_birth_date_future_raises():
    with pytest.raises(ValidationError):
        StaffCreate(**make_valid_staff(birth_date=date.today() + timedelta(days=1)))


def test_staff_birth_date_none_is_valid():
    StaffCreate(**make_valid_staff(birth_date=None))


# --- name ---

def test_staff_name_too_short_raises():
    with pytest.raises(ValidationError):
        StaffCreate(**make_valid_staff(name="A"))


def test_staff_name_min_length_is_valid():
    StaffCreate(**make_valid_staff(name="Ab"))


def test_staff_name_too_long_raises():
    with pytest.raises(ValidationError):
        StaffCreate(**make_valid_staff(name="A" * 101))


# --- cpf ---

def test_staff_cpf_with_punctuation_is_valid():
    StaffCreate(**make_valid_staff(cpf="123.456.789-00"))


def test_staff_cpf_without_punctuation_is_valid():
    StaffCreate(**make_valid_staff(cpf="12345678900"))


def test_staff_cpf_invalid_raises():
    with pytest.raises(ValidationError):
        StaffCreate(**make_valid_staff(cpf="abc-def-ghi"))


# --- sector ---

def test_staff_sector_required():
    with pytest.raises(ValidationError):
        StaffCreate(**{k: v for k, v in make_valid_staff().items() if k != "sector"})


def test_staff_sector_invalid_value_raises():
    with pytest.raises(ValidationError):
        StaffCreate(**make_valid_staff(sector="NOT_A_SECTOR"))
