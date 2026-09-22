"""Flow maestro: orquestación end-to-end del pipeline (actividad 9).

Encadena los flows ya existentes como SUBFLOWS de Prefect: al llamar una función
decorada con @flow desde dentro de otro @flow, Prefect crea un flow run anidado,
y la UI muestra la jerarquía completa (padre + etapas adentro). Por eso aquí no
se reescribe nada: cada etapa sigue viviendo en su propio módulo y sigue
pudiéndose correr por separado.

Orden: adquisición -> procesamiento -> baseline -> (optimización opcional) -> registro.
La comparación de familias (comparison_flow) queda fuera a propósito: fue evidencia
puntual para elegir el candidato, no parte del ciclo productivo.

Ejecutar de punta a punta con:
    uv run python -m proyecto_final.flows.pipeline_flow
    uv run python -m proyecto_final.flows.pipeline_flow --con-optimizacion
"""

import argparse

from mlflow.tracking import MlflowClient
from prefect import flow, task

from proyecto_final.config import enable_utf8_output, get_config
from proyecto_final.flows.acquisition_flow import acquisition_flow
from proyecto_final.flows.baseline_flow import baseline_flow
from proyecto_final.flows.optimization_flow import optimization_flow
from proyecto_final.flows.processing_flow import processing_flow
from proyecto_final.flows.registry_flow import registry_flow


@task(log_prints=True)
def check_mlflow_task(tracking_uri: str) -> None:
    """Falla temprano y con un mensaje accionable si el Tracking Server no está.

    Sin esto, el pipeline descargaría y procesaría los datos (minutos de trabajo)
    para reventar recién en el baseline con un error de conexión poco claro.
    """
    try:
        MlflowClient(tracking_uri=tracking_uri).search_experiments(max_results=1)
    except Exception as error:
        raise RuntimeError(
            f"No hay MLflow Tracking Server escuchando en {tracking_uri}. "
            "Levántalo en otra terminal con:\n"
            "  uv run mlflow server --host 127.0.0.1 --port 5000 "
            "--backend-store-uri sqlite:///mlflow.db --default-artifact-root ./mlruns "
            '--allowed-hosts "localhost,127.0.0.1,127.0.0.1:5000"'
        ) from error
    print(f"MLflow Tracking Server disponible en {tracking_uri}")


@flow(name="pipeline-completo-salarios", log_prints=True)
def pipeline_flow(run_optimization: bool = False) -> dict:
    """Orquesta el ciclo de vida completo en una sola ejecución (actividad 9).

    Los subflows se invocan de forma síncrona: Prefect espera a que cada uno
    termine antes de llamar el siguiente, así que el orden queda garantizado.
    Además, cada etapa valida su insumo (p. ej. processing_flow falla si no
    existe data/raw/), de modo que un orden equivocado nunca pasaría silencioso.
    """
    enable_utf8_output()  # los emojis de MLflow rompen la consola cp1252 de Windows
    config = get_config()

    check_mlflow_task(config["mlflow"]["tracking_uri"])

    raw_metadata = acquisition_flow()
    processed_metadata = processing_flow()
    baseline_metrics = baseline_flow()

    # Opcional: el estudio de Optuna tarda ~5-10 min y su muestreador es
    # aleatorio. No alimenta al registro: el candidato está fijado en
    # configs/config.yaml (training.candidate) tras la decisión de la actividad 8.
    optimization_result = optimization_flow() if run_optimization else None

    registry_result = registry_flow()

    print("--- Pipeline completo terminado ---")
    print(
        f"Datos crudos: {raw_metadata['n_rows']} filas "
        f"(sha256 {raw_metadata['sha256'][:12]}...)"
    )
    print(f"Baseline RF: RMSE={baseline_metrics['rf_baseline']['rmse']:,.0f} USD")
    print(
        f"Champion: {registry_result['registered_model']} "
        f"v{registry_result['version']} -> alias '{registry_result['alias']}' "
        f"| RMSE={registry_result['metrics']['rmse']:,.0f} USD"
    )

    return {
        "raw": raw_metadata,
        "processed": processed_metadata,
        "baseline": baseline_metrics,
        "optimization": optimization_result,
        "registry": registry_result,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline end-to-end de salarios")
    parser.add_argument(
        "--con-optimizacion",
        action="store_true",
        help="incluye el estudio de Optuna (actividad 7) en la cadena",
    )
    args = parser.parse_args()
    pipeline_flow(run_optimization=args.con_optimizacion)
