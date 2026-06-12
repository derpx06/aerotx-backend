from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import JobStatus

if TYPE_CHECKING:
    from app.models.event import JobEvent
    from app.models.summary import JobSummary
    from app.models.transaction import Transaction


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        Index("ix_jobs_status", "status"),
        Index("ix_jobs_created_at", "created_at"),
        Index("ix_jobs_file_checksum", "file_checksum"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    storage_path: Mapped[str | None] = mapped_column(String(1024))
    file_checksum: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus), nullable=False, default=JobStatus.PENDING
    )
    row_count_raw: Mapped[int] = mapped_column(default=0)
    row_count_clean: Mapped[int] = mapped_column(default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    llm_failed: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    events: Mapped[list["JobEvent"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    summary: Mapped["JobSummary | None"] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
