"""Entrenamiento, optimización, evaluación y registro de modelos.

La lógica pura (pipelines, métricas) vive en `training.py`; el tracking en
MLflow y la orquestación viven en los flows (`baseline_flow`, y los que sigan).
Reglas: todo run trackeado en MLflow, Optuna con parent/child runs, promoción
con aliases (ver CLAUDE.md, regla 2).
"""
