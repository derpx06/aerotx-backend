from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import JobStatus
from app.models.job import Job
from app.models.risk_signal import RiskSignal
from app.models.transaction import Transaction


class MetricsService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def snapshot(self) -> dict:
        jobs_processed = await self.session.scalar(
            select(func.count()).select_from(Job).where(Job.status == JobStatus.COMPLETED)
        )
        failed_jobs = await self.session.scalar(
            select(func.count()).select_from(Job).where(Job.status == JobStatus.FAILED)
        )
        in_progress = await self.session.scalar(
            select(func.count())
            .select_from(Job)
            .where(
                Job.status.in_(
                    [
                        JobStatus.PENDING,
                        JobStatus.PROCESSING,
                        JobStatus.LLM_PROCESSING,
                        JobStatus.REPORTING,
                    ]
                )
            )
        )
        llm_failed = await self.session.scalar(
            select(func.count()).select_from(Job).where(Job.llm_failed.is_(True))
        )
        total_jobs = await self.session.scalar(select(func.count()).select_from(Job))
        risk_signal_count = await self.session.scalar(select(func.count()).select_from(RiskSignal))
        anomaly_count = await self.session.scalar(
            select(func.count()).select_from(Transaction).where(Transaction.is_anomaly.is_(True))
        )
        transaction_count = await self.session.scalar(select(func.count()).select_from(Transaction))
        avg_seconds = await self.session.scalar(
            select(func.avg(func.extract("epoch", Job.completed_at - Job.started_at))).where(
                Job.started_at.is_not(None), Job.completed_at.is_not(None)
            )
        )

        total_jobs = int(total_jobs or 0)
        transaction_count = int(transaction_count or 0)
        anomaly_count = int(anomaly_count or 0)
        llm_success_rate = Decimal("1.0")
        if total_jobs:
            llm_success_rate = Decimal(total_jobs - int(llm_failed or 0)) / Decimal(total_jobs)

        return {
            "jobs_processed_total": int(jobs_processed or 0),
            "jobs_failed_total": int(failed_jobs or 0),
            "jobs_in_progress": int(in_progress or 0),
            "average_processing_time": float(avg_seconds or 0),
            "llm_success_rate": float(llm_success_rate),
            "llm_failure_rate": float(1 - llm_success_rate),
            "anomaly_rate": anomaly_count / transaction_count if transaction_count else 0,
            "queue_depth": {"processing_queue": None, "llm_queue": None, "reporting_queue": None},
            "worker_utilization": "see Flower dashboard at /flower",
            "risk_signal_count": int(risk_signal_count or 0),
        }
