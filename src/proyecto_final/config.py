"""Carga de la configuración central del proyecto (configs/config.yaml).

Un solo punto de lectura evita rutas y parámetros quemados en el código
(regla 6 de CLAUDE.md): los módulos de src/ y los flows de Prefect importan
get_config() en vez de leer el YAML cada uno por su cuenta.
"""

import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / "configs" / "config.yaml"


def get_config() -> dict:
    """Lee configs/config.yaml y lo devuelve como diccionario."""
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def enable_utf8_output() -> None:
    """Evita UnicodeEncodeError en consolas Windows (cp1252).

    MLflow imprime emojis (p. ej. "🏃 View run ...") al cerrar cada run; en
    Windows la consola por defecto no puede codificarlos y el print revienta el
    task de Prefect. Llamar esta función al inicio de cada flow que use MLflow.
    """
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
