from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "transaction_pipeline",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.pipeline_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    task_track_started=True,
    task_routes={
        "app.tasks.pipeline_tasks.run_processing_pipeline": {"queue": "processing_queue"},
        "app.tasks.pipeline_tasks.run_llm_pipeline": {"queue": "llm_queue"},
    },
    task_default_queue="processing_queue",
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)
