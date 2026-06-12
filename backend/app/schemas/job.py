from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import JobEventType, JobStatus
from app.schemas.summary import SummaryRead


class JobCreateResponse(BaseModel):
    id: UUID
    filename: str
    status: JobStatus


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    status: JobStatus
    row_count_raw: int
    row_count_clean: int
    error_message: str | None
    llm_failed: bool
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class JobStatusRead(BaseModel):
    id: UUID
    status: JobStatus
    error_message: str | None = None
    summary: SummaryRead | None = None


class JobEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    job_id: UUID
    event_type: JobEventType
    domain_event_name: str | None
    timestamp: datetime
    metadata: dict = Field(validation_alias="metadata_", serialization_alias="metadata")
