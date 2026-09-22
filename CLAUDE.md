# CLAUDE.md — Reglas del proyecto

Este archivo define las reglas que **toda instancia de Claude (y todo integrante del equipo)** debe seguir al trabajar en este repositorio. Si una instrucción puntual de un chat contradice estas reglas, preguntar antes de actuar.

## Contexto del proyecto

Proyecto final de la materia **MLOps / Aprendizaje en la nube** (Universidad de Medellín). El objetivo es orquestar con **Prefect** el ciclo de vida completo de un modelo de ML (adquisición de datos → procesamiento → feature engineering → entrenamiento y optimización → registro y versionado en **MLflow**), y desplegar un modelo candidato. Las instrucciones completas de la entrega están en `Instrucciones.txt`.

**Alcance:** hasta el despliegue. **NO incluye monitoreo** (fuera del alcance de la entrega).

**Estado actual:** scaffolding listo y entorno funcionando. Dataset **confirmado**: *The Global AI/ML/Data Science Salary for 2025* (Kaggle) — regresión sobre `salary_in_usd`, ficha completa en `docs/dataset.md` y parámetros en `configs/config.yaml`. Aval del equipo y de la profesora obtenido (fuente Kaggle + unicidad verificada). **EDA completado** (`notebooks/01_eda.ipynb`): sin nulos, duplicados y atípicos altos legítimos (se conservan), partición temporal train≤2024/validación 2025 confirmada. **Adquisición de datos automatizada completada**: flow de Prefect en `proyecto_final.flows.acquisition_flow` descarga el dataset y genera `metadata.json` de punta a punta. **Procesamiento y feature engineering completado**: `proyecto_final.flows.processing_flow` genera `data/processed/` (train ≤2024 / validación 2025, sin leakage, categorías raras agrupadas) y `proyecto_final.features.preprocessing.build_preprocessor` queda listo para la etapa de entrenamiento. El equipo trabaja los flows en **Prefect Cloud** con código agnóstico al servidor (regla 3). **Baseline completado**: `proyecto_final.flows.baseline_flow` trackea `dummy_median` y `rf_baseline` en el experimento `salarios-ai-ml` (RMSE a superar: 68.547 USD). **Optimización con Optuna completada**: `proyecto_final.flows.optimization_flow` corrió 15 trials (parent + child runs `nested=True`); mejor RMSE 68.142 USD, solo 0.59% de mejora sobre el baseline (muy por debajo del ~10% esperado — limitación real documentada en `docs/decisiones.md`, no de los hiperparámetros sino de las features disponibles). **Modelo candidato registrado**: `proyecto_final.flows.registry_flow` registró el mejor RF de Optuna como `salarios-ai-ml-model` v1 con alias `champion` (signature + input_example). **Orquestación end-to-end completada**: `proyecto_final.flows.pipeline_flow` encadena adquisición → procesamiento → baseline → registro como subflows de Prefect y corre todo el ciclo con un solo comando (verificado desde `data/` vacío: 2m 39s, RMSE 68.547 baseline / 68.142 champion). Siguiente paso: definir la modalidad de despliegue (actividad 10). La forma de despliegue AÚN NO está definida (batch, web service con API, o Docker): no implementar nada de deployment hasta que el equipo lo decida y se actualice este archivo.

## Regla 1 — Gestión de entorno y dependencias: SOLO con uv

- Todo se gestiona con [uv](https://docs.astral.sh/uv/). **Nunca** usar `pip install`, `conda`, `poetry` ni editar el entorno a mano.
- Agregar dependencias: `uv add <paquete>` (o `uv add --dev <paquete>` para herramientas de desarrollo).
- Ejecutar cualquier cosa: `uv run <comando>` (scripts, mlflow, prefect, pytest, jupyter).
- Python **3.11** (misma versión del curso, fijada en `.python-version`).
- `pyproject.toml` y `uv.lock` siempre van versionados en git; `.venv/` nunca.
- El único entorno válido para notebooks y scripts es el `.venv` de este proyecto. El kernel de Jupyter se llama **`proyecto-final (3.11)`** y se registra con: `uv run python -m ipykernel install --user --name proyecto-final --display-name "proyecto-final (3.11)"`. No usar kernels de otros proyectos (ni el del repo del curso) y dejar la metadata de los notebooks apuntando a ese kernel.

## Regla 2 — Experiment tracking y modelos: SOLO con MLflow

- Todo entrenamiento se loguea en MLflow: parámetros, métricas, tags y artifacts. Ningún experimento "suelto" sin tracking.
- Tracking server local con SQLite como backend (necesario para el Model Registry):
  ```
  uv run mlflow server --host 127.0.0.1 --port 5000 --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./mlruns --allowed-hosts "localhost,127.0.0.1,127.0.0.1:5000"
  ```
- La URI de tracking y los nombres de experimentos se leen de `configs/`, no se escriben quemados en el código.
- Optimización de hiperparámetros con **Optuna**: un parent run por estudio y cada trial como child run (`nested=True`).
- El mejor modelo se registra en el **Model Registry** y se promueve con **aliases** (`champion`, `candidate`). **No usar stages** (`Staging`/`Production`): están deprecados.
- Registrar siempre el **pipeline completo** (preprocesamiento + modelo) con `signature` e `input_example`.
- `mlflow.db` y `mlruns/` no se versionan en git.

## Regla 3 — Orquestación: SOLO con Prefect

- Todo el ciclo de vida (adquisición, procesamiento, features, entrenamiento, registro) se implementa como **flows y tasks de Prefect** en `src/proyecto_final/flows/`.
- Los notebooks son SOLO para exploración (EDA, análisis puntuales). Nada que haga parte del pipeline puede vivir únicamente en un notebook: la lógica va en módulos de `src/` y los flows la orquestan.
- Cada flow debe poder ejecutarse con un solo comando: `uv run python -m proyecto_final.flows.<nombre>`.
- Tasks pequeñas, con una responsabilidad clara, con reintentos donde haya I/O (descargas, red).
- **El código es agnóstico al servidor de Prefect.** El equipo trabaja en Prefect Cloud, pero los flows NUNCA referencian URLs, workspaces ni API keys de Prefect (ni en código, ni en `configs/`, ni commiteadas en ningún archivo): la conexión sale del perfil local de cada máquina. Quien no tenga sesión de Cloud corre exactamente el mismo código en modo local/efímero sin configurar nada — esto garantiza que el peer review pueda ejecutarlo.

## Regla 4 — Git y commits

- **NUNCA agregar a Claude como colaborador ni coautor de los commits.** Prohibido incluir trailers como `Co-Authored-By: Claude ...` o `Generated with Claude Code` en mensajes de commit, descripciones de PR o cualquier metadata de git. Los commits van únicamente a nombre de los integrantes del equipo.
- Usar **conventional commits** (https://www.conventionalcommits.org/): `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`. Mensajes en español, descriptivos y en minúscula tras el prefijo.
- Cada integrante del equipo debe tener al menos un commit (requisito de la nota). Claude no hace commits por su cuenta: prepara los cambios y el integrante de turno commitea, salvo que se le pida explícitamente commitear.
- Nunca commitear datos (`data/`), artefactos de MLflow (`mlflow.db`, `mlruns/`), modelos serializados (`models/*.pkl` y similares) ni secretos (`.env`).

## Regla 5 — Estructura del repositorio

```
MLOps_Entrega_Final/
├── CLAUDE.md              # este archivo: reglas del proyecto
├── README.md              # documentación principal de la entrega
├── Instrucciones.txt      # enunciado de la entrega (no modificar)
├── pyproject.toml         # dependencias (gestionado con uv)
├── configs/               # configuración (dataset, mlflow, parámetros) en YAML
├── data/                  # datos locales (NO se versionan; carpetas raw/ y processed/)
├── models/                # artefactos locales de modelos (NO se versionan)
├── notebooks/             # solo EDA y exploración
├── src/proyecto_final/    # código fuente (paquete Python)
│   ├── data/              #   adquisición y validación de datos
│   ├── features/          #   procesamiento y feature engineering
│   ├── models/            #   entrenamiento, optimización, evaluación, registro
│   ├── flows/             #   flows de Prefect que orquestan todo
│   └── deployment/        #   despliegue (vacío hasta definir la modalidad)
├── tests/unit/            # tests con pytest
└── docs/                  # decisiones técnicas y guías
```

- El código nuevo va en el módulo que corresponda; no crear carpetas nuevas en la raíz sin acordarlo con el equipo.
- Toda decisión técnica relevante (dataset elegido, modalidad de deploy, modelo candidato) se documenta en `docs/decisiones.md` y se refleja aquí en la sección "Estado actual".

## Regla 6 — Calidad de código

- Lint y formato con **ruff** (`uv run ruff check .` y `uv run ruff format .`) antes de cada commit.
- Tests unitarios con **pytest** en `tests/unit/` (`uv run pytest`). Toda función de transformación de datos debe tener al menos un test.
- Código y docstrings en **español**, nombres de variables/funciones en inglés (convención del curso).
- Comentarios que expliquen el *por qué* de las decisiones, no el *qué* hace la línea.
- Sin valores quemados: rutas, URLs, nombres de experimentos y parámetros van en `configs/`.

## Regla 7 — Datos

- Los datos crudos se descargan de forma **automatizada y reproducible** (task de Prefect), nunca se agregan a mano al repo.
- `data/raw/` = datos tal cual llegan de la fuente (inmutables). `data/processed/` = datos transformados listos para entrenar.
- Cada dataset procesado genera un `metadata.json` con filas, columnas y hash sha256 (versionado simple del dataset).

## Plan de trabajo (checklist del proyecto)

**Regla de oro:** una tarea se marca `[x]` ÚNICA Y EXCLUSIVAMENTE cuando está
**terminada, verificada y funcionando** (se ejecutó de punta a punta sin errores y
se comprobó el resultado). "Casi lista", "falta probar" o "compila" = sigue en `[ ]`.
Quien marque una tarea anota la fecha y qué verificación se hizo. Cada tarea
terminada se documenta (README, `docs/decisiones.md` o docstrings según aplique)
antes de marcarse. Al completar una actividad, actualizar también
`docs/guia_estudio.md` (estado, mapa del pipeline, ruta de lectura y preguntas
de sustentación): es el documento con el que el equipo se pone al día.

### 1. Construcción del repo y scaffolding
- [x] **(2026-09-17)** Estructura de carpetas, `CLAUDE.md` con reglas, `pyproject.toml` con uv,
  `.gitignore`, `configs/config.yaml`, README con setup, entorno `.venv` creado y
  kernel `proyecto-final (3.11)` registrado.
  *Verificado:* `uv sync` sin errores (195 paquetes), imports de mlflow/prefect/optuna/sklearn OK,
  kernel visible en `jupyter kernelspec list`.

### 2. Selección del dataset y definición del problema
- [x] **(2026-09-18)** Confirmar el dataset con la profesora (fuente Kaggle) y verificar unicidad frente a otros equipos.
  *Verificado:* aval del equipo y de la profesora obtenido para The Global AI/ML/Data Science Salary for 2025. Documentado en `docs/decisiones.md` y `docs/dataset.md`.
- [x] **(2026-09-17)** Definir el problema de negocio hipotético, la variable objetivo y la métrica de éxito.
  *Verificado:* regresión sobre `salary_in_usd`, RMSE como métrica principal con validación temporal (≤2024 / 2025), caso de negocio de benchmarking salarial. Documentado en `docs/dataset.md`.
- [x] **(2026-09-17)** Documentar la decisión y el dataset, y actualizar la configuración.
  *Verificado:* ficha con diccionario de datos y riesgos en `docs/dataset.md` (perfil real de la descarga: 88.584 filas, 0 nulos, descarga anónima probada), decisión en `docs/decisiones.md`, `configs/config.yaml` con source_url/target/leakage_columns, "Estado actual" actualizado.

### 3. Análisis exploratorio (EDA)
- [x] **(2026-09-18)** Notebook `notebooks/01_eda.ipynb` con el kernel `proyecto-final (3.11)`: distribución de la variable objetivo, faltantes, atípicos, correlaciones.
  *Verificado:* ejecutado de punta a punta con `jupyter nbconvert --execute` sobre el kernel `proyecto-final`, 0 errores en las 21 celdas de código, 3 gráficos generados, metadata del notebook apuntando al kernel correcto.
- [x] **(2026-09-18)** Conclusiones escritas del EDA: qué filtros, imputaciones y transformaciones necesita el preprocesamiento.
  *Verificado:* sección 8 del notebook y resumen en `docs/decisiones.md` (duplicados y atípicos altos se conservan, agrupación de `job_title`/ubicación por baja frecuencia, evaluar `log1p` del target con destransformación antes del RMSE; sin imputaciones por no haber nulos).
- [x] **(2026-09-18)** Definir estrategia de partición train/validación.
  *Verificado:* partición temporal confirmada en la sección 7 del notebook (train `work_year`≤2024, validación `work_year`=2025) tras comparar distribuciones de target y `experience_level` entre ambos periodos.

### 4. Adquisición de datos automatizada
- [x] **(2026-09-19)** Módulo en `src/proyecto_final/data/`: descarga reproducible del dataset a `data/raw/` (con reintentos, sin pasos manuales).
  *Verificado:* `src/proyecto_final/data/acquisition.py` con `download_raw_dataset`/`compute_dataset_metadata`/`save_metadata`, cubiertas por 3 tests en `tests/unit/test_acquisition.py` (`uv run pytest` en verde, descarga mockeada sin red real).
- [x] **(2026-09-19)** Generación de `metadata.json` (filas, columnas, sha256) para versionar el dataset.
  *Verificado:* `data/raw/metadata.json` generado por el flow (88.584 filas, 11 columnas, sha256 coincide con el verificado en el EDA); no se versiona en git (dentro de `data/`).
- [x] **(2026-09-19)** Task/flow de Prefect que ejecuta la adquisición: `uv run python -m proyecto_final.flows.<nombre>` corre de punta a punta.
  *Verificado:* `uv run python -m proyecto_final.flows.acquisition_flow` corre de punta a punta (servidor efímero de Prefect), probado dos veces simulando un clon limpio (`data/raw/` vacío salvo `.gitkeep`); reintentos de la task de descarga (`retries=3`) verificados por separado con una task de prueba que falla 2 veces y se recupera en el 3er intento.

### 5. Procesamiento y feature engineering
- [x] **(2026-09-19)** Módulo `src/proyecto_final/features/preprocessing.py`: exclusión de leakage, partición temporal ≤2024/2025, agrupación de categorías raras aprendida SOLO de train; orquestado en `proyecto_final.flows.processing_flow`.
- [x] **(2026-09-19)** Preprocesador sklearn reutilizable (`build_preprocessor`: OneHotEncoder `handle_unknown="ignore"` + StandardScaler); el fit se hará solo con train en la actividad 6.
- [x] **(2026-09-19)** 6 tests nuevos en `tests/unit/test_preprocessing.py`.
  *Verificado:* `uv run pytest` 10/10 en verde, `ruff check`/`format` limpios, flow de punta a punta OK → `data/processed/train.parquet` (72.709×9), `validation.parquet` (15.875×9) y `metadata.json` con sha256; leakage confirmado fuera y categoría `OTHER` presente.

### 6. Entrenamiento baseline con tracking
- [x] **(2026-09-19)** MLflow server local corriendo (SQLite) y experimento `salarios-ai-ml` creado.
- [x] **(2026-09-19)** Módulo `src/proyecto_final/models/training.py` + flow `proyecto_final.flows.baseline_flow`: dos runs trackeados (params, métricas, tags y pipeline completo logueado) — `dummy_median` (piso absoluto) y `rf_baseline`.
- [x] **(2026-09-19)** Métrica del baseline documentada: **RMSE 68.547 USD** (MAE 48.527, R² 0.225), 12,4% mejor que el dummy (78.233). Es el piso a superar en la actividad 7.
  *Verificado:* flow de punta a punta OK, 15/15 tests y ruff en verde, runs `FINISHED` en la UI de MLflow, y el pipeline logueado se recargó desde MLflow (`runs:/<id>/model`) y predijo sobre datos crudos de validación.

### 7. Optimización de hiperparámetros
- [x] **(2026-09-20)** Estudio de Optuna (parent run + child runs `nested=True`), espacio de búsqueda propio del equipo.
  *Verificado:* `proyecto_final.flows.optimization_flow` corrió de punta a punta (15 trials sobre el RandomForest, espacio en `configs/config.yaml`: n_estimators/max_depth/min_samples_split/min_samples_leaf/max_features); parent run `rf-optuna-salarios` con 15 child runs `nested=True`, todos `FINISHED`, verificado por API de MLflow (`tags.mlflow.parentRunId`).
- [x] **(2026-09-20)** Artifacts del estudio logueados (best params, top trials con model_id).
  *Verificado:* `best_rmse`/`best_*` params logueados en el parent run; artifact `top_trials.json` (5 mejores trials con params, rmse y `mlflow_run_id`) descargado y cruzado contra los runs reales: coincide exactamente.
- [x] **(2026-09-20)** Comparación en la UI de MLflow verificada.
  *Verificado:* estructura parent/child confirmada por la API de MLflow (`search_runs` con filtro `parentRunId`, 15/15 child runs). **Resultado del estudio:** mejor RMSE 68.142 USD, solo 0.59% mejor que el `rf_baseline` (68.547) — muy por debajo del ~10% esperado en `docs/dataset.md`; documentado como limitación real en `docs/decisiones.md` (no se fuerza el número ampliando el espacio de búsqueda sin sustento).

### 8. Modelo candidato y Model Registry
- [x] **(2026-09-20)** Candidato decidido con evidencia: el mejor RF de Optuna (RMSE 68.142 USD). Justificación en `docs/decisiones.md`: ninguna de las 6 alternativas de la comparación de familias lo superó; hiperparámetros fijados en `configs/config.yaml` (`training.candidate`).
- [x] **(2026-09-20)** Pipeline completo registrado vía `proyecto_final.flows.registry_flow`: `salarios-ai-ml-model` v1, con signature e input_example (muestra de datos crudos de validación).
- [x] **(2026-09-20)** Alias `champion` asignado y verificado.
  *Verificado:* flow de punta a punta OK — el reentrenamiento reprodujo el RMSE exacto (68.142), y `models:/salarios-ai-ml-model@champion` cargó y predijo sobre 5 filas crudas de validación. 22/22 tests y ruff en verde.

### 9. Orquestación end-to-end
- [x] **(2026-09-21)** Flow maestro `proyecto_final.flows.pipeline_flow`: encadena adquisición → procesamiento → baseline → registro reutilizando los flows existentes como subflows de Prefect. La optimización con Optuna es opcional (`--con-optimizacion`).
- [x] **(2026-09-21)** Ejecución de punta a punta con un solo comando, verificada tras vaciar `data/raw/` y `data/processed/`: regeneró los 88.584 registros crudos y terminó con el champion registrado en 2m 39s.
- [x] **(2026-09-21)** Runs visibles en la UI de Prefect: el flow run `pipeline-completo-salarios` muestra `check_mlflow_task` + los 4 subflow runs anidados, todos `Completed`.
  *Verificado:* 25/25 tests y ruff en verde; `rf_baseline` RMSE 68.547 y champion `salarios-ai-ml-model` v1 RMSE 68.142 (números exactos reproducidos) en la misma corrida.

### 10. Despliegue del modelo candidato
- [ ] Decidir modalidad: batch / web service (FastAPI) / Docker. Documentar en `docs/decisiones.md` y actualizar "Estado actual".
- [ ] Implementar el despliegue en `src/proyecto_final/deployment/` consumiendo el modelo por alias desde el Registry.
- [ ] Predicción de prueba end-to-end verificada (el alcance llega hasta aquí: SIN monitoreo).

### 11. Calidad y documentación final
- [ ] `uv run ruff check .` y `uv run pytest` en verde sobre todo el repo.
- [ ] README final: descripción del problema, instrucciones de ejecución paso a paso (pensado para el peer review), arquitectura del pipeline.
- [ ] Verificar que cada integrante tiene al menos un commit (requisito de nota).
- [ ] Preparar la presentación del proyecto.
