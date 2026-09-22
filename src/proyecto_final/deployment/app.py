"""API REST con FastAPI para predecir el salario de referencia (actividad 10).

Sirve el pipeline COMPLETO (preprocesador + RandomForest) registrado como
champion en el Model Registry, copiado antes a disco con
`proyecto_final.deployment.copy_model`. El alcance de la entrega llega hasta
aquí: predicción de prueba end-to-end, SIN monitoreo (ver CLAUDE.md).

Ejecutar:
    uv run uvicorn proyecto_final.deployment.app:app --host 0.0.0.0 --port 8000
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from proyecto_final.deployment.model_loader import model_loader
from proyecto_final.deployment.schemas import (
    BatchPredictionResponse,
    BatchSalaryRequest,
    HealthResponse,
    PredictionResponse,
    SalaryRequest,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Carga el modelo UNA vez al iniciar la app, no en cada request."""
    logger.info("Iniciando API de salarios...")
    model_loader.load()
    logger.info("API lista para recibir requests")
    yield


app = FastAPI(
    title="Salarios AI/ML/Data Science 2025 - API de predicción",
    description=(
        "Estima el salario anual de referencia (USD) para roles de datos/IA a "
        "partir de seniority, tipo de contrato, cargo, ubicación, modalidad "
        "remota y tamaño de empresa. Modelo champion registrado en MLflow "
        "(RandomForest optimizado con Optuna, RMSE ~68.142 USD)."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

# Permite llamar la API desde una página servida en otro origen (p. ej. la
# interfaz web de otro puerto durante desarrollo). Sin autenticación de
# usuarios de por medio, restringirlo no protege nada adicional aquí.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _to_record(request: SalaryRequest) -> dict:
    return request.model_dump()


def _prediction_response(predicted_salary: float) -> PredictionResponse:
    meta = model_loader.metadata
    return PredictionResponse(
        predicted_salary_usd=round(predicted_salary, 2),
        model_name=meta["registered_model_name"],
        model_version=str(meta["version"]),
        model_alias=meta["alias"],
    )


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Interfaz web simple para probar predicciones sin usar curl/Postman."""
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Verifica que el modelo esté cargado y devuelve su métrica de referencia."""
    if not model_loader.is_loaded():
        raise HTTPException(status_code=503, detail="Modelo no cargado")

    meta = model_loader.metadata
    return HealthResponse(
        status="healthy",
        model_loaded=True,
        model_name=meta["registered_model_name"],
        model_version=str(meta["version"]),
        model_rmse=meta["rmse"],
    )


@app.post("/predict", response_model=PredictionResponse)
async def predict(payload: SalaryRequest):
    """Predice el salario de referencia (USD) para un solo puesto."""
    try:
        prediction = model_loader.predict([_to_record(payload)])[0]
    except Exception as error:
        logger.error("Error en predicción: %s", error)
        raise HTTPException(
            status_code=500, detail=f"Error al hacer predicción: {error}"
        ) from error

    return _prediction_response(prediction)


@app.post("/predict/batch", response_model=BatchPredictionResponse)
async def predict_batch(payload: BatchSalaryRequest):
    """Predice el salario de referencia (USD) para varios puestos a la vez."""
    try:
        records = [_to_record(record) for record in payload.records]
        predictions = model_loader.predict(records)
    except Exception as error:
        logger.error("Error en predicción batch: %s", error)
        raise HTTPException(
            status_code=500, detail=f"Error al hacer predicción batch: {error}"
        ) from error

    responses = [_prediction_response(pred) for pred in predictions]
    return BatchPredictionResponse(predictions=responses, total=len(responses))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
