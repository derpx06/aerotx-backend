from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class RiskSignal(Base):
    __tablename__ = "risk_signals"
    __table_args__ = (
        UniqueConstraint("transaction_id", "signal_type", name="uq_risk_signal_transaction_type"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    transaction_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("transactions.id", ondelete="CASCADE"), index=True
    )
    signal_type: Mapped[str] = mapped_column(String(128), nullable=False)
    signal_score: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    transaction = relationship("Transaction", back_populates="risk_signals")
