"""Tests del flow maestro (actividad 9).

No ejecuta el pipeline real: se mockean los subflows y solo se verifica la
orquestación (qué se llama, en qué orden y qué hace el flag de optimización).
Se invoca `pipeline_flow.fn` (la función original que envuelve el decorador)
para no levantar un backend de Prefect dentro de la suite.
"""

from unittest.mock import patch

from proyecto_final.flows.pipeline_flow import pipeline_flow

RAW = {"n_rows": 100, "sha256": "abc123def456789"}
PROCESSED = {"train.parquet": {"n_rows": 80}}
BASELINE = {"rf_baseline": {"rmse": 68547.0}}
OPTIMIZATION = {"best_rmse": 68142.0}
REGISTRY = {
    "registered_model": "salarios-ai-ml-model",
    "version": "1",
    "alias": "champion",
    "metrics": {"rmse": 68142.0},
}


def _record(calls, name, value):
    """Devuelve un side_effect que anota la llamada y responde como el flow real."""

    def _call():
        calls.append(name)
        return value

    return _call


@patch("proyecto_final.flows.pipeline_flow.registry_flow")
@patch("proyecto_final.flows.pipeline_flow.optimization_flow")
@patch("proyecto_final.flows.pipeline_flow.baseline_flow")
@patch("proyecto_final.flows.pipeline_flow.processing_flow")
@patch("proyecto_final.flows.pipeline_flow.acquisition_flow")
@patch("proyecto_final.flows.pipeline_flow.check_mlflow_task")
def test_orden_por_defecto_sin_optimizacion(
    check, acquisition, processing, baseline, optimization, registry
):
    """Sin el flag, la cadena es adquisición -> procesamiento -> baseline -> registro."""
    calls = []
    acquisition.side_effect = _record(calls, "acquisition", RAW)
    processing.side_effect = _record(calls, "processing", PROCESSED)
    baseline.side_effect = _record(calls, "baseline", BASELINE)
    registry.side_effect = _record(calls, "registry", REGISTRY)

    resultado = pipeline_flow.fn()

    assert calls == ["acquisition", "processing", "baseline", "registry"]
    optimization.assert_not_called()
    assert resultado["optimization"] is None
    assert resultado["registry"]["alias"] == "champion"


@patch("proyecto_final.flows.pipeline_flow.registry_flow")
@patch("proyecto_final.flows.pipeline_flow.optimization_flow")
@patch("proyecto_final.flows.pipeline_flow.baseline_flow")
@patch("proyecto_final.flows.pipeline_flow.processing_flow")
@patch("proyecto_final.flows.pipeline_flow.acquisition_flow")
@patch("proyecto_final.flows.pipeline_flow.check_mlflow_task")
def test_con_optimizacion_corre_optuna_antes_del_registro(
    check, acquisition, processing, baseline, optimization, registry
):
    """Con el flag, Optuna entra en la cadena justo antes del registro."""
    calls = []
    acquisition.side_effect = _record(calls, "acquisition", RAW)
    processing.side_effect = _record(calls, "processing", PROCESSED)
    baseline.side_effect = _record(calls, "baseline", BASELINE)
    optimization.side_effect = _record(calls, "optimization", OPTIMIZATION)
    registry.side_effect = _record(calls, "registry", REGISTRY)

    resultado = pipeline_flow.fn(run_optimization=True)

    assert calls == [
        "acquisition",
        "processing",
        "baseline",
        "optimization",
        "registry",
    ]
    assert resultado["optimization"] == OPTIMIZATION


@patch("proyecto_final.flows.pipeline_flow.registry_flow")
@patch("proyecto_final.flows.pipeline_flow.optimization_flow")
@patch("proyecto_final.flows.pipeline_flow.baseline_flow")
@patch("proyecto_final.flows.pipeline_flow.processing_flow")
@patch("proyecto_final.flows.pipeline_flow.acquisition_flow")
@patch("proyecto_final.flows.pipeline_flow.check_mlflow_task")
def test_verifica_mlflow_antes_de_descargar(
    check, acquisition, processing, baseline, optimization, registry
):
    """El chequeo de MLflow ocurre antes de gastar minutos descargando y entrenando."""
    acquisition.side_effect = _record([], "acquisition", RAW)
    processing.return_value = PROCESSED
    baseline.return_value = BASELINE
    registry.return_value = REGISTRY

    pipeline_flow.fn()

    check.assert_called_once()
