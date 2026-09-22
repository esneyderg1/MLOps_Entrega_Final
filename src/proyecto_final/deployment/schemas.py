"""Esquemas Pydantic del servicio de predicción (actividad 10).

Las columnas y sus valores válidos reflejan exactamente `configs/config.yaml`
(features.categorical/numerical) y `docs/dataset.md` (leyenda de códigos):
si el dataset cambiara esas columnas, este archivo debe actualizarse también.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SalaryRequest(BaseModel):
    """Datos crudos de un puesto: las mismas columnas que espera el pipeline."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "work_year": 2025,
                "experience_level": "SE",
                "employment_type": "FT",
                "job_title": "Data Scientist",
                "employee_residence": "US",
                "remote_ratio": 100,
                "company_location": "US",
                "company_size": "M",
            }
        }
    )

    work_year: int = Field(
        ..., ge=2020, le=2030, description="Año del registro salarial"
    )
    experience_level: Literal["EN", "MI", "SE", "EX"] = Field(
        ..., description="Seniority: Entry, Mid, Senior, Executive"
    )
    employment_type: Literal["FT", "PT", "CT", "FL"] = Field(
        ..., description="Full-time, Part-time, Contract, Freelance"
    )
    job_title: str = Field(
        ...,
        min_length=1,
        description="Cargo (texto libre; el modelo se entrenó con los 15 más frecuentes + OTHER)",
    )
    employee_residence: str = Field(
        ..., min_length=2, max_length=2, description="País de residencia (código ISO-2)"
    )
    remote_ratio: Literal[0, 50, 100] = Field(
        ...,
        description="% de trabajo remoto: 0 presencial, 50 híbrido, 100 remoto total",
    )
    company_location: str = Field(
        ..., min_length=2, max_length=2, description="País de la empresa (código ISO-2)"
    )
    company_size: Literal["S", "M", "L"] = Field(
        ..., description="Tamaño de la empresa: Small, Medium, Large"
    )


class BatchSalaryRequest(BaseModel):
    """Request para predecir varios puestos en una sola llamada."""

    records: list[SalaryRequest] = Field(..., min_length=1, max_length=1000)


class PredictionResponse(BaseModel):
    """Salario de referencia estimado (USD) para un puesto."""

    predicted_salary_usd: float
    model_name: str
    model_version: str
    model_alias: str


class BatchPredictionResponse(BaseModel):
    predictions: list[PredictionResponse]
    total: int


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    model_name: str
    model_version: str
    model_rmse: float
