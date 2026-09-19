"""Flow de Prefect para la adquisición automatizada del dataset (actividad 4).

Ejecutar de punta a punta con:
    uv run python -m proyecto_final.flows.acquisition_flow
"""

from pathlib import Path

from prefect import flow, task

from proyecto_final.config import REPO_ROOT, get_config
from proyecto_final.data.acquisition import (
    compute_dataset_metadata,
    download_raw_dataset,
    save_metadata,
)


@task(retries=3, retry_delay_seconds=10, log_prints=True)
def download_task(url: str, destination: Path, csv_name_in_zip: str) -> Path:
    """Descarga el dataset crudo; reintenta ante fallas de red (regla 3 de CLAUDE.md)."""
    path = download_raw_dataset(url, destination, csv_name_in_zip)
    print(f"Dataset descargado en {path}")
    return path


@task(log_prints=True)
def metadata_task(csv_path: Path, metadata_path: Path) -> dict:
    """Calcula y guarda el metadata.json (filas, columnas, sha256) del dataset crudo."""
    metadata = compute_dataset_metadata(csv_path)
    save_metadata(metadata, metadata_path)
    print(
        f"metadata.json guardado en {metadata_path} (sha256={metadata['sha256'][:12]}...)"
    )
    return metadata


@flow(name="adquisicion-datos-salarios", log_prints=True)
def acquisition_flow() -> dict:
    """Orquesta la adquisición completa: descarga del dataset crudo + metadata.json."""
    config = get_config()
    dataset_cfg = config["dataset"]
    raw_dir = REPO_ROOT / config["paths"]["raw"]
    raw_path = raw_dir / dataset_cfg["raw_filename"]
    metadata_path = raw_dir / "metadata.json"

    download_task(dataset_cfg["source_url"], raw_path, dataset_cfg["raw_filename"])
    return metadata_task(raw_path, metadata_path)


if __name__ == "__main__":
    acquisition_flow()
