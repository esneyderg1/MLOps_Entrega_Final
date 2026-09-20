# Guía de estudio del proyecto

Documento **vivo** para que cualquier integrante se ponga al día rápido: dónde
vamos, cómo funciona lo construido, qué archivos leer y en qué orden. Se
actualiza cada vez que se completa una actividad del checklist (CLAUDE.md).

> **Última actualización:** 2026-09-20 — completadas las actividades 1–7 (7/11).
> Siguiente: actividad 8 (modelo candidato + Model Registry).

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
| 8 | Candidato + Registry | ⬜ | Evidencia lista (comparación de 6 modelos, `comparison_flow`): el candidato es el mejor RF de Optuna — falta registrarlo con alias |
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

## 4. Cómo correrlo tú mismo (la mejor forma de estudiar)

```bash
# terminal 1: el MLflow server (déjalo corriendo)
uv run mlflow server --host 127.0.0.1 --port 5000 --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./mlruns --allowed-hosts "localhost,127.0.0.1,127.0.0.1:5000"

# terminal 2: el pipeline, etapa por etapa
uv run python -m proyecto_final.flows.acquisition_flow
uv run python -m proyecto_final.flows.processing_flow
uv run python -m proyecto_final.flows.baseline_flow
uv run python -m proyecto_final.flows.optimization_flow   # ~varios minutos (15 trials)
uv run python -m proyecto_final.flows.comparison_flow      # 6 familias/variantes (~1 min)

# validaciones rápidas
uv run pytest && uv run ruff check .
```

Luego abre **http://127.0.0.1:5000** (experimento `salarios-ai-ml`) y compara los
runs; los flows se ven en **Prefect Cloud** (o local). Ojo: `mlflow.db` es local
— cada quien ve los runs de SU máquina.

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
