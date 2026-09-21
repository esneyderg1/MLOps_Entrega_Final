"""Flow de Prefect para registrar el modelo candidato en el Model Registry (actividad 8).

Reentrena el candidato (los mejores hiperparámetros de Optuna, fijados en
`configs/config.yaml -> training.candidate`), lo registra como PIPELINE COMPLETO
(preprocesador + modelo) con signature e input_example, le asigna el alias
`champion` y verifica que la carga por alias predice correctamente.

¿Por qué reentrenar en vez de reusar el modelo del trial ganador? Dos razones:
1. El tracking es local por máquina (SQLite): el artifact de ese trial vive en
   el mlflow.db de quien corrió el estudio.
2. Los trials no loguean signature ni input_example (regla 2 exige ambos para el
   Registry). El reentrenamiento es reproducible: mismos datos + mismos params +
   mismo random_state dan el mismo RMSE (verificado: 68.142 USD).

Requiere el MLflow Tracking Server corriendo y data/processed/ generado.
Ejecutar de punta a punta con:
    uv run python -m proyecto_final.flows.registry_flow
"""

import json
from pathlib import Path

import mlflow
import pandas as pd
from mlflow.models.signature import infer_signature
from mlflow.tracking import MlflowClient
from prefect import flow, task
from sklearn.pipeline import Pipeline

from proyecto_final.config import REPO_ROOT, enable_utf8_output, get_config
from proyecto_final.models.training import (
    build_rf_pipeline,
    evaluate_regression,
    prepare_features,
)

SKOPS_TRUSTED_TYPES = [
    "numpy.dtype",
    "sklearn.compose._column_transformer._RemainderColsList",
    "sklearn.tree._tree.Tree",
]

CHAMPION_ALIAS = "champion"


@task(log_prints=True)
def load_processed_task(
    processed_dir: Path, config: dict
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Carga train/validación; falla claro si no se ha corrido el processing_flow."""
    train_path = processed_dir / config["processed"]["train_filename"]
    val_path = processed_dir / config["processed"]["validation_filename"]
    if not train_path.exists() or not val_path.exists():
        raise FileNotFoundError(
            f"Faltan datos procesados en {processed_dir}. Ejecuta primero: "
            "uv run python -m proyecto_final.flows.processing_flow"
        )
    train, validation = pd.read_parquet(train_path), pd.read_parquet(val_path)
    print(f"Train: {train.shape} | Validación: {validation.shape}")
    return train, validation


@task(log_prints=True)
def train_candidate_task(
    train: pd.DataFrame, validation: pd.DataFrame, config: dict
) -> tuple[Pipeline, dict[str, float]]:
    """Reentrena el candidato con los hiperparámetros fijados en config."""
    features = config["features"]
    target = config["dataset"]["target_column"]
    x_train, y_train = prepare_features(
        train, features["categorical"], features["numerical"], target
    )
    x_val, y_val = prepare_features(
        validation, features["categorical"], features["numerical"], target
    )

    pipeline = build_rf_pipeline(
        features["categorical"],
        features["numerical"],
        config["training"]["random_state"],
        **config["training"]["candidate"],
    )
    pipeline.fit(x_train, y_train)
    metrics = evaluate_regression(y_val, pipeline.predict(x_val))

    print(
        f"Candidato reentrenado: RMSE={metrics['rmse']:,.0f} USD | "
        f"MAE={metrics['mae']:,.0f} | R²={metrics['r2']:.3f}"
    )
    return pipeline, metrics


@task(log_prints=True)
def register_champion_task(
    pipeline: Pipeline,
    metrics: dict[str, float],
    validation: pd.DataFrame,
    config: dict,
) -> str:
    """Loguea el candidato con signature + input_example, lo registra y le asigna el alias."""
    features = config["features"]
    registered_name = config["mlflow"]["registered_model_name"]

    # Muestra de datos CRUDOS de validación: documenta el contrato de entrada
    # real del modelo (lo que recibirá el deploy) y MLflow lo valida al servirlo.
    input_example = validation[features["categorical"] + features["numerical"]].head(5)
    signature = infer_signature(input_example, pipeline.predict(input_example))

    with mlflow.start_run(run_name="register_champion"):
        mlflow.set_tags(
            {
                "stage": "register",
                "dataset": config["dataset"]["name"],
                "decision": "mejor trial de optuna; ninguna familia lo supero (ver docs/decisiones.md)",
            }
        )
        mlflow.log_params(config["training"]["candidate"])
        mlflow.log_metrics(metrics)

        mlflow.sklearn.log_model(
            pipeline,
            name="model",
            signature=signature,
            input_example=input_example,
            registered_model_name=registered_name,
            skops_trusted_types=SKOPS_TRUSTED_TYPES,
        )

    # La versión recién creada, con search_model_versions (get_latest_versions
    # depende de los stages deprecados; regla 2: aliases, no stages).
    client = MlflowClient()
    versions = client.search_model_versions(f"name='{registered_name}'")
    new_version = max(versions, key=lambda v: int(v.creation_timestamp)).version
    client.set_registered_model_alias(registered_name, CHAMPION_ALIAS, new_version)

    # ---- Metadata del catálogo: que la pestaña Models se explique sola ----
    # La descripción del MODELO cuenta qué es y cómo consumirlo (estable entre
    # versiones); la de la VERSIÓN cuenta qué tiene ESTA versión y de dónde salió.
    client.update_registered_model(
        name=registered_name,
        description=(
            "Estimador de salario anual de referencia (USD) para roles de datos/IA. "
            "Pipeline completo: recibe datos CRUDOS con las columnas "
            f"{features['categorical'] + features['numerical']} y devuelve el salario "
            "estimado en USD (ver signature e input example de cada versión). "
            f"Consumir SIEMPRE por alias: models:/{registered_name}@{CHAMPION_ALIAS}. "
            "Decisión del candidato y evidencia: docs/decisiones.md del repo."
        ),
    )
    candidate_params = config["training"]["candidate"]
    client.update_model_version(
        name=registered_name,
        version=new_version,
        description=(
            "RandomForest con los mejores hiperparámetros del estudio de Optuna "
            f"({candidate_params}). Validación temporal (train work_year<=2024, "
            f"validación 2025): RMSE {metrics['rmse']:,.0f} USD | "
            f"MAE {metrics['mae']:,.0f} | R² {metrics['r2']:.3f}. "
            "Elegido tras comparar 6 alternativas (lineal, ridge, boosting ± log-target): "
            "ninguna lo superó."
        ),
    )
    # Tags de la versión: params y métricas consultables/filtrables sin abrir el run.
    for name, value in candidate_params.items():
        client.set_model_version_tag(
            registered_name, new_version, f"param_{name}", str(value)
        )
    for name, value in metrics.items():
        client.set_model_version_tag(registered_name, new_version, name, f"{value:.4f}")
    # Versión de los datos con que se entrenó (hash del processing_flow), para
    # poder auditar "¿con qué datos exactos se construyó este modelo?".
    processed_meta = REPO_ROOT / config["paths"]["processed"] / "metadata.json"
    if processed_meta.exists():
        train_sha = json.loads(processed_meta.read_text(encoding="utf-8"))[
            config["processed"]["train_filename"]
        ]["sha256"]
        client.set_model_version_tag(
            registered_name, new_version, "train_data_sha256", train_sha
        )

    print(f"Registrado: {registered_name} v{new_version} -> alias '{CHAMPION_ALIAS}'")
    print("Descripción y tags del catálogo escritos (modelo y versión)")
    return new_version


@task(log_prints=True)
def verify_champion_task(validation: pd.DataFrame, config: dict) -> None:
    """Verificación del criterio de terminado: cargar por alias y predecir.

    Simula exactamente lo que hará el deploy: pedir 'models:/<nombre>@champion'
    (sin saber el número de versión) y pasarle datos crudos.
    """
    features = config["features"]
    registered_name = config["mlflow"]["registered_model_name"]

    champion = mlflow.sklearn.load_model(f"models:/{registered_name}@{CHAMPION_ALIAS}")
    muestra = validation[features["categorical"] + features["numerical"]].head(5)
    predicciones = champion.predict(muestra)
    reales = validation[config["dataset"]["target_column"]].head(5).to_numpy()

    for pred, real in zip(predicciones, reales):
        print(f"  predicho: ${pred:,.0f} | real: ${real:,.0f}")
    print(f"Carga por alias '{CHAMPION_ALIAS}' verificada: el champion predice OK")


@flow(name="registro-modelo-candidato", log_prints=True)
def registry_flow() -> dict:
    """Orquesta la actividad 8: reentrenar candidato -> registrar -> alias -> verificar."""
    enable_utf8_output()  # los emojis de MLflow rompen la consola cp1252 de Windows
    config = get_config()

    mlflow.set_tracking_uri(config["mlflow"]["tracking_uri"])
    mlflow.set_experiment(config["mlflow"]["experiment_name"])

    processed_dir = REPO_ROOT / config["paths"]["processed"]
    train, validation = load_processed_task(processed_dir, config)

    pipeline, metrics = train_candidate_task(train, validation, config)
    version = register_champion_task(pipeline, metrics, validation, config)
    verify_champion_task(validation, config)

    return {
        "registered_model": config["mlflow"]["registered_model_name"],
        "version": version,
        "alias": CHAMPION_ALIAS,
        "metrics": metrics,
    }


if __name__ == "__main__":
    registry_flow()
