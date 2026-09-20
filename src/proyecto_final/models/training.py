"""Entrenamiento y evaluación de modelos (actividades 6 y 7 del checklist).

Funciones puras y testeables sin MLflow ni Prefect: la orquestación y el
tracking viven en los flows (regla 3 de CLAUDE.md). El preprocesador viene de
`proyecto_final.features.preprocessing.build_preprocessor` y se ajusta SOLO
con train, dentro del Pipeline (sin leakage).
"""

import numpy as np
import pandas as pd
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline

from proyecto_final.features.preprocessing import build_preprocessor


def prepare_features(
    df: pd.DataFrame, categorical: list[str], numerical: list[str], target: str
) -> tuple[pd.DataFrame, np.ndarray]:
    """Separa X (solo las features declaradas en configs/) e y (target).

    Seleccionar columnas explícitamente evita que una columna nueva del dataset
    "vivo" entre al modelo sin que nadie lo haya decidido.
    """
    x = df[categorical + numerical].copy()
    y = df[target].to_numpy()
    return x, y


def evaluate_regression(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    """Métricas de la entrega: RMSE (principal, en USD), MAE y R² de apoyo."""
    return {
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "r2": float(r2_score(y_true, y_pred)),
    }


def build_dummy_pipeline() -> Pipeline:
    """Piso absoluto: predecir siempre la mediana del train (sin features).

    Si un modelo no supera esto con claridad, las features no están aportando.
    La mediana (y no la media) porque el EDA mostró cola derecha pesada.
    """
    return Pipeline([("model", DummyRegressor(strategy="median"))])


def build_baseline_pipeline(
    categorical: list[str],
    numerical: list[str],
    n_estimators: int,
    max_depth: int,
    random_state: int,
) -> Pipeline:
    """Baseline real: preprocesador + RandomForest con parámetros simples.

    Es el pipeline COMPLETO (preprocesamiento incluido): el mismo objeto que se
    loguea en MLflow sirve para predecir sobre datos crudos en el despliegue.
    """
    return Pipeline(
        [
            ("preprocessor", build_preprocessor(categorical, numerical)),
            (
                "model",
                RandomForestRegressor(
                    n_estimators=n_estimators,
                    max_depth=max_depth,
                    random_state=random_state,
                    n_jobs=-1,
                ),
            ),
        ]
    )
