"""Procesamiento de datos y feature engineering.

Transformaciones reproducibles de data/raw/ a data/processed/ según las
conclusiones del EDA (leakage, partición temporal, agrupación de categorías
raras), más el preprocesador sklearn reutilizable. Orquestadas como flow de
Prefect en proyecto_final.flows.processing_flow.
"""
