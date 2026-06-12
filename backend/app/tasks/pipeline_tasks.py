import asyncio
from uuid import UUID

import structlog

from app.core.celery_app import celery_app
from app.services.job.pipeline import LLMPipeline, ProcessingPipeline, ReportingPipeline

log = structlog.get_logger(__name__)


@celery_app.task(name="app.tasks.pipeline_tasks.run_processing_pipeline")
def run_processing_pipeline(job_id: str) -> None:
    asyncio.run(ProcessingPipeline().run(UUID(job_id)))
    run_llm_pipeline.apply_async(args=[job_id], queue="llm_queue")
    log.info("llm_task_enqueued", job_id=job_id)


@celery_app.task(name="app.tasks.pipeline_tasks.run_llm_pipeline")
def run_llm_pipeline(job_id: str) -> None:
    asyncio.run(LLMPipeline().run(UUID(job_id)))
    asyncio.run(ReportingPipeline().run(UUID(job_id)))
    log.info("llm_and_reporting_completed", job_id=job_id)
