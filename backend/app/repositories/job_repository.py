from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import JobStatus
from app.models.job import Job


class JobRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        filename: str,
        storage_path: str | None = None,
        file_checksum: str | None = None,
    ) -> Job:
        job = Job(filename=filename, storage_path=storage_path, file_checksum=file_checksum)
        self.session.add(job)
        await self.session.flush()
        return job

    async def get(self, job_id: UUID) -> Job | None:
        return await self.session.get(Job, job_id)

    async def get_by_checksum(self, file_checksum: str) -> Job | None:
        stmt = (
            select(Job)
            .where(Job.file_checksum == file_checksum)
            .order_by(Job.created_at.desc())
            .limit(1)
        )
        return await self.session.scalar(stmt)

    async def list(
        self,
        status: JobStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Job]:
        stmt = select(Job).order_by(Job.created_at.desc()).limit(limit).offset(offset)
        if status:
            stmt = stmt.where(Job.status == status)
        return list((await self.session.scalars(stmt)).all())

    async def count(self, status: JobStatus | None = None) -> int:
        stmt = select(func.count()).select_from(Job)
        if status:
            stmt = stmt.where(Job.status == status)
        return int((await self.session.scalar(stmt)) or 0)

    async def mark_started(self, job_id: UUID, status: JobStatus = JobStatus.PROCESSING) -> None:
        await self.session.execute(
            update(Job)
            .where(Job.id == job_id)
            .values(status=status, started_at=datetime.now(UTC), error_message=None)
        )

    async def claim_status_transition(
        self,
        job_id: UUID,
        expected_statuses: set[JobStatus],
        next_status: JobStatus,
        mark_started: bool = False,
    ) -> bool:
        values: dict = {"status": next_status, "error_message": None}
        if mark_started:
            values["started_at"] = datetime.now(UTC)
        result = await self.session.execute(
            update(Job)
            .where(Job.id == job_id, Job.status.in_(expected_statuses))
            .values(**values)
            .execution_options(synchronize_session=False)
        )
        return bool(result.rowcount)

    async def update_counts(self, job_id: UUID, raw_count: int, clean_count: int) -> None:
        await self.session.execute(
            update(Job)
            .where(Job.id == job_id)
            .values(row_count_raw=raw_count, row_count_clean=clean_count)
        )

    async def set_status(
        self, job_id: UUID, status: JobStatus, error_message: str | None = None
    ) -> None:
        values: dict = {"status": status, "error_message": error_message}
        if status in {JobStatus.COMPLETED, JobStatus.FAILED}:
            values["completed_at"] = datetime.now(UTC)
        await self.session.execute(update(Job).where(Job.id == job_id).values(**values))

    async def mark_llm_failed(self, job_id: UUID) -> None:
        await self.session.execute(update(Job).where(Job.id == job_id).values(llm_failed=True))
