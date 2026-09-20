"""Optimización de hiperparámetros del RandomForest con Optuna (actividad 7).

Funciones puras y testeables: el estudio en sí (que sí necesita Optuna real y
un run de MLflow por trial) se ejecuta desde
`proyecto_final.flows.optimization_flow` (regla 3 de CLAUDE.md).
"""

import optuna


def suggest_rf_params(trial: optuna.trial.Trial, search_space: dict) -> dict:
    """Sugiere hiperparámetros de RandomForest según `training.optuna.search_space`
    (configs/config.yaml): sin esto, el espacio de búsqueda quedaría quemado en
    el código (regla 6 de CLAUDE.md).

    Soporta dos formas de espacio: rango entero (`{low, high}`) o lista de
    opciones (categórico), para no acoplar la función a un hiperparámetro
    específico del RandomForest.
    """
    params = {}
    for name, spec in search_space.items():
        if isinstance(spec, dict):
            params[name] = trial.suggest_int(name, spec["low"], spec["high"])
        else:
            params[name] = trial.suggest_categorical(name, spec)
    return params


def summarize_top_trials(study: optuna.Study, n_top: int) -> list[dict]:
    """Devuelve los `n_top` trials con menor RMSE, con su `mlflow_run_id`.

    El run_id se guarda como user_attr de cada trial dentro del objective (ver
    optimization_flow); así el equipo puede recuperar el modelo exacto de
    cualquiera de los mejores trials para el Model Registry (actividad 8).
    """
    trials_completos = [t for t in study.trials if t.value is not None]
    mejores = sorted(trials_completos, key=lambda t: t.value)[:n_top]
    return [
        {
            "trial_number": t.number,
            "rmse": t.value,
            "params": t.params,
            "mlflow_run_id": t.user_attrs.get("mlflow_run_id"),
        }
        for t in mejores
    ]
