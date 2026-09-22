"""Tests de proyecto_final.deployment.schemas (actividad 10)."""

import pytest
from pydantic import ValidationError

from proyecto_final.deployment.schemas import BatchSalaryRequest, SalaryRequest

VALID_PAYLOAD = {
    "work_year": 2025,
    "experience_level": "SE",
    "employment_type": "FT",
    "job_title": "Data Scientist",
    "employee_residence": "US",
    "remote_ratio": 100,
    "company_location": "US",
    "company_size": "M",
}


def test_salary_request_acepta_payload_valido():
    request = SalaryRequest(**VALID_PAYLOAD)
    assert request.experience_level == "SE"
    assert request.remote_ratio == 100


@pytest.mark.parametrize(
    "field, value",
    [
        ("experience_level", "SENIOR"),
        ("employment_type", "XX"),
        ("remote_ratio", 25),
        ("company_size", "XL"),
        ("employee_residence", "USA"),
        ("job_title", ""),
    ],
)
def test_salary_request_rechaza_valores_fuera_de_dominio(field, value):
    """Los códigos categóricos deben ser exactamente los del diccionario de datos."""
    payload = {**VALID_PAYLOAD, field: value}
    with pytest.raises(ValidationError):
        SalaryRequest(**payload)


def test_batch_salary_request_exige_al_menos_un_registro():
    with pytest.raises(ValidationError):
        BatchSalaryRequest(records=[])


def test_batch_salary_request_acepta_varios_registros():
    batch = BatchSalaryRequest(records=[VALID_PAYLOAD, VALID_PAYLOAD])
    assert len(batch.records) == 2
