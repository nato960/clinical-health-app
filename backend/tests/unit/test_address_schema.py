from pydantic import ValidationError
import pytest

from app.schemas.shared import AddressSchema


# --- zip_code ---

def test_zip_code_with_dash_is_valid():
    AddressSchema(zip_code="01310-100")


def test_zip_code_without_dash_is_valid():
    AddressSchema(zip_code="01310100")


def test_zip_code_invalid_raises():
    with pytest.raises(ValidationError):
        AddressSchema(zip_code="abc-def")


# --- state ---

def test_state_two_chars_is_valid():
    AddressSchema(state="SP")


def test_state_too_short_raises():
    with pytest.raises(ValidationError):
        AddressSchema(state="S")


def test_state_too_long_raises():
    with pytest.raises(ValidationError):
        AddressSchema(state="SPX")
