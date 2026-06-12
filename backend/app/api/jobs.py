from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.domain.events import FileUploaded, JobCreated
from app.infrastructure.events import SqlAlchemyDomainEventPublisher
from app.infrastructure.storage import get_storage_provider
from app.models.enums import JobStatus
from app.repositories.event_repository import EventRepository
from app.repositories.job_repository import JobRepository
from app.repositories.summary_repository import SummaryRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.job import JobCreateResponse, JobEventRead, JobRead, JobStatusRead
from app.schemas.summary import JobResultsRead
from app.services.upload.service import UploadService
from app.tasks.pipeline_tasks import run_processing_pipeline

from pydantic import BaseModel
from app.schemas.transaction import TransactionRead

class GlobalTransactionsRead(BaseModel):
    items: list[TransactionRead]
    total: int
    limit: int
    offset: int

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/upload", response_model=JobCreateResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_job(
    file: UploadFile = File(...), session: AsyncSession = Depends(get_session)
) -> JobCreateResponse:
    repo = JobRepository(session)
    stored = await UploadService(get_storage_provider()).store(file)
    existing = await repo.get_by_checksum(stored.checksum)
    if existing:
        return JobCreateResponse(id=existing.id, filename=existing.filename, status=existing.status)

    job = await repo.create(
        filename=file.filename or "transactions.csv",
        storage_path=stored.key,
        file_checksum=stored.checksum,
    )
    publisher = SqlAlchemyDomainEventPublisher(EventRepository(session))
    await publisher.publish(JobCreated(job.id, job.filename))
    await publisher.publish(FileUploaded(job.id, stored.bytes_written, stored.checksum))
    await session.commit()

    run_processing_pipeline.apply_async(args=[str(job.id)], queue="processing_queue")
    return JobCreateResponse(id=job.id, filename=job.filename, status=job.status)


@router.get("", response_model=list[JobRead])
async def list_jobs(
    status_filter: JobStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list:
    return await JobRepository(session).list(status=status_filter, limit=limit, offset=offset)


@router.get("/global/analytics")
async def get_global_analytics(
    session: AsyncSession = Depends(get_session)
):
    repo = TransactionRepository(session)
    return await repo.get_global_analytics()


@router.get("/global/transactions", response_model=GlobalTransactionsRead)
async def get_global_transactions(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None),
    category: str | None = Query(default=None),
    currency: str | None = Query(default=None),
    risk_level: str | None = Query(default=None),
    min_amount: float | None = Query(default=None),
    max_amount: float | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> GlobalTransactionsRead:
    repo = TransactionRepository(session)
    items = await repo.list_global(
        limit=limit,
        offset=offset,
        search=search,
        category=category,
        currency=currency,
        risk_level=risk_level,
        min_amount=min_amount,
        max_amount=max_amount,
    )
    total = await repo.count_global(
        search=search,
        category=category,
        currency=currency,
        risk_level=risk_level,
        min_amount=min_amount,
        max_amount=max_amount,
    )
    return GlobalTransactionsRead(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{job_id}", response_model=JobRead)
async def get_job(job_id: UUID, session: AsyncSession = Depends(get_session)):
    job = await JobRepository(session).get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/{job_id}/status", response_model=JobStatusRead)
async def get_job_status(
    job_id: UUID, session: AsyncSession = Depends(get_session)
) -> JobStatusRead:
    job = await JobRepository(session).get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    summary = None
    if job.status == JobStatus.COMPLETED:
        summary = await SummaryRepository(session).get_by_job(job_id)
    return JobStatusRead(
        id=job.id, status=job.status, error_message=job.error_message, summary=summary
    )


@router.get("/{job_id}/results", response_model=JobResultsRead)
async def get_job_results(
    job_id: UUID,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> JobResultsRead:
    job = await JobRepository(session).get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    summary = await SummaryRepository(session).get_by_job(job_id)
    tx_repo = TransactionRepository(session)

    # Fetch database-aggregated category spend
    category_spend_rows = await tx_repo.get_category_spend_for_job(job_id)
    category_spend = {}
    for cat, curr, total_amt in category_spend_rows:
        if cat not in category_spend:
            category_spend[cat] = {}
        category_spend[cat][curr] = total_amt

    # Fetch only flagged anomalies from database
    anomalies = await tx_repo.get_anomalies_for_job(job_id)

    # Fetch the requested page of transactions
    transactions = await tx_repo.list_for_job(job_id, limit=limit, offset=offset)
    total = await tx_repo.count_for_job(job_id)

    return JobResultsRead(
        summary=summary,
        transactions=transactions,
        anomalies=anomalies,
        category_spend=category_spend,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{job_id}/timeline", response_model=list[JobEventRead])
async def get_job_timeline(job_id: UUID, session: AsyncSession = Depends(get_session)):
    if not await JobRepository(session).get(job_id):
        raise HTTPException(status_code=404, detail="Job not found")
    return await EventRepository(session).list_for_job(job_id)
