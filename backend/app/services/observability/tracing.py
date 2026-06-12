import structlog
from opentelemetry import trace
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

log = structlog.get_logger(__name__)


def init_tracer(service_name: str = "transaction-pipeline") -> trace.Tracer:
    # Check if a tracer provider is already configured to avoid duplicates
    provider = trace.get_tracer_provider()
    if isinstance(provider, TracerProvider):
        return trace.get_tracer("transaction-pipeline")

    resource = Resource.create(attributes={"service.name": service_name})
    provider = TracerProvider(resource=resource)

    # Use simple processor exporting to stdout/console for local profiling & verification
    processor = SimpleSpanProcessor(ConsoleSpanExporter())
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    # Instrument third party dependencies
    HTTPXClientInstrumentor().instrument()
    CeleryInstrumentor().instrument()

    try:
        from app.core.database import engine

        if hasattr(engine, "sync_engine"):
            SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)
        elif engine is not None:
            SQLAlchemyInstrumentor().instrument(engine=engine)
    except (ImportError, AttributeError):
        log.warning("opentelemetry_sqlalchemy_instrumentation_skipped")

    log.info("opentelemetry_initialized", service_name=service_name)
    return trace.get_tracer("transaction-pipeline")


def instrument_app(app) -> None:
    FastAPIInstrumentor().instrument_app(app)


def get_tracer() -> trace.Tracer:
    return trace.get_tracer("transaction-pipeline")
