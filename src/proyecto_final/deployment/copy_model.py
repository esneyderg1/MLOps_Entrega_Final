"""Copia el modelo champion del Model Registry a disco (actividad 10).

El servicio de predicción (`proyecto_final.deployment.app`) NO se conecta al
Tracking Server en el momento de predecir: carga una copia local congelada.
Este script es el puente entre ambos mundos — se corre a mano cada vez que el
alias `champion` se mueve a una versión nueva (después de `registry_flow`).

¿Por qué una copia y no una conexión en vivo? Dentro de un contenedor Docker,
"127.0.0.1:5000" (configs/config.yaml) apunta al propio contenedor, no al
Tracking Server del host: el servicio tendría que depender de configuración de
red adicional (host.docker.internal, --network=host) solo para servir
predicciones. Copiando el modelo a disco ANTES del build, la imagen queda
autocontenida.

Ejecutar (con el MLflow Tracking Server corriendo y un champion ya registrado):
    uv run python -m proyecto_final.deployment.copy_model
"""

import json
import shutil
from datetime import UTC, datetime

import mlflow
from mlflow.tracking import MlflowClient

from proyecto_final.config import REPO_ROOT, enable_utf8_output, get_config
from proyecto_final.flows.registry_flow import SKOPS_TRUSTED_TYPES

CHAMPION_ALIAS = "champion"
LOCAL_MODEL_DIRNAME = "champion"
METADATA_FILENAME = "deployment_metadata.json"


def copy_champion_to_disk() -> dict:
    """Descarga el pipeline con alias `champion` y lo deja listo en `models/champion/`."""
    enable_utf8_output()
    config = get_config()
    mlflow.set_tracking_uri(config["mlflow"]["tracking_uri"])
    registered_name = config["mlflow"]["registered_model_name"]

    client = MlflowClient()
    version_info = client.get_model_version_by_alias(registered_name, CHAMPION_ALIAS)

    model_uri = f"models:/{registered_name}@{CHAMPION_ALIAS}"
    pipeline = mlflow.sklearn.load_model(model_uri)

    local_dir = REPO_ROOT / config["paths"]["models"] / LOCAL_MODEL_DIRNAME
    if local_dir.exists():
        # Se reemplaza por completo: una copia vieja con archivos de una
        # versión distinta a medio mezclar sería peor que fallar temprano.
        shutil.rmtree(local_dir)
    # El pipeline se guarda con skops (mismo formato con que registry_flow lo
    # registró); hay que declarar los mismos tipos de confianza o falla al
    # verificar el archivo recién escrito (RandomForest usa sklearn.tree._tree.Tree).
    mlflow.sklearn.save_model(
        pipeline, path=str(local_dir), skops_trusted_types=SKOPS_TRUSTED_TYPES
    )

    metadata = {
        "registered_model_name": registered_name,
        "alias": CHAMPION_ALIAS,
        "version": version_info.version,
        "run_id": version_info.run_id,
        "rmse": float(version_info.tags.get("rmse", "nan")),
        "mae": float(version_info.tags.get("mae", "nan")),
        "r2": float(version_info.tags.get("r2", "nan")),
        "copied_at": datetime.now(UTC).isoformat(),
    }
    (local_dir / METADATA_FILENAME).write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"Champion v{version_info.version} copiado a {local_dir}")
    print(
        f"RMSE={metadata['rmse']:,.0f} USD | MAE={metadata['mae']:,.0f} | "
        f"R²={metadata['r2']:.3f}"
    )
    return metadata


if __name__ == "__main__":
    copy_champion_to_disk()
