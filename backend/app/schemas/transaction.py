from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import RiskLevel


class RiskSignalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    signal_type: str
    signal_score: float
    description: str


class TransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    txn_id: str | None
    date: date
    merchant: str
    amount: Decimal
    currency: str
    status: str
    category: str
    account_id: str
    is_anomaly: bool
    anomaly_reason: str | None = None
    risk_score: int
    risk_level: RiskLevel
    llm_category: str | None = None
    llm_failed: bool = False
    risk_signals: list[RiskSignalRead] = []
