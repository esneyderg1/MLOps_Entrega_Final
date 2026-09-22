"""Tests de proyecto_final.deployment.copy_model (actividad 10).

No toca un MLflow Tracking Server real: se reemplaza el nombre `mlflow`
completo dentro del módulo bajo prueba por un MagicMock. Mockear solo
`mlflow.sklearn.load_model` (un atributo anidado del módulo real) no basta:
la función real hace su propia resolución interna del alias vía un
MlflowClient nuevo y termina llamando por red de todas formas si algo se
escapa sin mockear.
"""

import json
from pathlib import Path
from unittest.mock import Mock, patch

from proyecto_final.deployment.copy_model import copy_champion_to_disk

FAKE_CONFIG = {
    "mlflow": {
        "tracking_uri": "http://127.0.0.1:5000",
        "registered_model_name": "salarios-ai-ml-model",
    },
    "paths": {"models": "models"},
}


def _fake_save_model(pipeline, path, **kwargs):
    """Simula que mlflow.sklearn.save_model crea el directorio del modelo."""
    Path(path).mkdir(parents=True, exist_ok=True)


def test_copy_champion_to_disk_escribe_metadata_de_despliegue(tmp_path):
    version_info = Mock(
        version="3",
        run_id="abc123",
        tags={"rmse": "68142.31", "mae": "48224.23", "r2": "0.234"},
    )
    fake_client = Mock()
    fake_client.get_model_version_by_alias.return_value = version_info

    with (
        patch(
            "proyecto_final.deployment.copy_model.get_config", return_value=FAKE_CONFIG
        ),
        patch("proyecto_final.deployment.copy_model.REPO_ROOT", tmp_path),
        patch(
            "proyecto_final.deployment.copy_model.MlflowClient",
            return_value=fake_client,
        ),
        patch("proyecto_final.deployment.copy_model.mlflow") as mock_mlflow,
    ):
        mock_mlflow.sklearn.load_model.return_value = Mock()
        mock_mlflow.sklearn.save_model.side_effect = _fake_save_model

        metadata = copy_champion_to_disk()

    mock_mlflow.sklearn.save_model.assert_called_once()
    assert metadata["version"] == "3"
    assert metadata["run_id"] == "abc123"
    assert metadata["rmse"] == 68142.31
    assert metadata["alias"] == "champion"

    metadata_file = tmp_path / "models" / "champion" / "deployment_metadata.json"
    assert json.loads(metadata_file.read_text(encoding="utf-8")) == metadata


def test_copy_champion_to_disk_reemplaza_una_copia_previa(tmp_path):
    """Una copia vieja de otra versión no debe dejar archivos mezclados."""
    old_dir = tmp_path / "models" / "champion"
    old_dir.mkdir(parents=True)
    (old_dir / "archivo_viejo.txt").write_text("version anterior", encoding="utf-8")

    version_info = Mock(
        version="2",
        run_id="def456",
        tags={"rmse": "70000.0", "mae": "50000.0", "r2": "0.2"},
    )
    fake_client = Mock()
    fake_client.get_model_version_by_alias.return_value = version_info

    with (
        patch(
            "proyecto_final.deployment.copy_model.get_config", return_value=FAKE_CONFIG
        ),
        patch("proyecto_final.deployment.copy_model.REPO_ROOT", tmp_path),
        patch(
            "proyecto_final.deployment.copy_model.MlflowClient",
            return_value=fake_client,
        ),
        patch("proyecto_final.deployment.copy_model.mlflow") as mock_mlflow,
    ):
        mock_mlflow.sklearn.load_model.return_value = Mock()
        mock_mlflow.sklearn.save_model.side_effect = _fake_save_model

        copy_champion_to_disk()

    assert not (old_dir / "archivo_viejo.txt").exists()
