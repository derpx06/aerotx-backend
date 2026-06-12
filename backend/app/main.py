from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.jobs import router as jobs_router
from app.api.metrics import router as metrics_router
from app.core.config import get_settings
from app.core.logging import configure_logging, request_context_middleware


def create_app() -> FastAPI:
    configure_logging()
    from app.services.observability.tracing import init_tracer, instrument_app
    init_tracer()
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0")
    instrument_app(app)
    app.middleware("http")(request_context_middleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(metrics_router)
    app.include_router(jobs_router)
    return app


app = create_app()
