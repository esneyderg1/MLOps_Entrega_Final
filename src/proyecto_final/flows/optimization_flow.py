"""Flow de Prefect para la optimización de hiperparámetros con Optuna (actividad 7).

Corre un estudio de Optuna sobre el RandomForest del baseline: un parent run en
MLflow por estudio, y cada trial como child run (`nested=True`, regla 2 de
CLAUDE.md). Al terminar, loguea en el parent los mejores params y un resumen de
los mejores trials (con su `mlflow_run_id`, para recuperar ese modelo exacto en
la actividad 8 sin tener que reentrenar).

Requiere el MLflow Tracking Server corriendo y data/processed/ generado
(processing_flow). Ejecutar de punta a punta con:
    uv run python -m proyecto_final.flows.optimization_flow
"""

import json
import tempfile
from pathlib import Path

import mlflow
import optuna
import pandas as pd
from prefect import flow, task

from proyecto_final.config import REPO_ROOT, enable_utf8_output, get_config
from proyecto_final.models.optimization import suggest_rf_params, summarize_top_trials
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


def _build_objective(train: pd.DataFrame, validation: pd.DataFrame, config: dict):
    """Cierra sobre datos/config para exponer `objective(trial)` a Optuna.

    Vive en el flow (no en models/optimization.py) porque cada trial abre su
    propio child run de MLflow: acoplar Optuna con el ciclo de vida de un run
    es justamente la orquestación que la regla 3 pide dejar en flows/.
    """
    features = config["features"]
    target = config["dataset"]["target_column"]
    x_train, y_train = prepare_features(
        train, features["categorical"], features["numerical"], target
    )
    x_val, y_val = prepare_features(
        validation, features["categorical"], features["numerical"], target
    )
    search_space = config["training"]["optuna"]["search_space"]
    random_state = config["training"]["random_state"]

    def objective(trial: optuna.trial.Trial) -> float:
        params = suggest_rf_params(trial, search_space)
        pipeline = build_rf_pipeline(
            features["categorical"], features["numerical"], random_state, **params
        )

        with mlflow.start_run(nested=True, run_name=f"trial-{trial.number}") as run:
            mlflow.set_tags({"stage": "optuna-trial", "trial_number": trial.number})
            mlflow.log_params(params)

            pipeline.fit(x_train, y_train)
            metrics = evaluate_regression(y_val, pipeline.predict(x_val))
            mlflow.log_metrics(metrics)

            # Mismo pipeline completo que el baseline: cualquier trial puede
            # terminar siendo el modelo candidato de la actividad 8.
            mlflow.sklearn.log_model(
                pipeline, name="model", skops_trusted_types=SKOPS_TRUSTED_TYPES
            )
            # Sin esto no hay forma de volver del resumen de trials (solo params
            # y métricas) al modelo real logueado en MLflow.
            trial.set_user_attr("mlflow_run_id", run.info.run_id)

        print(
            f"trial {trial.number}: RMSE={metrics['rmse']:,.0f} USD | params={params}"
        )
        return metrics["rmse"]

    return objective


@task(log_prints=True)
def run_study_task(
    train: pd.DataFrame, validation: pd.DataFrame, config: dict
) -> optuna.Study:
    """Corre el estudio; cada trial abre y cierra su propio child run de MLflow."""
    optuna_cfg = config["training"]["optuna"]
    optuna.logging.set_verbosity(
        optuna.logging.WARNING
    )  # el log de cada trial ya sale por print()

    study = optuna.create_study(
        direction="minimize", study_name=optuna_cfg["study_name"]
    )
    study.optimize(
        _build_objective(train, validation, config),
        n_trials=config["training"]["n_trials"],
    )

    print(
        f"Mejor RMSE: {study.best_value:,.0f} USD | mejores params: {study.best_params}"
    )
    return study


@task(log_prints=True)
def log_study_summary_task(study: optuna.Study, config: dict) -> list[dict]:
    """Loguea en el parent run (activo) los mejores params y el resumen de top trials."""
    n_top = config["training"]["optuna"]["n_top_trials"]
    top_trials = summarize_top_trials(study, n_top)

    mlflow.log_params(
        {f"best_{name}": value for name, value in study.best_params.items()}
    )
    mlflow.log_metric("best_rmse", study.best_value)

    with tempfile.TemporaryDirectory() as tmp_dir:
        summary_path = Path(tmp_dir) / "top_trials.json"
        summary_path.write_text(
            json.dumps(top_trials, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        mlflow.log_artifact(str(summary_path))

    print(
        f"Top {n_top} trials logueados como artifact (top_trials.json) en el parent run"
    )
    return top_trials


@flow(name="optimizacion-hiperparametros-salarios", log_prints=True)
def optimization_flow() -> dict:
    """Orquesta el estudio de Optuna: parent run en MLflow + un child run por trial."""
    enable_utf8_output()  # los emojis de MLflow rompen la consola cp1252 de Windows
    config = get_config()

    mlflow.set_tracking_uri(config["mlflow"]["tracking_uri"])
    mlflow.set_experiment(config["mlflow"]["experiment_name"])

    processed_dir = REPO_ROOT / config["paths"]["processed"]
    train, validation = load_processed_task(processed_dir, config)

    optuna_cfg = config["training"]["optuna"]
    with mlflow.start_run(run_name=optuna_cfg["study_name"]) as parent_run:
        mlflow.set_tags(
            {"stage": "optuna-parent", "dataset": config["dataset"]["name"]}
        )
        study = run_study_task(train, validation, config)
        top_trials = log_study_summary_task(study, config)

    print(f"Parent run: {parent_run.info.run_id}")
    return {
        "parent_run_id": parent_run.info.run_id,
        "best_params": study.best_params,
        "best_rmse": study.best_value,
        "top_trials": top_trials,
    }


if __name__ == "__main__":
    optimization_flow()
