"""Entrenamiento, optimización, evaluación y registro de modelos.

Todo entrenamiento se loguea en MLflow; la optimización de hiperparámetros usa
Optuna (parent run + child runs) y el mejor modelo se registra en el Model
Registry con alias (champion/candidate). Ver reglas en CLAUDE.md.
"""
