"""Tests de proyecto_final.data.acquisition (actividad 4 del checklist)."""

import hashlib
import io
import json
import zipfile
from unittest.mock import Mock, patch

from proyecto_final.data.acquisition import (
    compute_dataset_metadata,
    download_raw_dataset,
    save_metadata,
)

CSV_CONTENT = b"a,b,c\n1,2,3\n4,5,6\n7,8,9\n"


def test_compute_dataset_metadata_devuelve_filas_columnas_y_hash(tmp_path):
    csv_path = tmp_path / "datos.csv"
    csv_path.write_bytes(CSV_CONTENT)

    metadata = compute_dataset_metadata(csv_path)

    assert metadata["filename"] == "datos.csv"
    assert metadata["n_rows"] == 3
    assert metadata["n_columns"] == 3
    assert metadata["columns"] == ["a", "b", "c"]
    assert metadata["sha256"] == hashlib.sha256(CSV_CONTENT).hexdigest()


def test_save_metadata_escribe_json_legible(tmp_path):
    metadata = {"filename": "datos.csv", "n_rows": 3, "sha256": "abc123"}
    destino = tmp_path / "metadata.json"

    save_metadata(metadata, destino)

    assert json.loads(destino.read_text(encoding="utf-8")) == metadata


def test_download_raw_dataset_extrae_csv_del_zip_descargado(tmp_path):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr("datos.csv", CSV_CONTENT)

    fake_response = Mock(content=zip_buffer.getvalue())
    fake_response.raise_for_status = Mock()
    destino = tmp_path / "raw" / "datos.csv"

    with patch(
        "proyecto_final.data.acquisition.requests.get", return_value=fake_response
    ) as mock_get:
        resultado = download_raw_dataset(
            "http://fuente.falsa/dataset.zip", destino, "datos.csv"
        )

    mock_get.assert_called_once_with("http://fuente.falsa/dataset.zip", timeout=60)
    assert resultado == destino
    assert destino.read_bytes() == CSV_CONTENT
