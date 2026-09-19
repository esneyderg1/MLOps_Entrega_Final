# Decisiones técnicas del proyecto

Registro de las decisiones relevantes del equipo. Cada decisión nueva se agrega
aquí con fecha y responsable, y se refleja en CLAUDE.md si cambia una regla.

| Fecha | Decisión | Justificación | Responsable |
|---|---|---|---|
| 2026-09-17 | Gestión de dependencias con `uv` y Python 3.11 | Mismo stack del curso (repo MLOps_UdM); entornos reproducibles con `uv.lock` | Equipo |
| 2026-09-17 | Tracking y registry con MLflow (server local + SQLite) | Requisito de la entrega; SQLite habilita el Model Registry | Equipo |
| 2026-09-17 | Orquestación con Prefect (flows en `src/proyecto_final/flows/`) | Requisito de la entrega | Equipo |
| 2026-09-17 | Conventional commits, sin coautores automáticos | Recomendado por la entrega; commits solo a nombre de integrantes | Equipo |
| 2026-09-17 | **Dataset (PROVISIONAL):** The Global AI/ML/Data Science Salary for 2025 (Kaggle) | Tabular, 88.584 filas sin nulos, liviano (~600 KB), descarga anónima automatizable (verificada), problema de regresión claro con caso de negocio natural (benchmarking salarial) y partición temporal honesta (≤2024 / 2025). Ficha completa en `docs/dataset.md` | Esneyder (pendiente aval del equipo y la profesora) |
| 2026-09-17 | Problema: regresión sobre `salary_in_usd`; métrica principal RMSE (apoyo: MAE, R²); validación temporal ≤2024 vs 2025 | Replica el patrón del curso (entrenar pasado, validar "futuro"); RMSE en USD es interpretable para el caso de negocio | Equipo |
| 2026-09-18 | **Dataset confirmado (ya no provisional):** The Global AI/ML/Data Science Salary for 2025 (Kaggle) | Aval de la profesora y del equipo obtenido (fuente Kaggle aceptada, unicidad frente a otros equipos verificada) | Equipo |
| 2026-09-18 | **EDA completado** (`notebooks/01_eda.ipynb`): no eliminar duplicados exactos (esperables por baja cardinalidad combinada + salarios redondeados; no cruzan entre años) ni atípicos altos (1.98%, roles senior/ejecutivos reales); agrupar `job_title` y `employee_residence`/`company_location` por baja frecuencia en el preprocesamiento; evaluar `log1p(salary_in_usd)` como variante de target (destransformando con `expm1` antes del RMSE); partición temporal confirmada: train `work_year`≤2024 (62.234 filas), validación `work_year`=2025 (15.875 filas) | Distribuciones de target y de `experience_level` consistentes entre 2024 y 2025 (ver notebook); cero nulos en el dataset, no se requieren imputaciones | Equipo |

## Pendientes

- [ ] Modalidad de despliegue: batch / web service (FastAPI) / Docker
- [ ] Timeline con responsables por fase (requisito de la Fase 1 del proyecto)
- [ ] Verificar la licencia del dataset en la página de Kaggle
