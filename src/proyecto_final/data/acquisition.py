"""Adquisición del dataset crudo (actividad 4 del checklist).

Funciones puras y testeables sin Prefect: la orquestación (reintentos, logging)
vive en el flow de `proyecto_final.flows.acquisition_flow`, que importa estas
funciones y las envuelve como tasks (regla 3 de CLAUDE.md).
"""

import hashlib
import io
import json
import zipfile
from pathlib import Path

import pandas as pd
import requests


def download_raw_dataset(url: str, destination: Path, csv_name_in_zip: str) -> Path:
    """Descarga el zip del dataset y extrae el csv a `destination`.

    No usa caché: el dataset es "vivo" (se actualiza en Kaggle, ver
    docs/dataset.md), así que cada ejecución sobrescribe el archivo para que
    el sha256 del metadata.json siempre refleje la última descarga real.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        destination.write_bytes(zf.read(csv_name_in_zip))
    return destination


def compute_dataset_metadata(csv_path: Path) -> dict:
    """Calcula filas, columnas y sha256 del csv descargado."""
    df = pd.read_csv(csv_path)
    sha256 = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    return {
        "filename": csv_path.name,
        "n_rows": len(df),
        "n_columns": len(df.columns),
        "columns": list(df.columns),
        "sha256": sha256,
    }


def save_metadata(metadata: dict, destination: Path) -> Path:
    """Guarda el metadata.json junto al dataset crudo (no se versiona en git)."""
    destination.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return destination
