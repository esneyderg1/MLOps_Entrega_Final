# Guion de la presentación (borrador)

Punto de partida para armar las slides (actividad 11). Cada sección es una
slide; el contenido ya está verificado y documentado en el resto del repo —
aquí solo se organiza el orden de la historia. Ajustar libremente.

> Las slides ya están armadas en **`docs/presentacion.html`** (abrir en el
> navegador; funciona sin internet). Cada slide muestra arriba a la derecha la
> insignia de quién la presenta.

## Reparto de temas (acordado 2026-09-22)

| Quién | Temas | Slide |
|---|---|---|
| **Carolina** | Problema de negocio, dataset y conclusiones del EDA (qué se conserva, qué se agrupa, partición temporal) | 2 |
| **Juanita** | Procesamiento sin leakage (`processing_flow`) y optimización con Optuna (parent/child runs) | 3 |
| **Yennifer** | Baseline (dummy + RF), comparación de familias y resultados/precisión con el hallazgo honesto del 0,59% | 4 |
| **Esneyder** | Registro del champion en MLflow, orquestación end-to-end (`pipeline_flow` en vivo), y despliegue FastAPI/Docker con la demo de cierre | 5 y 6 |

La presentación cierra con la demo en vivo (sin slide de cierre aparte). Las
15 preguntas de sustentación de `docs/guia_estudio.md` las repasamos los
cuatro sin importar el reparto.

## 1. Problema y dataset (1 slide)

- Caso de negocio: estimar salario de referencia (USD) para roles de datos/IA
  al publicar una vacante (ver `docs/dataset.md`, sección "Definición del problema").
- Dataset: *The Global AI/ML/Data Science Salary for 2025* (Kaggle), 88.584 filas,
  11 columnas, cero nulos. Target: `salary_in_usd`. Métrica: RMSE (validación temporal).

## 2. Arquitectura del pipeline (1 slide)

- Usar el diagrama de `README.md` (sección "Arquitectura del pipeline") o el
  ampliado de `docs/guia_estudio.md` (sección 2).
- Mensaje clave: cada etapa es un flow de Prefect independiente, y
  `pipeline_flow` las encadena como subflows — un solo comando reproduce todo.

## 3. Resultados del modelo (1-2 slides)

- Tabla de `docs/guia_estudio.md` sección "¿Qué precisión tiene el modelo?":
  R² 0.234, MAE ~48 mil USD, 55% de las predicciones dentro de ±30%.
- Hallazgo honesto: Optuna solo mejoró el baseline en 0.59% (68.142 vs 68.547 USD).
  Confirmado con 4 familias de modelos distintas (`comparison_flow`) convergiendo
  a la misma banda ~68-69k: el techo está en las features, no en el algoritmo.
- Encuadre: el modelo es un estimador de referencia de mercado, no un tasador exacto.

## 4. MLflow: tracking y Model Registry (1 slide)

- Screenshot de la UI: experimento `salarios-ai-ml` con los runs de baseline,
  Optuna (parent + 15 childs) y comparación.
- Screenshot de la pestaña Models: `salarios-ai-ml-model`, versión con alias
  `champion`, tags con métricas e hiperparámetros.

## 5. Despliegue (1 slide)

- Modalidad: web service con FastAPI + Docker (decisión y justificación en
  `docs/decisiones.md`, entrada 2026-09-22).
- Demo en vivo si es posible: `docker compose up`, abrir http://localhost:8000,
  hacer una predicción desde la interfaz web o con curl.
- Mensaje clave: el servicio no depende del Tracking Server en runtime (copia
  el modelo a disco antes de arrancar) — más simple y más portable.

## 6. Calidad y reproducibilidad (1 slide)

- 45 tests unitarios, `ruff check`/`format` en verde.
- Código agnóstico al servidor de Prefect (Cloud o local, mismo comando).
- Sin valores quemados: todo en `configs/config.yaml`.

## 7. Aprendizajes y limitaciones (1 slide)

- El "fracaso" de Optuna (0.59% de mejora) como hallazgo honesto, no oculto.
- 90% de los registros son de EE. UU.: limitación documentada, no escondida.
- Alcance: hasta el despliegue, sin monitoreo (fuera del alcance de la entrega).

## Preguntas de sustentación

Todas las preguntas que el equipo debe poder responder sin mirar están en
`docs/guia_estudio.md`, sección 5 (15 preguntas, con la respuesta esperada
entre paréntesis). Repasarlas antes de la sustentación.
