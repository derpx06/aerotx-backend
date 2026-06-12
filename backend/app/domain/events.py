from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass(frozen=True)
class DomainEvent:
    job_id: UUID
    name: str
    payload: dict = field(default_factory=dict)
    idempotency_key: str | None = None
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def stable_key(self) -> str:
        return self.idempotency_key or f"{self.job_id}:{self.name}:{self.event_id}"


class JobCreated(DomainEvent):
    def __init__(self, job_id: UUID, filename: str):
        super().__init__(
            job_id=job_id,
            name="JobCreated",
            payload={"filename": filename},
            idempotency_key=f"{job_id}:job-created",
        )


class FileUploaded(DomainEvent):
    def __init__(self, job_id: UUID, bytes_written: int, checksum: str):
        super().__init__(
            job_id=job_id,
            name="FileUploaded",
            payload={"bytes": bytes_written, "checksum": checksum},
            idempotency_key=f"{job_id}:file-uploaded",
        )


class FileValidated(DomainEvent):
    def __init__(self, job_id: UUID, bytes_validated: int):
        super().__init__(
            job_id=job_id,
            name="FileValidated",
            payload={"bytes": bytes_validated},
            idempotency_key=f"{job_id}:file-validated",
        )


class TransactionsCleaned(DomainEvent):
    def __init__(self, job_id: UUID, raw_count: int, clean_count: int, error_count: int):
        super().__init__(
            job_id=job_id,
            name="TransactionsCleaned",
            payload={
                "raw_count": raw_count,
                "clean_count": clean_count,
                "error_count": error_count,
            },
            idempotency_key=f"{job_id}:transactions-cleaned",
        )


class RiskAnalysisCompleted(DomainEvent):
    def __init__(self, job_id: UUID, signal_count: int, anomaly_count: int):
        super().__init__(
            job_id=job_id,
            name="RiskAnalysisCompleted",
            payload={"signal_count": signal_count, "anomaly_count": anomaly_count},
            idempotency_key=f"{job_id}:risk-analysis-completed",
        )


class ClassificationCompleted(DomainEvent):
    def __init__(self, job_id: UUID, llm_success: bool):
        super().__init__(
            job_id=job_id,
            name="ClassificationCompleted",
            payload={"llm_success": llm_success},
            idempotency_key=f"{job_id}:classification-completed",
        )


class SummaryGenerated(DomainEvent):
    def __init__(self, job_id: UUID, llm_success: bool):
        super().__init__(
            job_id=job_id,
            name="SummaryGenerated",
            payload={"llm_success": llm_success},
            idempotency_key=f"{job_id}:summary-generated",
        )


class JobCompleted(DomainEvent):
    def __init__(self, job_id: UUID):
        super().__init__(
            job_id=job_id,
            name="JobCompleted",
            payload={},
            idempotency_key=f"{job_id}:job-completed",
        )


class JobFailed(DomainEvent):
    def __init__(self, job_id: UUID, error: str, phase: str):
        super().__init__(
            job_id=job_id,
            name="JobFailed",
            payload={"error": error, "phase": phase},
            idempotency_key=f"{job_id}:job-failed:{phase}",
        )
