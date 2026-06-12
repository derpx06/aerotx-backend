import logging
import sys
import time
import uuid
from collections.abc import Awaitable, Callable
from contextvars import ContextVar

import structlog
from fastapi import Request, Response

from app.core.config import get_settings

request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)
correlation_id_ctx: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def add_context(_, __, event_dict):
    event_dict["request_id"] = request_id_ctx.get()
    event_dict["correlation_id"] = correlation_id_ctx.get()
    event_dict.setdefault("service", "transaction-pipeline")
    event_dict.setdefault("operation", None)
    event_dict.setdefault("duration", None)
    event_dict.setdefault("job_id", None)
    event_dict.setdefault("error_context", None)
    return event_dict


def configure_logging() -> None:
    settings = get_settings()
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=settings.log_level)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            add_context,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level.upper(), logging.INFO)
        ),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


try:
    from celery.signals import after_setup_logger, after_setup_user_logger, worker_process_init

    @after_setup_logger.connect
    @after_setup_user_logger.connect
    def setup_celery_logging(logger, *args, **kwargs):
        configure_logging()

    @worker_process_init.connect
    def setup_celery_tracing(*args, **kwargs):
        from app.services.observability.tracing import init_tracer
        init_tracer()
except ImportError:
    pass


async def request_context_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    correlation_id = request.headers.get("x-correlation-id", request_id)
    request_id_ctx.set(request_id)
    correlation_id_ctx.set(correlation_id)
    started_at = time.perf_counter()
    log = structlog.get_logger(__name__)
    operation = f"{request.method} {request.url.path}"
    log.info(
        "api_request_started", method=request.method, path=request.url.path, operation=operation
    )
    try:
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        response.headers["x-correlation-id"] = correlation_id
        log.info(
            "api_request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            operation=operation,
            duration=round(time.perf_counter() - started_at, 6),
        )
        return response
    except Exception as exc:
        log.exception(
            "api_request_failed",
            method=request.method,
            path=request.url.path,
            operation=operation,
            duration=round(time.perf_counter() - started_at, 6),
            error_context={"type": type(exc).__name__, "message": str(exc)},
        )
        raise
