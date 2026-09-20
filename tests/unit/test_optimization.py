"""Tests de proyecto_final.models.optimization (actividad 7 del checklist)."""

import optuna

from proyecto_final.models.optimization import suggest_rf_params, summarize_top_trials

SEARCH_SPACE = {
    "n_estimators": {"low": 100, "high": 500},
    "max_features": ["sqrt", "log2", None],
}


def test_suggest_rf_params_respeta_rango_entero():
    trial = optuna.trial.FixedTrial({"n_estimators": 250, "max_features": "sqrt"})

    params = suggest_rf_params(trial, SEARCH_SPACE)

    assert params == {"n_estimators": 250, "max_features": "sqrt"}


def test_suggest_rf_params_devuelve_solo_las_claves_del_search_space():
    trial = optuna.trial.FixedTrial({"n_estimators": 100, "max_features": None})

    params = suggest_rf_params(trial, SEARCH_SPACE)

    assert set(params) == {"n_estimators", "max_features"}
    assert params["max_features"] is None


def test_summarize_top_trials_ordena_por_menor_rmse_y_conserva_run_id():
    study = optuna.create_study(direction="minimize")

    def objective(trial):
        # rmse decrece con el número de trial: 0 -> 100, 1 -> 90, 2 -> 80, ...
        rmse = 100 - trial.number * 10
        trial.set_user_attr("mlflow_run_id", f"run-{trial.number}")
        return rmse

    study.optimize(objective, n_trials=5)

    top_2 = summarize_top_trials(study, n_top=2)

    assert len(top_2) == 2
    assert top_2[0]["rmse"] < top_2[1]["rmse"]
    assert top_2[0]["trial_number"] == 4  # el último trial tiene el menor rmse (60)
    assert top_2[0]["mlflow_run_id"] == "run-4"
    assert all("params" in t for t in top_2)
