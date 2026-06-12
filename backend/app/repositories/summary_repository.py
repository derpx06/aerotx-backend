from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.summary import JobSummary


class SummaryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert(self, summary: JobSummary) -> JobSummary:
        existing = await self.get_by_job(summary.job_id)
        if existing:
            for field in (
                "total_spend_inr",
                "total_spend_usd",
                "top_merchants",
                "currency_breakdown",
                "anomaly_count",
                "narrative",
                "risk_level",
            ):
                setattr(existing, field, getattr(summary, field))
            await self.session.flush()
            return existing
        self.session.add(summary)
        await self.session.flush()
        return summary

    async def get_by_job(self, job_id: UUID) -> JobSummary | None:
        stmt = select(JobSummary).where(JobSummary.job_id == job_id)
        return await self.session.scalar(stmt)
