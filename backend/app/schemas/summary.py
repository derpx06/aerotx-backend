from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import RiskLevel
from app.schemas.transaction import TransactionRead


class SummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: UUID
    total_spend_inr: Decimal
    total_spend_usd: Decimal
    top_merchants: list[dict]
    currency_breakdown: dict
    anomaly_count: int
    narrative: str | None
    risk_level: RiskLevel


class JobResultsRead(BaseModel):
    summary: SummaryRead | None
    transactions: list[TransactionRead]
    anomalies: list[TransactionRead] = []
    category_spend: dict[str, dict[str, Decimal]] = {}
    total: int
    limit: int
    offset: int
