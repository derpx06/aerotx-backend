from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import JobEventType
from app.repositories.event_repository import EventRepository

log = structlog.get_logger(__name__)


class EventTimeline:
    def __init__(self, session: AsyncSession):
        self.repository = EventRepository(session)

    async def emit(
        self, job_id: UUID, event_type: JobEventType, metadata: dict | None = None
    ) -> None:
        await self.repository.emit(job_id, event_type, metadata)
        log.info(
            "job_event_emitted", job_id=str(job_id), event_type=event_type, metadata=metadata or {}
        )
