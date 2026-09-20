"""Procesamiento y feature engineering (actividad 5 del checklist).

Implementa las conclusiones del EDA (docs/decisiones.md, 2026-09-18):
- Excluir `salary` y `salary_currency` (leakage: son el target disfrazado).
- NO eliminar duplicados exactos ni atípicos altos (son registros legítimos).
- Partición temporal: train work_year<=2024, validación work_year=2025.
- Agrupar categorías poco frecuentes de job_title y columnas de país, aprendiendo
  las categorías frecuentes SOLO de train (evita leakage de validación).

Funciones puras y testeables sin Prefect: la orquestación vive en
`proyecto_final.flows.processing_flow` (regla 3 de CLAUDE.md).
"""

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


def drop_leakage_columns(df: pd.DataFrame, leakage_columns: list[str]) -> pd.DataFrame:
    """Elimina las columnas que filtran el target (salary, salary_currency)."""
    return df.drop(columns=[c for c in leakage_columns if c in df.columns])


def split_temporal(
    df: pd.DataFrame, year_column: str, validation_year: int
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Parte train (años anteriores) / validación (validation_year).

    Entrenar con el pasado y validar con el "futuro" da una medida honesta del
    desempeño en producción (mismo patrón enero/febrero del curso).
    """
    train = df[df[year_column] < validation_year].copy()
    validation = df[df[year_column] == validation_year].copy()
    return train, validation


def fit_frequent_categories(train_series: pd.Series, min_freq: float) -> list[str]:
    """Aprende de TRAIN las categorías con frecuencia relativa >= min_freq.

    Se calcula solo sobre train: si mirara validación, estaríamos usando
    información del "futuro" para decidir cómo transformar (leakage).
    """
    freqs = train_series.value_counts(normalize=True)
    return sorted(freqs[freqs >= min_freq].index.astype(str).tolist())


def apply_rare_grouping(
    series: pd.Series, frequent: list[str], other_label: str
) -> pd.Series:
    """Reemplaza por `other_label` toda categoría fuera de la lista de frecuentes.

    También cubre categorías nunca vistas en train (p. ej. un país nuevo que
    aparezca en 2025): caen en `other_label` en vez de romper el encoding.
    """
    return series.astype(str).where(series.astype(str).isin(frequent), other_label)


def build_preprocessor(
    categorical: list[str], numerical: list[str]
) -> ColumnTransformer:
    """Preprocesador sklearn reutilizable en entrenamiento y despliegue.

    - Categóricas: OneHotEncoder con handle_unknown="ignore" — una categoría no
      vista en fit no rompe la predicción en producción (queda como fila de ceros).
    - Numéricas: StandardScaler (inofensivo para árboles, necesario si se prueban
      modelos lineales con el mismo pipeline).
    El fit se hace SOLO con train, en la etapa de entrenamiento (actividad 6).
    """
    return ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), categorical),
            ("num", Pipeline([("scaler", StandardScaler())]), numerical),
        ]
    )
