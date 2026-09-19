"""Carga de la configuración central del proyecto (configs/config.yaml).

Un solo punto de lectura evita rutas y parámetros quemados en el código
(regla 6 de CLAUDE.md): los módulos de src/ y los flows de Prefect importan
get_config() en vez de leer el YAML cada uno por su cuenta.
"""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / "configs" / "config.yaml"


def get_config() -> dict:
    """Lee configs/config.yaml y lo devuelve como diccionario."""
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)
