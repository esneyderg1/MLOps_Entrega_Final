"""Flow de Prefect para el procesamiento y feature engineering (actividad 5).

Lee el dataset crudo de data/raw/ (generado por acquisition_flow), aplica las
transformaciones concluidas en el EDA y deja en data/processed/ los datasets de
train y validación listos para entrenar, junto con su metadata.json.

Ejecutar de punta a punta con:
    uv run python -m proyecto_final.flows.processing_flow
"""

import hashlib
import json
from pathlib import Path

import pandas as pd
from prefect import flow, task

from proyecto_final.config import REPO_ROOT, get_config
from proyecto_final.features.preprocessing import (
    apply_rare_grouping,
    drop_leakage_columns,
    fit_frequent_categories,
    split_temporal,
)


@task(log_prints=True)
def load_raw_task(raw_path: Path) -> pd.DataFrame:
    """Carga el csv crudo; falla claro si no se ha corrido el acquisition_flow."""
    if not raw_path.exists():
        raise FileNotFoundError(
            f"No existe {raw_path}. Ejecuta primero: "
            "uv run python -m proyecto_final.flows.acquisition_flow"
        )
    df = pd.read_csv(raw_path)
    print(f"Dataset crudo cargado: {df.shape[0]} filas, {df.shape[1]} columnas")
    return df


@task(log_prints=True)
def transform_task(df: pd.DataFrame, config: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Aplica leakage-drop, partición temporal y agrupación de categorías raras."""
    df = drop_leakage_columns(df, config["dataset"]["leakage_columns"])

    train, validation = split_temporal(
        df,
        year_column="work_year",
        validation_year=config["training"]["validation_year"],
    )

    grouping = config["features"]["rare_grouping"]
    for column in grouping["columns"]:
        # Las categorías frecuentes se aprenden SOLO de train (sin leakage);
        # lo no visto o raro cae en other_label en ambos conjuntos.
        frequent = fit_frequent_categories(train[column], grouping["min_freq"])
        train[column] = apply_rare_grouping(
            train[column], frequent, grouping["other_label"]
        )
        validation[column] = apply_rare_grouping(
            validation[column], frequent, grouping["other_label"]
        )
        print(f"{column}: {len(frequent)} categorías frecuentes conservadas")

    print(f"Train: {train.shape} | Validación: {validation.shape}")
    return train, validation


@task(log_prints=True)
def save_processed_task(
    train: pd.DataFrame, validation: pd.DataFrame, processed_dir: Path, config: dict
) -> dict:
    """Guarda los parquet procesados y su metadata.json (filas, columnas, sha256)."""
    processed_dir.mkdir(parents=True, exist_ok=True)
    splits = {
        config["processed"]["train_filename"]: train,
        config["processed"]["validation_filename"]: validation,
    }

    metadata = {}
    for filename, df in splits.items():
        path = processed_dir / filename
        df.to_parquet(path, index=False)
        metadata[filename] = {
            "n_rows": len(df),
            "n_columns": len(df.columns),
            "columns": list(df.columns),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }

    metadata_path = processed_dir / "metadata.json"
    metadata_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Datos procesados y metadata guardados en {processed_dir}")
    return metadata


@flow(name="procesamiento-datos-salarios", log_prints=True)
def processing_flow() -> dict:
    """Orquesta el procesamiento completo: raw -> transformaciones -> processed."""
    config = get_config()
    raw_path = REPO_ROOT / config["paths"]["raw"] / config["dataset"]["raw_filename"]
    processed_dir = REPO_ROOT / config["paths"]["processed"]

    df = load_raw_task(raw_path)
    train, validation = transform_task(df, config)
    return save_processed_task(train, validation, processed_dir, config)


if __name__ == "__main__":
    processing_flow()
