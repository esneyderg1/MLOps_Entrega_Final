# CLAUDE.md — Reglas del proyecto

Este archivo define las reglas que **toda instancia de Claude (y todo integrante del equipo)** debe seguir al trabajar en este repositorio. Si una instrucción puntual de un chat contradice estas reglas, preguntar antes de actuar.

## Contexto del proyecto

Proyecto final de la materia **MLOps / Aprendizaje en la nube** (Universidad de Medellín). El objetivo es orquestar con **Prefect** el ciclo de vida completo de un modelo de ML (adquisición de datos → procesamiento → feature engineering → entrenamiento y optimización → registro y versionado en **MLflow**), y desplegar un modelo candidato. Las instrucciones completas de la entrega están en `Instrucciones.txt`.

**Alcance:** hasta el despliegue. **NO incluye monitoreo** (fuera del alcance de la entrega).

**Estado actual:** scaffolding listo y entorno funcionando. Dataset seleccionado **PROVISIONALMENTE**: *The Global AI/ML/Data Science Salary for 2025* (Kaggle) — regresión sobre `salary_in_usd`, ficha completa en `docs/dataset.md` y parámetros en `configs/config.yaml`. Falta el aval del equipo y de la profesora (fuente Kaggle + unicidad); **no arrancar el EDA ni la adquisición hasta ese aval**. La forma de despliegue AÚN NO está definida (batch, web service con API, o Docker): no implementar nada de deployment hasta que el equipo lo decida y se actualice este archivo.

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
antes de marcarse.

### 1. Construcción del repo y scaffolding
- [x] **(2026-09-17)** Estructura de carpetas, `CLAUDE.md` con reglas, `pyproject.toml` con uv,
  `.gitignore`, `configs/config.yaml`, README con setup, entorno `.venv` creado y
  kernel `proyecto-final (3.11)` registrado.
  *Verificado:* `uv sync` sin errores (195 paquetes), imports de mlflow/prefect/optuna/sklearn OK,
  kernel visible en `jupyter kernelspec list`.

### 2. Selección del dataset y definición del problema
- [ ] Confirmar el dataset con la profesora (fuente Kaggle) y verificar unicidad frente a otros equipos.
  *Seleccionado provisionalmente (2026-09-17): The Global AI/ML/Data Science Salary for 2025 — este ítem se marca solo con el aval.*
- [x] **(2026-09-17)** Definir el problema de negocio hipotético, la variable objetivo y la métrica de éxito.
  *Verificado:* regresión sobre `salary_in_usd`, RMSE como métrica principal con validación temporal (≤2024 / 2025), caso de negocio de benchmarking salarial. Documentado en `docs/dataset.md`.
- [x] **(2026-09-17)** Documentar la decisión y el dataset, y actualizar la configuración.
  *Verificado:* ficha con diccionario de datos y riesgos en `docs/dataset.md` (perfil real de la descarga: 88.584 filas, 0 nulos, descarga anónima probada), decisión en `docs/decisiones.md`, `configs/config.yaml` con source_url/target/leakage_columns, "Estado actual" actualizado.

### 3. Análisis exploratorio (EDA)
- [ ] Notebook `notebooks/01_eda.ipynb` con el kernel `proyecto-final (3.11)`: distribución de la variable objetivo, faltantes, atípicos, correlaciones.
- [ ] Conclusiones escritas del EDA: qué filtros, imputaciones y transformaciones necesita el preprocesamiento.
- [ ] Definir estrategia de partición train/validación.

### 4. Adquisición de datos automatizada
- [ ] Módulo en `src/proyecto_final/data/`: descarga reproducible del dataset a `data/raw/` (con reintentos, sin pasos manuales).
- [ ] Generación de `metadata.json` (filas, columnas, sha256) para versionar el dataset.
- [ ] Task/flow de Prefect que ejecuta la adquisición: `uv run python -m proyecto_final.flows.<nombre>` corre de punta a punta.

### 5. Procesamiento y feature engineering
- [ ] Módulo en `src/proyecto_final/features/` con las transformaciones definidas en el EDA (de `data/raw/` a `data/processed/`).
- [ ] Preprocesador sklearn (ColumnTransformer/Pipeline) reutilizable en entrenamiento y despliegue.
- [ ] Tests unitarios en `tests/unit/` para cada transformación (`uv run pytest` en verde).

### 6. Entrenamiento baseline con tracking
- [ ] MLflow server local corriendo (SQLite) y experimento del proyecto creado.
- [ ] Módulo en `src/proyecto_final/models/`: baseline simple, con params, métricas y modelo logueados en MLflow.
- [ ] Métrica del baseline documentada (es el piso a superar).

### 7. Optimización de hiperparámetros
- [ ] Estudio de Optuna (parent run + child runs `nested=True`), espacio de búsqueda propio del equipo.
- [ ] Artifacts del estudio logueados (best params, top trials con model_id).
- [ ] Comparación en la UI de MLflow verificada.

### 8. Modelo candidato y Model Registry
- [ ] Decisión del modelo candidato justificada con métricas (documentar en `docs/decisiones.md`).
- [ ] Pipeline completo (preprocesamiento + modelo) registrado en el Model Registry con signature e input_example.
- [ ] Alias `champion` asignado y carga por alias verificada (`models:/<nombre>@champion` predice OK).

### 9. Orquestación end-to-end
- [ ] Flow maestro de Prefect que encadena: adquisición → procesamiento → entrenamiento → registro.
- [ ] Ejecución completa de punta a punta con un solo comando, verificada desde un clon limpio del repo.
- [ ] Runs del flow visibles en la UI de Prefect.

### 10. Despliegue del modelo candidato
- [ ] Decidir modalidad: batch / web service (FastAPI) / Docker. Documentar en `docs/decisiones.md` y actualizar "Estado actual".
- [ ] Implementar el despliegue en `src/proyecto_final/deployment/` consumiendo el modelo por alias desde el Registry.
- [ ] Predicción de prueba end-to-end verificada (el alcance llega hasta aquí: SIN monitoreo).

### 11. Calidad y documentación final
- [ ] `uv run ruff check .` y `uv run pytest` en verde sobre todo el repo.
- [ ] README final: descripción del problema, instrucciones de ejecución paso a paso (pensado para el peer review), arquitectura del pipeline.
- [ ] Verificar que cada integrante tiene al menos un commit (requisito de nota).
- [ ] Preparar la presentación del proyecto.
