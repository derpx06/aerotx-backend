from app.domain.events import (
    ClassificationCompleted,
    DomainEvent,
    FileUploaded,
    FileValidated,
    JobCompleted,
    JobCreated,
    JobFailed,
    RiskAnalysisCompleted,
    SummaryGenerated,
    TransactionsCleaned,
)
from app.models.enums import JobEventType
from app.repositories.event_repository import EventRepository


EVENT_TYPE_BY_DOMAIN: dict[type[DomainEvent], JobEventType] = {
    JobCreated: JobEventType.JOB_CREATED,
    FileUploaded: JobEventType.FILE_UPLOADED,
    FileValidated: JobEventType.VALIDATION_COMPLETED,
    TransactionsCleaned: JobEventType.CLEANING_COMPLETED,
    RiskAnalysisCompleted: JobEventType.ANOMALY_DETECTION_COMPLETED,
    ClassificationCompleted: JobEventType.CLASSIFICATION_COMPLETED,
    SummaryGenerated: JobEventType.SUMMARY_GENERATION_COMPLETED,
    JobCompleted: JobEventType.JOB_COMPLETED,
    JobFailed: JobEventType.JOB_FAILED,
}


class SqlAlchemyDomainEventPublisher:
    def __init__(self, repository: EventRepository):
        self.repository = repository

    async def publish(self, event: DomainEvent) -> None:
        event_type = EVENT_TYPE_BY_DOMAIN[type(event)]
        await self.repository.publish_domain_event(event, event_type)
