"""Tests de proyecto_final.deployment.model_loader (actividad 10).

No toca MLflow real: `mlflow.sklearn.load_model` se mockea y el modelo
copiado se simula escribiendo el `deployment_metadata.json` en un tmp_path.
"""

import json
from unittest.mock import Mock, patch

import pytest

from proyecto_final.deployment.model_loader import ModelLoader

FAKE_CONFIG = {
    "paths": {"models": "models"},
    "features": {"categorical": ["experience_level"], "numerical": ["work_year"]},
}

FAKE_METADATA = {
    "registered_model_name": "salarios-ai-ml-model",
    "alias": "champion",
    "version": "1",
    "rmse": 68142.0,
}


def _write_champion_dir(repo_root):
    model_dir = repo_root / "models" / "champion"
    model_dir.mkdir(parents=True)
    (model_dir / "deployment_metadata.json").write_text(
        json.dumps(FAKE_METADATA), encoding="utf-8"
    )
    return model_dir


def test_load_falla_claro_si_no_hay_modelo_copiado(tmp_path):
    """Sin `models/champion/`, debe fallar con un mensaje que diga qué correr."""
    loader = ModelLoader()
    with (
        patch(
            "proyecto_final.deployment.model_loader.get_config",
            return_value=FAKE_CONFIG,
        ),
        patch("proyecto_final.deployment.model_loader.REPO_ROOT", tmp_path),
        pytest.raises(FileNotFoundError, match="copy_model"),
    ):
        loader.load()


def test_load_carga_pipeline_y_metadata(tmp_path):
    _write_champion_dir(tmp_path)
    fake_pipeline = Mock()
    loader = ModelLoader()

    # Se reemplaza el nombre `mlflow` completo (no solo .sklearn.load_model):
    # mockear un atributo anidado del módulo real deja resquicios por donde
    # mlflow puede colarse a intentar red/disco real (visto empíricamente).
    with (
        patch(
            "proyecto_final.deployment.model_loader.get_config",
            return_value=FAKE_CONFIG,
        ),
        patch("proyecto_final.deployment.model_loader.REPO_ROOT", tmp_path),
        patch("proyecto_final.deployment.model_loader.mlflow") as mock_mlflow,
    ):
        mock_mlflow.sklearn.load_model.return_value = fake_pipeline
        loader.load()

    assert loader.is_loaded()
    assert loader.metadata == FAKE_METADATA
    assert loader.feature_columns == ["experience_level", "work_year"]
    mock_mlflow.sklearn.load_model.assert_called_once()


def test_predict_usa_solo_las_columnas_declaradas():
    """Una columna extra en el request (no declarada en config) se ignora."""
    loader = ModelLoader()
    loader.pipeline = Mock()
    loader.pipeline.predict.return_value = [100000.0, 200000.0]
    loader.feature_columns = ["experience_level", "work_year"]

    records = [
        {"experience_level": "SE", "work_year": 2025, "campo_extra": "ignorar"},
        {"experience_level": "EN", "work_year": 2024, "campo_extra": "ignorar"},
    ]

    predictions = loader.predict(records)

    assert predictions == [100000.0, 200000.0]
    called_df = loader.pipeline.predict.call_args[0][0]
    assert list(called_df.columns) == ["experience_level", "work_year"]


def test_predict_sin_cargar_lanza_error():
    loader = ModelLoader()
    with pytest.raises(RuntimeError, match="load"):
        loader.predict([{"experience_level": "SE", "work_year": 2025}])
