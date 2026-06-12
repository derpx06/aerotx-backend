from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import RiskLevel


class JobSummary(Base):
    __tablename__ = "job_summaries"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    job_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), unique=True, index=True
    )
    total_spend_inr: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    total_spend_usd: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    top_merchants: Mapped[list[dict]] = mapped_column(JSONB, default=list, nullable=False)
    currency_breakdown: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    anomaly_count: Mapped[int] = mapped_column(default=0, nullable=False)
    narrative: Mapped[str | None] = mapped_column(Text)
    risk_level: Mapped[RiskLevel] = mapped_column(String(16), default=RiskLevel.LOW, nullable=False)

    job = relationship("Job", back_populates="summary")
