from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.core.config import APP_NAME, APP_VERSION
from app.ml.predictor import ModelsUnavailableError
from app.services.message_bus_service import register_sensor
from app.sensors.people_location_sensor import PeopleLocationSensor


@asynccontextmanager
async def lifespan(app: FastAPI):
    people_sensor = PeopleLocationSensor()
    register_sensor(
        sensor_type=people_sensor.sensor_type,
        device_name=people_sensor.device_name,
    )
    yield


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="Zonalyze backend for simulated business feasibility intelligence",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ModelsUnavailableError)
async def models_unavailable_handler(request: Request, exc: ModelsUnavailableError):
    """Return a clear 503 instead of a raw 500 when model artifacts are missing."""
    return JSONResponse(
        status_code=503,
        content={
            "error": "models_unavailable",
            "message": str(exc),
        },
    )


app.include_router(router)