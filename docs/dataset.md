# Ficha del dataset — The Global AI/ML/Data Science Salary for 2025

> **Estado: confirmado (2026-09-18).** Aval de la profesora (fuente Kaggle) y del
> equipo obtenidos; unicidad frente a otros equipos verificada.

## Fuente

- **Página:** https://www.kaggle.com/datasets/samithsachidanandan/the-global-ai-ml-data-science-salary-for-2025
- **Descarga automatizable:** endpoint público de la API de Kaggle (verificado: funciona **sin credenciales**, devuelve un zip con `salaries.csv`):
  `https://www.kaggle.com/api/v1/datasets/download/samithsachidanandan/the-global-ai-ml-data-science-salary-for-2025`
- **Origen de los datos:** encuestas salariales agregadas de roles de AI/ML/Data (originalmente publicadas por ai-jobs.net).
- **Licencia:** verificar en la página de Kaggle antes de la entrega.
- **Ojo:** el dataset se actualiza en Kaggle. Cada descarga queda versionada con
  su `metadata.json` (filas + sha256), según la regla 7 de CLAUDE.md.

## Perfil (descarga del 2026-09-17)

- **88.584 filas × 11 columnas, cero valores nulos.** Peso: ~600 KB (zip).
- Años: 2020 (75), 2021 (218), 2022 (1.660), 2023 (8.522), **2024 (62.234), 2025 (15.875)**.
- `salary_in_usd`: mín $15.000 · mediana $146.307 · p99 $375.000 · máx $800.000 → **cola derecha pesada** (tratar en preprocesamiento: filtro de atípicos y/o log-transformación).
- 90% de los registros son de empresas en EE. UU. (documentar como limitación).

## Diccionario de datos

| Columna | Tipo | Cardinalidad | Descripción | Uso en el modelo |
|---|---|---|---|---|
| `work_year` | int | 6 (2020–2025) | Año del registro salarial | Feature / eje de partición temporal |
| `experience_level` | cat | 4 (EN/MI/SE/EX) | Seniority: Entry, Mid, Senior, Executive | Feature |
| `employment_type` | cat | 4 (FT/PT/CT/FL) | Tiempo completo, parcial, contrato, freelance | Feature |
| `job_title` | cat | 312 | Título del cargo (p. ej. Data Scientist, Data Engineer) | Feature (alta cardinalidad → requiere agrupación/encoding) |
| `salary` | num | — | Salario en moneda original | **EXCLUIDA (leakage)** |
| `salary_currency` | cat | — | Moneda del salario original | **EXCLUIDA (leakage)** |
| `salary_in_usd` | num | — | Salario anual convertido a USD | **TARGET** |
| `employee_residence` | cat | 96 | País de residencia del empleado (ISO-2) | Feature |
| `remote_ratio` | int | 3 (0/50/100) | % de trabajo remoto | Feature |
| `company_location` | cat | 90 | País de la empresa (ISO-2) | Feature |
| `company_size` | cat | 3 (S/M/L) | Tamaño de la empresa | Feature |

## Definición del problema

- **Tipo:** regresión.
- **Target:** `salary_in_usd`.
- **Problema de negocio (hipotético):** un área de compensación/atracción de talento
  necesita estimar el salario de mercado en USD para roles de datos e IA al momento
  de publicar una vacante o preparar una oferta. El modelo entrega un salario de
  referencia según el rol, seniority, tipo de contrato, ubicación, modalidad remota
  y tamaño de la empresa, reduciendo ofertas desalineadas con el mercado.
- **Métrica principal:** RMSE en USD sobre validación temporal (entrenar con ≤2024,
  validar con 2025 — mismo patrón enero/febrero del curso: entrenar con el pasado,
  validar con el "futuro"). Métricas de apoyo: MAE y R².
- **Criterio de éxito:** el modelo optimizado (Optuna) debe mejorar el RMSE del
  baseline en al menos ~10% (la cifra exacta del baseline se fija en la actividad 6).

## Riesgos identificados y su manejo

| Riesgo | Manejo |
|---|---|
| `salary`/`salary_currency` son el target disfrazado | Excluirlas siempre (`leakage_columns` en `configs/config.yaml`) |
| Cola pesada del target (máx $800k) | Filtro de atípicos y/o `log(salary_in_usd)` — decidir en el EDA |
| 90% registros de EE. UU. | Documentar como limitación o filtrar a US — decidir en el EDA |
| `job_title` con 312 valores | Agrupar títulos poco frecuentes / encoding — decidir en el EDA |
| Dataset vivo (se actualiza en Kaggle) | `metadata.json` con sha256 en cada descarga |
| Desempeño moderado esperado (features categóricas gruesas) | Comunicarlo en la presentación: la nota evalúa el pipeline, no el R² |
