"""Tests de proyecto_final.deployment.app (actividad 10).

No depende de un modelo real en disco: `ModelLoader.load()` (llamado en el
lifespan de FastAPI) se mockea, y el estado de `model_loader` se fija a mano
antes de cada request.
"""

from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from proyecto_final.deployment.app import app
from proyecto_final.deployment.model_loader import model_loader

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

FAKE_METADATA = {
    "registered_model_name": "salarios-ai-ml-model",
    "version": "1",
    "alias": "champion",
    "rmse": 68142.0,
}


@pytest.fixture(autouse=True)
def _mock_model_load():
    """El lifespan de la app llama a `model_loader.load()`: se mockea en todos los tests."""
    with patch.object(model_loader, "load"):
        yield


def _client_con_modelo_simulado(predictions):
    """TestClient con el lifespan real, pero `load()` no-op y el pipeline mockeado."""
    model_loader.pipeline = Mock()
    model_loader.pipeline.predict.return_value = predictions
    model_loader.feature_columns = list(VALID_PAYLOAD.keys())
    model_loader.metadata = FAKE_METADATA
    return TestClient(app)


def test_health_devuelve_healthy_con_modelo_cargado():
    client = _client_con_modelo_simulado([100000.0])
    with client:
        response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["model_version"] == "1"


def test_predict_devuelve_salario_estimado():
    client = _client_con_modelo_simulado([162537.71])
    with client:
        response = client.post("/predict", json=VALID_PAYLOAD)

    assert response.status_code == 200
    body = response.json()
    assert body["predicted_salary_usd"] == 162537.71
    assert body["model_alias"] == "champion"


def test_predict_batch_devuelve_una_prediccion_por_registro():
    client = _client_con_modelo_simulado([100000.0, 200000.0])
    with client:
        response = client.post(
            "/predict/batch", json={"records": [VALID_PAYLOAD, VALID_PAYLOAD]}
        )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert len(body["predictions"]) == 2


def test_predict_con_payload_invalido_devuelve_422():
    """Un código fuera del dominio (experience_level) lo rechaza Pydantic, no el modelo."""
    client = _client_con_modelo_simulado([0.0])
    payload = {**VALID_PAYLOAD, "experience_level": "INVALIDO"}

    with client:
        response = client.post("/predict", json=payload)

    assert response.status_code == 422


def test_root_sirve_interfaz_web():
    client = _client_con_modelo_simulado([0.0])
    with client:
        response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
