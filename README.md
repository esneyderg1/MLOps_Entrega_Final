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

> **Estado:** dataset confirmado:
> [The Global AI/ML/Data Science Salary for 2025](https://www.kaggle.com/datasets/samithsachidanandan/the-global-ai-ml-data-science-salary-for-2025)
> (regresión sobre `salary_in_usd`, ficha en `docs/dataset.md`). Completados: EDA
> (`notebooks/01_eda.ipynb`) y los flows de adquisición, procesamiento, baseline
> y optimización con Optuna (ver tabla de flows). Mejor RMSE: **68.142 USD** (Optuna,
> 0,59% mejor que el baseline de 68.547 — por debajo del ~10% esperado, limitación
> documentada en `docs/decisiones.md`). Siguiente: modelo candidato y Model Registry.
> Modalidad de despliegue por definir (`docs/decisiones.md`).

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

## Flows de Prefect

Cada flow corre de punta a punta con un solo comando (regla 3 de `CLAUDE.md`).
El código es **agnóstico al servidor de Prefect**: la conexión sale del perfil
local de cada máquina, nunca del repo.

- **Prefect Cloud** (así trabaja el equipo): inicia sesión una vez con
  `uv run prefect cloud login` y cada ejecución imprime la URL del run en el
  dashboard compartido.
- **Local** (sin cuenta, por ejemplo para el peer review): no hay que configurar
  nada — el flow levanta un servidor efímero automáticamente. Para una UI local
  persistente: `uv run prefect server start` → http://127.0.0.1:4200.

En ambos casos el comando del flow es exactamente el mismo. Las credenciales de
Prefect Cloud son personales y **nunca se commitean**.

| Flow | Comando | Qué hace | Entrada | Salida |
|---|---|---|---|---|
| Adquisición de datos | `uv run python -m proyecto_final.flows.acquisition_flow` | Descarga el dataset desde Kaggle (sin caché: siempre trae la versión más reciente) y reintenta hasta 3 veces si falla la red | `configs/config.yaml` (`dataset.source_url`) | `data/raw/salaries.csv`, `data/raw/metadata.json` (filas, columnas, sha256) |
| Procesamiento | `uv run python -m proyecto_final.flows.processing_flow` | Excluye columnas de leakage, parte train (≤2024) / validación (2025) y agrupa categorías raras (aprendidas solo de train) | `data/raw/salaries.csv`, `configs/config.yaml` (`features`) | `data/processed/train.parquet`, `validation.parquet`, `metadata.json` |
| Baseline | `uv run python -m proyecto_final.flows.baseline_flow` | Entrena y trackea en MLflow el piso a superar: `dummy_median` (mediana) y `rf_baseline` (RandomForest simple), con el pipeline completo logueado. Requiere el MLflow server corriendo | `data/processed/`, `configs/config.yaml` (`training.baseline`) | 2 runs en el experimento `salarios-ai-ml` (RMSE baseline: 68.547 USD) |
| Optimización (Optuna) | `uv run python -m proyecto_final.flows.optimization_flow` | Estudio de Optuna sobre el RandomForest (15 trials, espacio en `configs/config.yaml`): 1 parent run + 15 child runs `nested=True` en MLflow, cada uno con su pipeline completo logueado. Requiere el MLflow server corriendo | `data/processed/`, `configs/config.yaml` (`training.optuna`) | Parent run `rf-optuna-salarios` + 15 child runs; artifact `top_trials.json` (mejor RMSE: 68.142 USD) |

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

**¿Nuevo en el proyecto o retomando?** Empieza por la
[**guía de estudio**](docs/guia_estudio.md): estado actual, cómo funciona el
pipeline de punta a punta, qué archivos leer en qué orden y las preguntas de
sustentación que todos debemos poder responder.

El avance del proyecto se lleva en el **Plan de trabajo (checklist)** al final de
`CLAUDE.md`: una tarea solo se marca cuando está terminada, verificada y
funcionando. Estado actual: **7/11 completadas** (scaffolding, selección del
dataset, EDA, adquisición, procesamiento/feature engineering, baseline con
tracking en MLflow y optimización con Optuna); la siguiente es **modelo
candidato y Model Registry**.
