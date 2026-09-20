"""Tests de proyecto_final.models.training (actividad 6 del checklist)."""

import numpy as np
import pandas as pd

from proyecto_final.models.training import (
    build_baseline_pipeline,
    build_dummy_pipeline,
    evaluate_regression,
    prepare_features,
)


def _datos_ejemplo() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "job_title": ["DS", "DE", "DS", "DE"] * 5,
            "work_year": [2023, 2023, 2024, 2024] * 5,
            "salary_in_usd": [100_000, 120_000, 110_000, 130_000] * 5,
            "columna_extra": ["no debe entrar al modelo"] * 20,
        }
    )


def test_prepare_features_selecciona_solo_columnas_declaradas():
    x, y = prepare_features(
        _datos_ejemplo(),
        categorical=["job_title"],
        numerical=["work_year"],
        target="salary_in_usd",
    )

    assert list(x.columns) == ["job_title", "work_year"]
    assert "columna_extra" not in x.columns
    assert len(y) == 20
    assert y[0] == 100_000


def test_evaluate_regression_calcula_las_tres_metricas():
    y_true = np.array([100.0, 200.0, 300.0])
    y_pred = np.array([110.0, 190.0, 310.0])

    metrics = evaluate_regression(y_true, y_pred)

    assert set(metrics) == {"rmse", "mae", "r2"}
    assert metrics["rmse"] == 10.0  # errores de 10 en todos los puntos
    assert metrics["mae"] == 10.0
    assert 0.9 < metrics["r2"] < 1.0


def test_evaluate_regression_prediccion_perfecta():
    y = np.array([1.0, 2.0, 3.0])
    metrics = evaluate_regression(y, y)

    assert metrics["rmse"] == 0.0
    assert metrics["r2"] == 1.0


def test_dummy_pipeline_predice_la_mediana_del_train():
    df = _datos_ejemplo()
    x, y = prepare_features(df, ["job_title"], ["work_year"], "salary_in_usd")

    pipeline = build_dummy_pipeline()
    pipeline.fit(x, y)

    assert (pipeline.predict(x) == np.median(y)).all()


def test_baseline_pipeline_entrena_y_predice_sobre_datos_crudos():
    df = _datos_ejemplo()
    x, y = prepare_features(df, ["job_title"], ["work_year"], "salary_in_usd")

    pipeline = build_baseline_pipeline(
        categorical=["job_title"],
        numerical=["work_year"],
        n_estimators=5,
        max_depth=3,
        random_state=42,
    )
    pipeline.fit(x, y)
    predicciones = pipeline.predict(x)

    # El pipeline completo acepta el dataframe crudo (sin preprocesar aparte)
    # y devuelve valores en el rango del target: eso es lo que usará el deploy.
    assert len(predicciones) == len(y)
    assert predicciones.min() >= 90_000 and predicciones.max() <= 140_000
