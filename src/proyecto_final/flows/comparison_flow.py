"""Flow de Prefect para comparar familias de modelos (insumo de la actividad 8).

Entrena 6 candidatos (lineal, ridge y gradient boosting; cada uno con target en
USD y en log1p) sobre los MISMOS datos y validación temporal del baseline, y
loguea cada uno como run de MLflow (params + métricas + tags).

Nota: estos runs son exploratorios y NO loguean el artefacto del modelo — el
ganador se reentrena con logging completo y se registra en el Model Registry en
la actividad 8. Así el tracking no se llena de modelos de descarte.

Requiere el MLflow Tracking Server corriendo y data/processed/ generado.
Ejecutar de punta a punta con:
    uv run python -m proyecto_final.flows.comparison_flow
"""

from pathlib import Path

import mlflow
import pandas as pd
from prefect import flow, task

from proyecto_final.config import REPO_ROOT, enable_utf8_output, get_config
from proyecto_final.models.comparison import candidate_pipelines
from proyecto_final.models.training import evaluate_regression, prepare_features


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
    name: str,
    pipeline: object,
    train: pd.DataFrame,
    validation: pd.DataFrame,
    config: dict,
) -> dict[str, float]:
    """Entrena un candidato y loguea params, métricas y tags en su run de MLflow."""
    features = config["features"]
    target = config["dataset"]["target_column"]
    x_train, y_train = prepare_features(
        train, features["categorical"], features["numerical"], target
    )
    x_val, y_val = prepare_features(
        validation, features["categorical"], features["numerical"], target
    )

    with mlflow.start_run(run_name=name):
        mlflow.set_tags(
            {
                "stage": "model-comparison",
                "dataset": config["dataset"]["name"],
                "target_transform": "log1p" if name.endswith("_log_target") else "none",
            }
        )
        mlflow.log_param("candidate", name)

        pipeline.fit(x_train, y_train)
        metrics = evaluate_regression(y_val, pipeline.predict(x_val))
        mlflow.log_metrics(metrics)

    print(f"{name}: RMSE={metrics['rmse']:,.0f} USD | R²={metrics['r2']:.3f}")
    return metrics


@flow(name="comparacion-familias-modelos", log_prints=True)
def comparison_flow() -> dict:
    """Orquesta la comparación: entrena los 6 candidatos y muestra el ranking."""
    enable_utf8_output()  # los emojis de MLflow rompen la consola cp1252 de Windows
    config = get_config()

    mlflow.set_tracking_uri(config["mlflow"]["tracking_uri"])
    mlflow.set_experiment(config["mlflow"]["experiment_name"])

    processed_dir = REPO_ROOT / config["paths"]["processed"]
    train, validation = load_processed_task(processed_dir, config)

    candidates = candidate_pipelines(
        config["features"]["categorical"],
        config["features"]["numerical"],
        config["training"]["random_state"],
        config["training"]["comparison"]["ridge_alpha"],
    )

    results = {
        name: train_candidate_task(name, pipeline, train, validation, config)
        for name, pipeline in candidates.items()
    }

    ranking = sorted(results.items(), key=lambda item: item[1]["rmse"])
    print("--- Ranking (RMSE en USD, menor es mejor) ---")
    for puesto, (name, metrics) in enumerate(ranking, start=1):
        print(f"{puesto}. {name}: {metrics['rmse']:,.0f} (R²={metrics['r2']:.3f})")
    return results


if __name__ == "__main__":
    comparison_flow()
