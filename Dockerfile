# Imagen base de Python (misma versión que .python-version / pyproject.toml).
FROM python:3.11-slim

WORKDIR /app

# uv: el mismo gestor de dependencias de todo el proyecto (regla 1 de CLAUDE.md).
# curl: solo para el HEALTHCHECK de docker-compose (GET /health).
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv

# 1) Dependencias primero (capa que cambia poco): instala TODO lo declarado
# en pyproject.toml/uv.lock sin construir aún el paquete proyecto_final, para
# que un cambio de código no invalide esta capa pesada (mlflow, sklearn,
# prefect, fastapi...).
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen --no-install-project

# 2) Código del proyecto (capa que cambia seguido): ahora sí se instala el
# paquete proyecto_final en modo editable dentro del venv ya creado.
# README.md se copia porque pyproject.toml lo declara como `readme` del
# paquete: uv_build lo necesita presente para construirlo.
COPY README.md ./
COPY src/ ./src/
RUN uv sync --no-dev --frozen

# 3) Configuración y modelo: el modelo NO se entrena ni se descarga de MLflow
# dentro del contenedor. Debe existir ANTES del build (ver README):
#   uv run python -m proyecto_final.deployment.copy_model
COPY configs/ ./configs/
COPY models/champion/ ./models/champion/

EXPOSE 8000
ENV PYTHONUNBUFFERED=1

# Se llama al binario del venv directamente (no "uv run"): "uv run" revisa y
# sincroniza dependencias al arrancar, lo que en runtime intentaría descargar
# las de desarrollo (ruff, pytest) que quedaron fuera con --no-dev. El venv ya
# quedó completo en el build; el contenedor no necesita red para arrancar.
CMD [".venv/bin/uvicorn", "proyecto_final.deployment.app:app", "--host", "0.0.0.0", "--port", "8000"]
