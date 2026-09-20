"""Flow de Prefect para el entrenamiento baseline con tracking en MLflow (actividad 6).

Entrena dos modelos sobre data/processed/ y los loguea como runs de MLflow:
- dummy_median: piso absoluto (predice la mediana del train).
- rf_baseline:  RandomForest simple; su RMSE es el piso a superar por Optuna (actividad 7).

Requiere el MLflow Tracking Server corriendo (comando en el README).
Ejecutar de punta a punta con:
    uv run python -m proyecto_final.flows.baseline_flow
"""

from pathlib import Path

import mlflow
import pandas as pd
from prefect import flow, task
from sklearn.pipeline import Pipeline

from proyecto_final.config import REPO_ROOT, enable_utf8_output, get_config
from proyecto_final.models.training import (
    build_baseline_pipeline,
    build_dummy_pipeline,
    evaluate_regression,
    prepare_features,
)


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
def train_and_log_task(
    run_name: str,
    pipeline: Pipeline,
    train: pd.DataFrame,
    validation: pd.DataFrame,
    config: dict,
    extra_params: dict | None = None,
) -> dict[str, float]:
    """Entrena un pipeline y loguea params, métricas y tags en un run de MLflow."""
    features = config["features"]
    target = config["dataset"]["target_column"]
    x_train, y_train = prepare_features(
        train, features["categorical"], features["numerical"], target
    )
    x_val, y_val = prepare_features(
        validation, features["categorical"], features["numerical"], target
    )

    with mlflow.start_run(run_name=run_name):
        mlflow.set_tags(
            {
                "stage": "baseline",
                "model_family": type(pipeline.named_steps["model"]).__name__,
                "dataset": config["dataset"]["name"],
                "particion": f"train<=2024 / validacion={config['training']['validation_year']}",
            }
        )
        mlflow.log_params(extra_params or {})

        pipeline.fit(x_train, y_train)
        metrics = evaluate_regression(y_val, pipeline.predict(x_val))
        mlflow.log_metrics(metrics)

        # El pipeline completo (preprocesador + modelo) como Logged Model.
        # skops (formato default de mlflow.sklearn) exige confiar explícitamente
        # los tipos internos de numpy/sklearn que usan el ColumnTransformer y el
        # RandomForest. Es seguro: el modelo lo entrenamos nosotros mismos en
        # este proceso, no viene de un archivo externo.
        mlflow.sklearn.log_model(
            pipeline,
            name="model",
            skops_trusted_types=[
                "numpy.dtype",
                "sklearn.compose._column_transformer._RemainderColsList",
                "sklearn.tree._tree.Tree",
            ],
        )

    print(
        f"{run_name}: RMSE={metrics['rmse']:,.0f} USD | MAE={metrics['mae']:,.0f} | R²={metrics['r2']:.3f}"
    )
    return metrics


@flow(name="baseline-salarios", log_prints=True)
def baseline_flow() -> dict:
    """Orquesta el baseline: carga datos procesados, entrena y trackea dummy + RF."""
    enable_utf8_output()  # los emojis de MLflow rompen la consola cp1252 de Windows
    config = get_config()

    mlflow.set_tracking_uri(config["mlflow"]["tracking_uri"])
    mlflow.set_experiment(config["mlflow"]["experiment_name"])

    processed_dir = REPO_ROOT / config["paths"]["processed"]
    train, validation = load_processed_task(processed_dir, config)

    dummy_metrics = train_and_log_task(
        "dummy_median",
        build_dummy_pipeline(),
        train,
        validation,
        config,
        extra_params={"strategy": "median"},
    )

    baseline_cfg = config["training"]["baseline"]
    rf_params = {
        "n_estimators": baseline_cfg["n_estimators"],
        "max_depth": baseline_cfg["max_depth"],
        "random_state": config["training"]["random_state"],
    }
    rf_pipeline = build_baseline_pipeline(
        config["features"]["categorical"], config["features"]["numerical"], **rf_params
    )
    rf_metrics = train_and_log_task(
        "rf_baseline", rf_pipeline, train, validation, config, extra_params=rf_params
    )

    mejora = (1 - rf_metrics["rmse"] / dummy_metrics["rmse"]) * 100
    print(f"El RF baseline mejora el RMSE del dummy en {mejora:.1f}%")
    return {"dummy": dummy_metrics, "rf_baseline": rf_metrics}


if __name__ == "__main__":
    baseline_flow()
