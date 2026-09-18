# MLOps_Entrega_Final

Trabajo final para la materia **Aprendizaje en la nube / MLOps** (Universidad de Medellín).

## Integrantes del equipo

- Yennifer Serna
- Carolina Uribe
- Juanita Arango
- Esneyder Gomez

## Objetivo

Orquestar con **Prefect** el ciclo de vida completo de un modelo de Machine Learning
(adquisición de datos, procesamiento, feature engineering, entrenamiento y
optimización, registro y versionado en **MLflow**) y desplegar un modelo candidato.
El enunciado completo está en `Instrucciones.txt`.

> **Estado:** scaffolding y entorno listos. Dataset seleccionado provisionalmente:
> [The Global AI/ML/Data Science Salary for 2025](https://www.kaggle.com/datasets/samithsachidanandan/the-global-ai-ml-data-science-salary-for-2025)
> (regresión sobre `salary_in_usd`) — pendiente de aval del equipo y la profesora.
> Ficha del dataset en `docs/dataset.md`; modalidad de despliegue por definir
> (`docs/decisiones.md`).

## Estructura del repositorio

```
├── CLAUDE.md              # reglas de trabajo del proyecto (leer primero)
├── Instrucciones.txt      # enunciado de la entrega
├── pyproject.toml         # dependencias (gestionado con uv)
├── configs/               # configuración central (YAML)
├── data/                  # datos locales (no versionados): raw/ y processed/
├── models/                # artefactos locales de modelos (no versionados)
├── notebooks/             # EDA y exploración
├── src/proyecto_final/    # código fuente
│   ├── data/              # adquisición y validación de datos
│   ├── features/          # procesamiento y feature engineering
│   ├── models/            # entrenamiento, optimización y registro
│   ├── flows/             # flows de Prefect (orquestación)
│   └── deployment/        # despliegue (pendiente de definir modalidad)
├── tests/unit/            # tests con pytest
└── docs/                  # decisiones técnicas y guías
```

## Requisitos

- Python 3.11
- [uv](https://docs.astral.sh/uv/)

## Setup

```bash
git clone git@github.com:esneyderg1/MLOps_Entrega_Final.git
cd MLOps_Entrega_Final
uv sync
```

`uv sync` crea el entorno virtual `.venv/` con Python 3.11 (lo descarga si no lo
tienes) e instala exactamente las versiones fijadas en `uv.lock` — todos en el
equipo quedamos con el mismo entorno.

## Kernel de Jupyter

Para trabajar con los notebooks, registra el entorno del proyecto como kernel
(se hace **una sola vez** por máquina, después de `uv sync`):

```bash
uv run python -m ipykernel install --user --name proyecto-final --display-name "proyecto-final (3.11)"
```

Luego selecciona el kernel **`proyecto-final (3.11)`** en VS Code o Jupyter.

> En VS Code normalmente ni siquiera hace falta: el repo incluye
> `.vscode/settings.json` apuntando al `.venv` del proyecto, y VS Code detecta
> automáticamente ese entorno al abrir la carpeta. El registro del kernel es la
> garantía para quien use Jupyter Lab u otro editor.

## Servicios locales

MLflow Tracking Server (necesario para tracking y Model Registry):

```bash
uv run mlflow server --host 127.0.0.1 --port 5000 --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./mlruns --allowed-hosts "localhost,127.0.0.1,127.0.0.1:5000"
```

UI de MLflow: http://127.0.0.1:5000

## Comandos útiles

```bash
uv run pytest                 # tests
uv run ruff check .           # lint
uv run ruff format .          # formato
```

## Convenciones del equipo

Las reglas de trabajo (uv, MLflow, Prefect, estructura, commits) están en
[`CLAUDE.md`](CLAUDE.md). Resumen de commits: **conventional commits**
(`feat:`, `fix:`, `docs:`, ...), en español, y cada integrante debe aportar
commits propios.

El avance del proyecto se lleva en el **Plan de trabajo (checklist)** al final de
`CLAUDE.md`: una tarea solo se marca cuando está terminada, verificada y
funcionando. Estado actual: **1/11 completada** (repo y scaffolding); la
siguiente es la **selección del dataset y el EDA**.
