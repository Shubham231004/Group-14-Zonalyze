import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import public_router, router
from app.core.auth import require_user
from app.core.config import (
    APP_NAME,
    APP_VERSION,
    CORS_ALLOW_ORIGINS,
    RATE_LIMIT,
    RATE_LIMIT_ENABLED,
)
from app.ml.predictor import ModelsUnavailableError
from app.services.message_bus_service import register_sensor
from app.sensors.people_location_sensor import PeopleLocationSensor

logger = logging.getLogger("zonalyze")


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


# --- Security response headers (applied to every response) ---
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
}
# Swagger UI / ReDoc load scripts and styles, so they are exempt from the strict CSP.
_CSP_EXEMPT_PREFIXES = ("/docs", "/redoc", "/openapi")


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    for key, value in SECURITY_HEADERS.items():
        response.headers.setdefault(key, value)
    if not request.url.path.startswith(_CSP_EXEMPT_PREFIXES):
        # This API only ever returns JSON, so a locked-down CSP is safe and does
        # not affect the separately-hosted frontend.
        response.headers.setdefault(
            "Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'"
        )
    return response


# --- Rate limiting (optional; OFF unless RATE_LIMIT_ENABLED=true) ---
if RATE_LIMIT_ENABLED:
    try:
        from slowapi import Limiter, _rate_limit_exceeded_handler
        from slowapi.errors import RateLimitExceeded
        from slowapi.middleware import SlowAPIMiddleware
        from slowapi.util import get_remote_address

        limiter = Limiter(key_func=get_remote_address, default_limits=[RATE_LIMIT])
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        app.add_middleware(SlowAPIMiddleware)
        logger.info("Rate limiting enabled: %s per client IP.", RATE_LIMIT)
    except Exception:
        logger.warning(
            "Rate limiting was requested but could not be enabled "
            "(is slowapi installed? pip install -r requirements.txt).",
            exc_info=True,
        )


# --- CORS (added last so it is the outermost middleware) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
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


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Log full detail server-side; return a sanitized message to the client."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "message": "An unexpected error occurred.",
        },
    )


# Public endpoints (health/root) stay open; everything else requires a valid
# Clerk session token when auth is enabled. When Clerk is not configured,
# require_user is a no-op and all routes behave exactly as before.
app.include_router(public_router)
app.include_router(router, dependencies=[Depends(require_user)])
