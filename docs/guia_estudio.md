# Guía de estudio del proyecto

Documento **vivo** para que cualquier integrante se ponga al día rápido: dónde
vamos, cómo funciona lo construido, qué archivos leer y en qué orden. Se
actualiza cada vez que se completa una actividad del checklist (CLAUDE.md).

> **Última actualización:** 2026-09-20 — completadas las actividades 1–8 (8/11).
> Siguiente: actividad 9 (orquestación end-to-end, flow maestro).

## 1. Dónde vamos (estado en una tabla)

| # | Actividad | Estado | Resultado clave |
|---|---|---|---|
| 1 | Repo y scaffolding | ✅ | Estructura, uv, kernel `proyecto-final (3.11)` |
| 2 | Dataset y problema | ✅ | Salarios AI/ML 2025 (Kaggle), regresión sobre `salary_in_usd` |
| 3 | EDA | ✅ | Sin nulos; partición temporal ≤2024/2025; agrupar categorías raras |
| 4 | Adquisición automatizada | ✅ | `acquisition_flow`: descarga + `metadata.json` (sha256) |
| 5 | Procesamiento / features | ✅ | `processing_flow`: sin leakage, train/validación, `OTHER` |
| 6 | Baseline con MLflow | ✅ | dummy 78.233 USD / **rf_baseline 68.547 USD** (piso a superar) |
| 7 | Optimización (Optuna) | ✅ | Mejor trial **68.142 USD** (solo 0,59% mejor — ver hallazgo abajo) |
| 8 | Candidato + Registry | ✅ | `salarios-ai-ml-model` v1 con alias `champion` (`registry_flow`); RMSE reproducido 68.142 |
| 9 | Orquestación end-to-end | ⬜ | Flow maestro que encadene todo |
| 10 | Despliegue | ⬜ | Modalidad por definir (batch / API / Docker) |
| 11 | Calidad y presentación | ⬜ | README final, commits de todos, sustentación |

## 2. Cómo funciona lo construido (el cuento de punta a punta)

Cada etapa es un **flow de Prefect** que corre con un comando y deja su salida
lista para la siguiente. Nada se hace a mano:

```
Kaggle ──► acquisition_flow ──► data/raw/salaries.csv + metadata.json (sha256)
                │
                ▼ processing_flow
   1. quita salary y salary_currency  (LEAKAGE: son el target disfrazado)
   2. parte por tiempo: train ≤2024 / validación 2025  (validación honesta)
   3. agrupa categorías raras en "OTHER"  (aprendidas SOLO de train)
                │
                ▼ data/processed/train.parquet + validation.parquet
                │
                ▼ baseline_flow ────────► MLflow: 2 runs
   dummy_median (RMSE 78.233) = piso "sin modelo" (predice la mediana)
   rf_baseline  (RMSE 68.547) = piso a superar
                │
                ▼ optimization_flow ────► MLflow: 1 parent run + 15 child runs
   Optuna prueba 15 combinaciones de hiperparámetros del mismo RandomForest
   mejor trial: RMSE 68.142
                │
                ▼ comparison_flow ──────► MLflow: 6 runs exploratorios
   lineal / ridge / gradient boosting (± log-target): nadie supera al RF
                │
                ▼ registry_flow ────────► Model Registry
   reentrena el candidato (RMSE reproducido: 68.142) y lo registra:
   salarios-ai-ml-model v1  ──  alias "champion"
   el deploy consumirá: models:/salarios-ai-ml-model@champion
```

**Qué queda trackeado en MLflow por cada entrenamiento:** parámetros, métricas
(RMSE/MAE/R²), tags (etapa, dataset) y el **pipeline completo** (preprocesador +
modelo) como Logged Model — listo para que el deploy prediga sobre datos crudos.

**Hallazgo honesto de la actividad 7:** Optuna solo mejoró el baseline en 0,59%
(muy por debajo del ~10% del criterio de éxito). No es un fracaso: indica que el
techo está en las **features** (categorías gruesas, 90% EE. UU.), no en los
hiperparámetros. Está documentado en `docs/decisiones.md`.

**Confirmación con otras familias (`comparison_flow`, 2026-09-20):** se compararon
3 familias × 2 targets con los mismos datos y validación — LinearRegression 68.752 ·
Ridge 68.752 · HistGradientBoosting 68.198 · variantes `log1p(target)` todas peores
(68.859–69.079). **Todas caen en la banda ~68–69k**: el techo es de los datos, no
del algoritmo, y el mejor RF de Optuna (68.142) sigue siendo el candidato.

### ¿"Qué precisión tiene el modelo"? (memorizar estos números)

"Precisión/accuracy" es de clasificación; esto es **regresión**. Los equivalentes,
medidos sobre validación (año 2025) con el mejor modelo (RF de Optuna, reproducido
con RMSE idéntico 68.142 — prueba de reproducibilidad del pipeline):

| Métrica | Valor | Cómo decirlo en la sustentación |
|---|---|---|
| R² | 0.234 | "El modelo explica el 23% de la variación salarial" |
| MAE | $48.224 | "El error típico es ~48 mil USD" (el dummy: ~57 mil) |
| Error relativo mediano | 26,9% | "La mitad de las predicciones erra menos del 27%" |
| Dentro de ±20% del real | 39% | |
| **Dentro de ±30% del real** | **55%** | **La frase estrella: "el 55% de las veces acertamos el salario con margen de ±30%"** |
| Dentro de ±50% del real | 77% | |

**El encuadre de negocio:** el modelo no es un tasador exacto — es un **estimador
de referencia de mercado** para publicar vacantes/preparar ofertas. La varianza
que no captura viene de factores que el dataset no tiene (empresa concreta, skills,
años exactos, negociación); por eso 4 familias de modelos distintas convergen al
mismo error. La rúbrica evalúa el pipeline y el método, no el R².

## 3. Qué leer y en qué orden (ruta de estudio)

### Nivel 0 — contexto (10 min)
| Archivo | Qué entender |
|---|---|
| `CLAUDE.md` | Las 7 reglas del proyecto y el checklist con el estado real |
| `docs/dataset.md` | El dataset, la leyenda de códigos (SE/MI/EN/EX...), riesgos |
| `docs/decisiones.md` | El "por qué" de cada decisión, con fecha |

### Nivel 1 — configuración (5 min)
| Archivo | Qué entender |
|---|---|
| `configs/config.yaml` | El "panel de control": features, leakage, umbral de `OTHER`, espacio de búsqueda de Optuna. Si entiendes cada sección, ya sabes QUÉ hace el pipeline |
| `src/proyecto_final/config.py` | `get_config()` (único punto de lectura del YAML) y el fix UTF-8 de Windows |

### Nivel 2 — la lógica (30 min, el corazón)
| Archivo | Qué entender |
|---|---|
| `features/preprocessing.py` | `split_temporal` (partir ANTES de transformar), `fit_frequent_categories` (aprender solo de train = sin leakage), `build_preprocessor` (OneHotEncoder `handle_unknown="ignore"`) |
| `models/training.py` | `prepare_features` (solo columnas declaradas), `evaluate_regression`, `build_dummy_pipeline` vs `build_rf_pipeline` (compartido por baseline y Optuna) |
| `models/optimization.py` | Cómo el YAML se vuelve sugerencias de Optuna; resumen de top trials |

### Nivel 3 — la orquestación (30 min)
| Archivo | Qué entender |
|---|---|
| `flows/processing_flow.py` | El patrón task por responsabilidad: cargar → transformar → guardar |
| `flows/baseline_flow.py` | `train_and_log_task` = EL patrón MLflow completo: start_run → tags → params → fit → métricas → log_model |
| `flows/optimization_flow.py` | Parent run que envuelve el estudio; `objective` abre un child run por trial (`nested=True`); `trial.set_user_attr("mlflow_run_id", ...)` conecta Optuna↔MLflow |

### Nivel 4 — apoyo (lectura diagonal)
| Archivo | Qué entender |
|---|---|
| `tests/unit/*.py` | Documentación ejecutable: qué garantiza cada función |
| `notebooks/01_eda.ipynb` | De dónde salieron las decisiones de preprocesamiento |

### Diccionario de funciones (qué hace cada una y por qué existe)

El patrón de diseño de TODO el proyecto: **funciones puras** en `data/`,
`features/` y `models/` (testeables sin red, sin MLflow, sin Prefect) y **tasks**
en `flows/` que solo las envuelven agregando orquestación (reintentos, logging,
runs de MLflow). Si entiendes eso, entiendes por qué cada cosa vive donde vive.

**`config.py` — configuración**
| Función | Qué hace | Por qué existe |
|---|---|---|
| `get_config()` | Lee `configs/config.yaml` y lo devuelve como dict | Único punto de lectura: nada de rutas/parámetros quemados (regla 6) |
| `enable_utf8_output()` | Reconfigura stdout/stderr a UTF-8 | Los emojis de MLflow revientan la consola cp1252 de Windows; se llama al inicio de cada flow que usa MLflow |
| `REPO_ROOT` (constante) | Ruta absoluta a la raíz del repo | Los flows funcionan sin importar desde qué carpeta se ejecuten |

**`data/acquisition.py` — adquisición (actividad 4)**
| Función | Qué hace | Por qué existe |
|---|---|---|
| `download_raw_dataset()` | Descarga el zip de Kaggle y extrae el csv a `data/raw/` | Sin caché a propósito: el dataset es "vivo" y cada descarga debe reflejarse en el hash |
| `compute_dataset_metadata()` | Calcula filas, columnas y sha256 del csv | Versionado simple del dataset: si el hash cambia, los datos cambiaron |
| `save_metadata()` | Escribe el `metadata.json` | Deja la "versión de datos" junto al archivo (no se commitea) |

**`features/preprocessing.py` — procesamiento (actividad 5)**
| Función | Qué hace | Por qué existe |
|---|---|---|
| `drop_leakage_columns()` | Elimina `salary` y `salary_currency` | Son el target disfrazado: dejarlas sería hacer trampa |
| `split_temporal()` | Parte train (≤2024) / validación (2025) | Validación honesta; se parte ANTES de cualquier transformación que aprenda de los datos |
| `fit_frequent_categories()` | Aprende de TRAIN qué categorías superan `min_freq` | Solo de train: mirar validación sería leakage |
| `apply_rare_grouping()` | Manda lo raro/no visto a `OTHER` | Un país o cargo nuevo en producción no rompe el encoding |
| `build_preprocessor()` | ColumnTransformer: OneHot (`handle_unknown="ignore"`) + StandardScaler | El MISMO objeto transforma train, validación y producción; se ajusta solo con train |

**`models/training.py` — entrenamiento (actividad 6)**
| Función | Qué hace | Por qué existe |
|---|---|---|
| `prepare_features()` | Separa X (solo columnas declaradas en config) e y | Una columna nueva del dataset vivo no entra al modelo sin decisión explícita |
| `evaluate_regression()` | RMSE + MAE + R² | Las tres métricas de la entrega, calculadas igual en todos los flows |
| `build_dummy_pipeline()` | DummyRegressor(mediana) | El piso absoluto: si un modelo no le gana, las features no aportan |
| `build_rf_pipeline()` | Preprocesador + RandomForest con `**rf_params` libres | Lo comparten baseline, Optuna y registro: un solo constructor para cualquier combinación de hiperparámetros |
| `build_baseline_pipeline()` | `build_rf_pipeline` con los params simples de config | El piso "razonable" a superar (actividad 6) |

**`models/optimization.py` — HPO (actividad 7)**
| Función | Qué hace | Por qué existe |
|---|---|---|
| `suggest_rf_params()` | Traduce el `search_space` del YAML a sugerencias de Optuna | El espacio de búsqueda vive en config, no quemado; soporta rangos y categóricos |
| `summarize_top_trials()` | Top-N trials con params, RMSE y `mlflow_run_id` | Poder volver del resumen al modelo exacto de cualquier trial |

**`models/comparison.py` — comparación de familias (insumo actividad 8)**
| Función | Qué hace | Por qué existe |
|---|---|---|
| `build_ordinal_preprocessor()` | OrdinalEncoder (+ `unknown_value=-1`) para árboles | HistGradientBoosting no acepta matrices dispersas del OneHot; a los árboles les basta el ordinal |
| `with_log_target()` | Envuelve un pipeline para entrenar en `log1p(y)` y predecir en USD | Probar la sugerencia del EDA sin duplicar código de métricas (expm1 destransforma solo) |
| `candidate_pipelines()` | Los 6 candidatos: 3 familias × 2 targets | Comparación justa: mismos datos, misma validación, pipelines completos |

**Los flows y sus tasks (orquestación)**
| Flow | Tasks | Qué orquesta |
|---|---|---|
| `acquisition_flow` | `download_task` (retries=3) → `metadata_task` | Descarga con reintentos + versión del dataset |
| `processing_flow` | `load_raw_task` → `transform_task` → `save_processed_task` | raw → (leakage, split, OTHER) → parquets + metadata |
| `baseline_flow` | `load_processed_task` → `train_and_log_task` ×2 | Entrena dummy y RF baseline; cada uno con su run de MLflow (params, métricas, tags, modelo) |
| `optimization_flow` | `load_processed_task` → `run_study_task` → `log_study_summary_task` | Parent run + 15 child runs; `_build_objective` crea el `objective(trial)` que abre un child run por trial y guarda su `mlflow_run_id` |
| `comparison_flow` | `load_processed_task` → `train_candidate_task` ×6 | Los 6 candidatos como runs exploratorios (sin artefacto de modelo) |
| `registry_flow` | `load_processed_task` → `train_candidate_task` → `register_champion_task` → `verify_champion_task` | Reentrena el candidato, lo registra con signature + input_example, asigna `champion` y verifica la carga por alias |

> Detalle común: varios flows repiten `load_processed_task` — es deliberado (cada
> flow es autocontenido y legible); si molesta, es un refactor natural durante la
> actividad 9.

## 4. Runbook: correr y VALIDAR todo, paso a paso

La mejor forma de estudiar el pipeline es ejecutarlo y verificar cada etapa. No
pases al siguiente paso si el actual no cumple su criterio de validación.

> Ojo: `mlflow.db` y `mlruns/` son locales — cada quien ve los runs de SU máquina.
> Los flows se ven en Prefect Cloud (o local, según tu perfil).

### Paso 0 — Preparación (una vez por máquina)

```bash
git pull && uv sync
uv run pytest            # ✅ criterio: 22 passed
uv run ruff check .      # ✅ criterio: All checks passed!
```

*Qué hace:* reconstruye el entorno exacto desde `uv.lock` y valida la lógica pura
(transformaciones, pipelines, métricas) sin tocar red ni servidores. Si algo
falla aquí, es problema de entorno, no del pipeline — no sigas.

### Paso 1 — MLflow server (terminal aparte, déjala corriendo)

```bash
uv run mlflow server --host 127.0.0.1 --port 5000 --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./mlruns --allowed-hosts "localhost,127.0.0.1,127.0.0.1:5000"
```

*Qué hace:* levanta el tracking server con SQLite (lo que habilita el Registry).
**✅ Criterio:** http://127.0.0.1:5000 carga la UI.

### Paso 2 — Adquisición

```bash
uv run python -m proyecto_final.flows.acquisition_flow
```

*Qué hace:* descarga el zip de Kaggle (3 reintentos), extrae `salaries.csv` a
`data/raw/` y genera `metadata.json` (filas, columnas, sha256 = versión de la descarga).
**✅ Criterio:** las 2 tasks en `Completed`; `data/raw/metadata.json` con **~88.584
filas** (puede variar: el dataset se actualiza en Kaggle — para eso está el hash).

### Paso 3 — Procesamiento

```bash
uv run python -m proyecto_final.flows.processing_flow
```

*Qué hace:* quita el leakage (`salary`, `salary_currency`), parte train ≤2024 /
validación 2025, agrupa categorías raras en `OTHER` (aprendidas solo de train).
**✅ Criterio:** logs con `Train: (72709, 9) | Validación: (15875, 9)` y las
categorías conservadas (job_title: 15, países: 3); `data/processed/metadata.json`
con los dos parquet y su sha256.

### Paso 4 — Baseline

```bash
uv run python -m proyecto_final.flows.baseline_flow
```

*Qué hace:* entrena y trackea los dos pisos (`dummy_median` y `rf_baseline`).
**✅ Criterio (números EXACTOS, semilla fija):** `dummy_median: RMSE=78,233` y
`rf_baseline: RMSE=68,547` (+ "mejora 12.4%"). En la UI de MLflow (experimento
`salarios-ai-ml`): 2 runs nuevos, cada uno con params, métricas, tags y modelo.

### Paso 5 — Optimización con Optuna (~5–10 min, el paso lento)

```bash
uv run python -m proyecto_final.flows.optimization_flow
```

*Qué hace:* 15 trials sobre el mismo RF; 1 parent run + 15 child runs anidados;
el parent guarda `best_rmse` y el artifact `top_trials.json`.
**✅ Criterio:** en MLflow, el run `rf-optuna-salarios` con 15 runs anidados
debajo (flechita para expandir). **Tu mejor RMSE será ~68.000–68.500, NO
exactamente 68.142**: el muestreador de Optuna es aleatorio (explora combinaciones
distintas cada estudio); lo reproducible es el entrenamiento DADO un set de
hiperparámetros. Eso es normal.

### Paso 6 — Comparación de familias (~1 min)

```bash
uv run python -m proyecto_final.flows.comparison_flow
```

*Qué hace:* entrena los 6 candidatos (lineal, ridge, boosting × USD/log1p) con
la misma validación.
**✅ Criterio (exactos):** ranking entre 68.198 y 69.079; 6 runs con tag
`stage=model-comparison` en MLflow; ninguno baja de 68.142.

### Paso 7 — Registro del champion

```bash
uv run python -m proyecto_final.flows.registry_flow
```

*Qué hace:* reentrena el candidato (`training.candidate` del config), lo registra
con signature + input_example, asigna el alias `champion` y se auto-verifica
cargando `models:/salarios-ai-ml-model@champion` y prediciendo 5 filas.
**✅ Criterio:** `RMSE=68,142` **exacto** (la prueba de reproducibilidad estrella),
`Registrado: salarios-ai-ml-model vN -> alias 'champion'` y las 5 predicciones.
Si lo corres otra vez crea v2, v3... y el alias se mueve a la última — ese es el
comportamiento correcto de un registry (versionado).

### Paso 8 — Cierre

```bash
uv run pytest && uv run ruff check .
```

**✅ Éxito total:** 22 tests · 78.233 / 68.547 / 68.142 exactos (pasos 4 y 7) ·
Optuna y comparación en la banda 68–69k · 15 child runs anidados · champion
carga por alias y predice · los 6 flows en verde en Prefect.

### Cómo revisar el champion registrado (3 formas)

**1. En la UI de MLflow** — http://127.0.0.1:5000 → pestaña **Models** (menú superior):

- Clic en `salarios-ai-ml-model`: verás la **descripción del modelo** (qué predice,
  qué columnas espera, cómo consumirlo por alias), la lista de **versiones**
  (v1, v2, ...) y en la columna de aliases cuál tiene **@champion**.
- Clic en la versión con el alias: su **descripción** dice qué modelo es y por qué
  se eligió; sus **tags** traen los hiperparámetros (`param_*`), las métricas
  (`rmse`, `mae`, `r2`) y el hash de los datos de entrenamiento
  (`train_data_sha256`) — todo legible sin abrir el run.
- Además: el **source run** (`register_champion`, link a sus params y métricas
  completos), la **signature** (el contrato: qué columnas de entrada espera y qué
  devuelve) y el **input example** (las 5 filas de muestra).
- La distinción clave para la sustentación: la pestaña *Experiments* muestra los
  **runs** (historia de experimentación); la pestaña *Models* muestra el
  **catálogo** (qué modelo está "bendecido" para producción y bajo qué nombre).

**2. Por código** — así lo consumirá el deploy (sin saber el número de versión):

```python
import mlflow

mlflow.set_tracking_uri("http://127.0.0.1:5000")
champion = mlflow.sklearn.load_model("models:/salarios-ai-ml-model@champion")
# champion.predict(df_con_columnas_crudas)  -> salarios en USD
```

**3. Con el cliente, para inspeccionar metadata** (qué versión es el champion y de
qué run salió):

```python
from mlflow.tracking import MlflowClient

client = MlflowClient(tracking_uri="http://127.0.0.1:5000")
v = client.get_model_version_by_alias("salarios-ai-ml-model", "champion")
print(v.version, v.run_id, v.creation_timestamp)
```

## 5. Preguntas de sustentación (autoevalúate: debes poder responderlas sin mirar)

1. ¿Por qué se excluyen `salary` y `salary_currency`? *(leakage: `salary_in_usd` es su conversión directa — el modelo "vería la respuesta")*
2. ¿Por qué la partición es por año y no aleatoria? *(simula producción: entrenar con el pasado, predecir el "futuro"; una partición aleatoria infla las métricas)*
3. ¿Qué es `OTHER` y por qué las categorías frecuentes se calculan solo con train? *(agrupa categorías raras/no vistas; si mirara validación habría leakage)*
4. ¿Para qué sirve un dummy que siempre predice la mediana? *(es la vara: si un modelo no le gana, las features no aportan)*
5. ¿Por qué se loguea el pipeline completo y no solo el modelo? *(el deploy recibe datos crudos; el pipeline garantiza el mismo preprocesamiento de entrenamiento)*
6. ¿Qué es un parent run y un child run en MLflow? *(el parent agrupa el estudio de Optuna; cada trial es un child anidado — comparables en la UI)*
7. ¿Optuna "fracasó" al mejorar solo 0,59%? *(no: es un hallazgo documentado — el límite está en las features; se decidió no maquillarlo ampliando la búsqueda)*
8. ¿Por qué todo se corre con `uv run` y la config vive en un YAML? *(reproducibilidad: mismo entorno para todos vía `uv.lock`; sin valores quemados, cambiar parámetros no toca código)*
9. ¿Qué garantiza que el peer review pueda ejecutar esto? *(código agnóstico a Prefect Cloud, datos descargables por flow, `uv sync` reconstruye el entorno exacto)*
10. ¿Cómo recuperarías el modelo exacto del mejor trial sin reentrenar? *(cada trial guardó su `mlflow_run_id` — está en el artifact `top_trials.json` del parent run)*
11. ¿Qué "precisión" tiene el modelo? *(no aplica accuracy en regresión; responder con la tabla de la sección 2: R² 0.234, error típico ~48 mil USD, 55% de predicciones dentro de ±30% — y el encuadre: estimador de referencia de mercado, no tasador)*
12. ¿Por qué no usaron otra familia de modelos? *(sí se probó: lineal, Ridge y gradient boosting, con y sin log-target — todas en la banda ~68–69k; la evidencia está en los runs `stage=model-comparison`)*
