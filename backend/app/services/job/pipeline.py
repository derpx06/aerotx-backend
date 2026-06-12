from uuid import UUID

import structlog

from app.core.database import SessionLocal
from app.domain.events import JobFailed
from app.infrastructure.events import SqlAlchemyDomainEventPublisher
from app.models.enums import JobStatus
from app.repositories.event_repository import EventRepository
from app.repositories.job_repository import JobRepository
from app.services.job.stages import (
    AnomalyDetectionStage,
    ClassificationStage,
    CleaningStage,
    CompletionStage,
    DeduplicationStage,
    FileValidationStage,
    PersistenceStage,
    PipelineContext,
    SummaryGenerationStage,
)

log = structlog.get_logger(__name__)


class ProcessingPipeline:
    stages = [
        FileValidationStage(),
        CleaningStage(),
        DeduplicationStage(),
        AnomalyDetectionStage(),
        PersistenceStage(),
    ]

    async def run(self, job_id: UUID) -> None:
        async with SessionLocal() as session:
            try:
                job_repo = JobRepository(session)
                claimed = await job_repo.claim_status_transition(
                    job_id,
                    expected_statuses={JobStatus.PENDING},
                    next_status=JobStatus.PROCESSING,
                    mark_started=True,
                )
                if not claimed:
                    await session.rollback()
                    log.info("processing_pipeline_skipped_idempotent_replay", job_id=str(job_id))
                    return
                context = PipelineContext(job_id=job_id, session=session)
                for stage in self.stages:
                    await stage.run(context)
                await job_repo.set_status(job_id, JobStatus.LLM_PROCESSING)
                await session.commit()
                log.info("processing_pipeline_completed", job_id=str(job_id))
            except Exception as exc:
                await session.rollback()
                await self._mark_failed(job_id, str(exc))
                raise

    async def _mark_failed(self, job_id: UUID, error: str) -> None:
        async with SessionLocal() as session:
            await JobRepository(session).set_status(job_id, JobStatus.FAILED, error)
            publisher = SqlAlchemyDomainEventPublisher(EventRepository(session))
            await publisher.publish(JobFailed(job_id, error=error, phase="processing"))
            await session.commit()


class LLMPipeline:
    async def run(self, job_id: UUID) -> None:
        async with SessionLocal() as session:
            try:
                job_repo = JobRepository(session)
                claimed = await job_repo.claim_status_transition(
                    job_id,
                    expected_statuses={JobStatus.LLM_PROCESSING},
                    next_status=JobStatus.LLM_PROCESSING,
                )
                if not claimed:
                    await session.rollback()
                    log.info("llm_pipeline_skipped_idempotent_replay", job_id=str(job_id))
                    return
                context = PipelineContext(job_id=job_id, session=session)
                llm_success = await ClassificationStage().run(context)
                if not llm_success:
                    await job_repo.mark_llm_failed(job_id)
                await job_repo.set_status(job_id, JobStatus.REPORTING)
                await session.commit()
                log.info("llm_pipeline_completed", job_id=str(job_id), llm_success=llm_success)
            except Exception as exc:
                await session.rollback()
                async with SessionLocal() as fail_session:
                    await JobRepository(fail_session).mark_llm_failed(job_id)
                    await JobRepository(fail_session).set_status(job_id, JobStatus.REPORTING)
                    publisher = SqlAlchemyDomainEventPublisher(EventRepository(fail_session))
                    await publisher.publish(JobFailed(job_id, error=str(exc), phase="llm"))
                    await fail_session.commit()


class ReportingPipeline:
    async def run(self, job_id: UUID) -> None:
        async with SessionLocal() as session:
            try:
                job_repo = JobRepository(session)
                claimed = await job_repo.claim_status_transition(
                    job_id,
                    expected_statuses={JobStatus.REPORTING},
                    next_status=JobStatus.REPORTING,
                )
                if not claimed:
                    await session.rollback()
                    log.info("reporting_pipeline_skipped_idempotent_replay", job_id=str(job_id))
                    return
                context = PipelineContext(job_id=job_id, session=session)
                llm_success = await SummaryGenerationStage().run(context)
                if not llm_success:
                    await job_repo.mark_llm_failed(job_id)
                await CompletionStage().run(context)
                await session.commit()
                log.info(
                    "reporting_pipeline_completed", job_id=str(job_id), llm_success=llm_success
                )
            except Exception as exc:
                await session.rollback()
                async with SessionLocal() as fail_session:
                    await JobRepository(fail_session).set_status(job_id, JobStatus.FAILED, str(exc))
                    publisher = SqlAlchemyDomainEventPublisher(EventRepository(fail_session))
                    await publisher.publish(JobFailed(job_id, error=str(exc), phase="reporting"))
                    await fail_session.commit()
                raise
