"""Tests de proyecto_final.features.preprocessing (actividad 5 del checklist)."""

import pandas as pd

from proyecto_final.features.preprocessing import (
    apply_rare_grouping,
    build_preprocessor,
    drop_leakage_columns,
    fit_frequent_categories,
    split_temporal,
)


def _df_ejemplo() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "work_year": [2023, 2024, 2024, 2025, 2025],
            "job_title": ["DS", "DS", "DE", "DS", "Quantum Analyst"],
            "salary": [100, 200, 300, 400, 500],
            "salary_currency": ["USD"] * 5,
            "salary_in_usd": [100, 200, 300, 400, 500],
        }
    )


def test_drop_leakage_columns_elimina_solo_las_de_leakage():
    df = drop_leakage_columns(_df_ejemplo(), ["salary", "salary_currency"])

    assert "salary" not in df.columns
    assert "salary_currency" not in df.columns
    assert "salary_in_usd" in df.columns  # el target se conserva


def test_drop_leakage_columns_tolera_columnas_ausentes():
    # No debe fallar si una columna de leakage ya no está en el dataframe.
    df = drop_leakage_columns(_df_ejemplo(), ["salary", "columna_inexistente"])
    assert "salary" not in df.columns


def test_split_temporal_separa_train_y_validacion_por_anio():
    train, validation = split_temporal(_df_ejemplo(), "work_year", 2025)

    assert train["work_year"].max() == 2024
    assert set(validation["work_year"]) == {2025}
    assert len(train) + len(validation) == 5


def test_fit_frequent_categories_respeta_umbral_de_frecuencia():
    # DS aparece 3/4 veces (75%), DE 1/4 (25%): con min_freq=0.5 solo queda DS.
    serie = pd.Series(["DS", "DS", "DS", "DE"])

    assert fit_frequent_categories(serie, min_freq=0.5) == ["DS"]
    assert fit_frequent_categories(serie, min_freq=0.2) == ["DE", "DS"]


def test_apply_rare_grouping_agrupa_raras_y_no_vistas():
    frequent = ["DS", "DE"]
    serie = pd.Series(["DS", "DE", "Quantum Analyst", "Otro Rol Nuevo"])

    resultado = apply_rare_grouping(serie, frequent, other_label="OTHER")

    assert resultado.tolist() == ["DS", "DE", "OTHER", "OTHER"]


def test_build_preprocessor_transforma_y_tolera_categorias_no_vistas():
    train = pd.DataFrame(
        {"job_title": ["DS", "DE", "DS"], "work_year": [2023, 2024, 2024]}
    )
    validation = pd.DataFrame({"job_title": ["ROL_NUNCA_VISTO"], "work_year": [2025]})

    preprocessor = build_preprocessor(
        categorical=["job_title"], numerical=["work_year"]
    )
    x_train = preprocessor.fit_transform(train)
    x_val = preprocessor.transform(validation)  # no debe lanzar error

    assert x_train.shape == (3, 3)  # 2 one-hot (DS, DE) + 1 numérica
    assert x_val.shape == (1, 3)
    # handle_unknown="ignore": la categoría no vista queda como ceros en el one-hot.
    assert x_val[0][:2].tolist() == [0.0, 0.0]
