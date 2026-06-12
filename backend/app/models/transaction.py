from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import RiskLevel

if TYPE_CHECKING:
    from app.models.job import Job
    from app.models.risk_signal import RiskSignal


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_transactions_job_id", "job_id"),
        Index("ix_transactions_account_id", "account_id"),
        Index("ix_transactions_merchant", "merchant"),
        UniqueConstraint("job_id", "fingerprint", name="uq_transactions_job_fingerprint"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    job_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE")
    )
    txn_id: Mapped[str | None] = mapped_column(String(255))
    date: Mapped[date] = mapped_column(Date, nullable=False)
    merchant: Mapped[str] = mapped_column(String(512), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str] = mapped_column(String(255), nullable=False)
    account_id: Mapped[str] = mapped_column(String(255), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    is_anomaly: Mapped[bool] = mapped_column(default=False, nullable=False)
    anomaly_reason: Mapped[str | None] = mapped_column(Text)
    risk_score: Mapped[int] = mapped_column(default=0, nullable=False)
    risk_level: Mapped[RiskLevel] = mapped_column(String(16), default=RiskLevel.LOW, nullable=False)
    llm_category: Mapped[str | None] = mapped_column(String(255))
    llm_raw_response: Mapped[str | None] = mapped_column(Text)
    llm_failed: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    job: Mapped["Job"] = relationship(back_populates="transactions")
    risk_signals: Mapped[list["RiskSignal"]] = relationship(
        back_populates="transaction", cascade="all, delete-orphan"
    )
