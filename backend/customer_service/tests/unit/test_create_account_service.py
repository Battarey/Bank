from uuid import uuid4

import pytest

from customer_service.create_account.service import (
    _normalize_contacts_payload,
    _normalize_identifiers_payload,
    _normalize_passport_payload,
    _normalize_personal_payload,
)
from shared import schemas

def test_normalize_personal_payload():
    payload = schemas.PersonalDataPayload(
        first_name="  ИВАН  ",
        last_name="иванов",
        middle_name=" Иванович ",
        birth_date="1990-01-01",
        gender="M",
    )
    result = _normalize_personal_payload(payload)
    assert result.first_name == "ИВАН"
    assert result.last_name == "ИВАНОВ"
    assert result.middle_name == "ИВАНОВИЧ"


def test_normalize_passport_payload():
    payload = schemas.PassportPayload(
        series="1234",
        number="567890",
        issued_by="  Отдел УФМС России  ",
        issued_at="2010-01-01",
        expiration_date="2030-01-01",
        division_code="123-456",
        registration_address="  г. Москва, ул. Пушкина, д. Колотушкина  ",
    )
    result = _normalize_passport_payload(payload)
    assert result.issued_by == "Отдел УФМС России"
    assert result.registration_address == "г. Москва, ул. Пушкина, д. Колотушкина"


def test_normalize_identifiers_payload():
    payload = schemas.IdentifiersPayload(
        inn="123456789012",
        snils="12345678901",
    )
    result = _normalize_identifiers_payload(payload)
    assert result.inn == "123456789012"
    assert result.snils == "12345678901"


def test_normalize_contacts_payload():
    payload = schemas.ContactsPayload(
        email="Test@Example.com",
        phone="+79991234567",
    )
    result = _normalize_contacts_payload(payload)
    assert result.email == "test@example.com"
    assert result.phone == "+79991234567"
