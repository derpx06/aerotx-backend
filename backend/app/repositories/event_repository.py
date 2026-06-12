from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.events import DomainEvent
from app.models.enums import JobEventType
from app.models.event import JobEvent


class EventRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def emit(
        self,
        job_id: UUID,
        event_type: JobEventType,
        metadata: dict | None = None,
        idempotency_key: str | None = None,
        domain_event_name: str | None = None,
    ) -> JobEvent:
        stable_key = idempotency_key or f"{job_id}:{event_type}"
        existing = await self.get_by_idempotency_key(job_id, stable_key)
        if existing:
            return existing
        event = JobEvent(
            job_id=job_id,
            event_type=event_type,
            domain_event_name=domain_event_name,
            idempotency_key=stable_key,
            metadata_=metadata or {},
        )
        try:
            async with self.session.begin_nested():
                self.session.add(event)
                await self.session.flush()
            return event
        except IntegrityError:
            existing = await self.get_by_idempotency_key(job_id, stable_key)
            if existing:
                return existing
            raise

    async def publish_domain_event(self, event: DomainEvent, event_type: JobEventType) -> JobEvent:
        return await self.emit(
            job_id=event.job_id,
            event_type=event_type,
            metadata=event.payload,
            idempotency_key=event.stable_key(),
            domain_event_name=event.name,
        )

    async def get_by_idempotency_key(self, job_id: UUID, idempotency_key: str) -> JobEvent | None:
        stmt = select(JobEvent).where(
            JobEvent.job_id == job_id, JobEvent.idempotency_key == idempotency_key
        )
        return await self.session.scalar(stmt)

    async def list_for_job(self, job_id: UUID) -> list[JobEvent]:
        stmt = select(JobEvent).where(JobEvent.job_id == job_id).order_by(JobEvent.timestamp.asc())
        return list((await self.session.scalars(stmt)).all())
