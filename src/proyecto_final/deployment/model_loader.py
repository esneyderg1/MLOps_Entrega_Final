"""Carga el modelo champion desde disco para servir predicciones (actividad 10).

Lee la copia local que dejó `copy_model.py` (no el Tracking Server en vivo):
el servicio de predicción no depende de que MLflow esté corriendo en el
momento de responder un request. `ModelLoader.load()` se llama UNA vez al
iniciar la API (ver `app.py`), no en cada request — cargar el pipeline en
cada predicción sería carísimo e innecesario.
"""

import json
import logging

import mlflow
import pandas as pd

from proyecto_final.config import REPO_ROOT, get_config
from proyecto_final.deployment.copy_model import LOCAL_MODEL_DIRNAME, METADATA_FILENAME

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class ModelLoader:
    """Mantiene el pipeline champion y su metadata en memoria."""

    def __init__(self) -> None:
        self.pipeline = None
        self.metadata: dict | None = None
        self.feature_columns: list[str] = []

    def load(self) -> None:
        """Carga el pipeline y su metadata desde `models/champion/`."""
        config = get_config()
        model_dir = REPO_ROOT / config["paths"]["models"] / LOCAL_MODEL_DIRNAME
        metadata_path = model_dir / METADATA_FILENAME

        if not model_dir.exists() or not metadata_path.exists():
            raise FileNotFoundError(
                f"No hay modelo copiado en {model_dir}. Ejecuta primero: "
                "uv run python -m proyecto_final.deployment.copy_model"
            )

        self.metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        self.pipeline = mlflow.sklearn.load_model(str(model_dir))
        self.feature_columns = (
            config["features"]["categorical"] + config["features"]["numerical"]
        )
        logger.info(
            "Champion v%s cargado (RMSE=%.0f USD)",
            self.metadata["version"],
            self.metadata["rmse"],
        )

    def is_loaded(self) -> bool:
        return self.pipeline is not None

    def predict(self, records: list[dict]) -> list[float]:
        """Predice el salario en USD para cada registro (dict con datos crudos)."""
        if self.pipeline is None:
            raise RuntimeError("Modelo no cargado. Llama a load() primero.")
        x = pd.DataFrame.from_records(records)[self.feature_columns]
        return [float(pred) for pred in self.pipeline.predict(x)]


# Instancia global: un solo pipeline en memoria compartido por todos los requests.
model_loader = ModelLoader()
