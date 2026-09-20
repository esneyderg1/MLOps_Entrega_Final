"""Tests de proyecto_final.models.comparison (comparación de familias, actividad 8)."""

import numpy as np
import pandas as pd

from proyecto_final.models.comparison import (
    build_ordinal_preprocessor,
    candidate_pipelines,
    with_log_target,
)


def _datos_ejemplo() -> tuple[pd.DataFrame, np.ndarray]:
    x = pd.DataFrame(
        {
            "job_title": ["DS", "DE", "DS", "DE"] * 10,
            "work_year": [2023, 2023, 2024, 2024] * 10,
        }
    )
    y = np.array([100_000.0, 120_000.0, 110_000.0, 130_000.0] * 10)
    return x, y


def test_candidate_pipelines_devuelve_3_familias_x_2_targets():
    candidates = candidate_pipelines(
        categorical=["job_title"],
        numerical=["work_year"],
        random_state=42,
        ridge_alpha=1.0,
    )

    assert len(candidates) == 6
    assert {
        "linear_regression",
        "ridge",
        "hist_gradient_boosting",
        "linear_regression_log_target",
        "ridge_log_target",
        "hist_gradient_boosting_log_target",
    } == set(candidates)


def test_todos_los_candidatos_entrenan_y_predicen_en_usd():
    x, y = _datos_ejemplo()
    candidates = candidate_pipelines(
        categorical=["job_title"],
        numerical=["work_year"],
        random_state=42,
        ridge_alpha=1.0,
    )

    for name, pipeline in candidates.items():
        pipeline.fit(x, y)
        pred = pipeline.predict(x)
        # Aunque la variante log entrene sobre log1p(y), la predicción debe
        # volver a la escala original (USD): ese es el punto de expm1.
        assert pred.min() > 50_000, f"{name} predice fuera de escala USD"
        assert pred.max() < 200_000, f"{name} predice fuera de escala USD"


def test_with_log_target_destransforma_a_la_escala_original():
    x, y = _datos_ejemplo()
    candidates = candidate_pipelines(
        categorical=["job_title"],
        numerical=["work_year"],
        random_state=42,
        ridge_alpha=1.0,
    )

    modelo_log = with_log_target(candidates["linear_regression"])
    modelo_log.fit(x, y)

    # Si no destransformara, las predicciones serían ~log1p(110000) ≈ 11.6.
    assert modelo_log.predict(x).mean() > 50_000


def test_ordinal_preprocessor_tolera_categorias_no_vistas():
    preprocessor = build_ordinal_preprocessor(
        categorical=["job_title"], numerical=["work_year"]
    )
    x, _ = _datos_ejemplo()
    preprocessor.fit(x)

    nuevo = pd.DataFrame({"job_title": ["ROL_NUNCA_VISTO"], "work_year": [2025]})
    transformado = preprocessor.transform(nuevo)

    assert transformado[0][0] == -1  # unknown_value, no lanza error
