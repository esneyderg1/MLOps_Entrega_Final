"""Comparación de familias de modelos (insumo para decidir el candidato, actividad 8).

Motivación (docs/decisiones.md, 2026-09-20): Optuna solo mejoró el RandomForest
en 0.59%, señal de que el techo puede estar en la familia de modelo y no en los
hiperparámetros. Antes de fijar el candidato comparamos, con los MISMOS datos y
la MISMA validación temporal:

- Regresión multilineal (LinearRegression) y Ridge (lineal regularizada).
- HistGradientBoostingRegressor (boosting de sklearn, sin dependencias nuevas).
- Cada familia en dos variantes de target: USD directo y log1p(USD) — la
  transformación que el EDA dejó sugerida por la cola derecha pesada. Se
  destransforma con expm1 al predecir, así el RMSE queda siempre en USD.

Funciones puras y testeables; la orquestación y el tracking viven en
`proyecto_final.flows.comparison_flow` (regla 3 de CLAUDE.md).
"""

import numpy as np
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder

from proyecto_final.features.preprocessing import build_preprocessor


def build_ordinal_preprocessor(
    categorical: list[str], numerical: list[str]
) -> ColumnTransformer:
    """Preprocesador para modelos de árboles/boosting.

    HistGradientBoosting no acepta las matrices dispersas del OneHotEncoder y a
    los árboles no les hace falta one-hot: OrdinalEncoder les basta para partir
    por categoría. `unknown_value=-1` cubre categorías no vistas en train (mismo
    espíritu del handle_unknown="ignore" del pipeline lineal).
    """
    return ColumnTransformer(
        transformers=[
            (
                "cat",
                OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1),
                categorical,
            ),
            ("num", "passthrough", numerical),
        ]
    )


def with_log_target(pipeline: Pipeline) -> TransformedTargetRegressor:
    """Envuelve un pipeline para entrenar sobre log1p(target) y predecir en USD.

    Con cola derecha pesada, el log evita que los salarios ejecutivos dominen el
    ajuste. TransformedTargetRegressor aplica log1p al entrenar y expm1 al
    predecir: las métricas siguen siendo comparables en USD sin código extra.
    """
    return TransformedTargetRegressor(
        regressor=pipeline, func=np.log1p, inverse_func=np.expm1
    )


def candidate_pipelines(
    categorical: list[str],
    numerical: list[str],
    random_state: int,
    ridge_alpha: float,
) -> dict[str, object]:
    """Los candidatos a comparar: 3 familias x 2 variantes de target (6 modelos).

    Todos son pipelines COMPLETOS (preprocesamiento incluido), igual que el
    baseline: el ganador puede pasar directo al Model Registry.
    """
    linear = Pipeline(
        [
            ("preprocessor", build_preprocessor(categorical, numerical)),
            ("model", LinearRegression()),
        ]
    )
    ridge = Pipeline(
        [
            ("preprocessor", build_preprocessor(categorical, numerical)),
            ("model", Ridge(alpha=ridge_alpha)),
        ]
    )
    hgb = Pipeline(
        [
            ("preprocessor", build_ordinal_preprocessor(categorical, numerical)),
            ("model", HistGradientBoostingRegressor(random_state=random_state)),
        ]
    )

    base = {
        "linear_regression": linear,
        "ridge": ridge,
        "hist_gradient_boosting": hgb,
    }
    log_variants = {
        f"{name}_log_target": with_log_target(pipeline)
        for name, pipeline in base.items()
    }
    return {**base, **log_variants}
