from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import RiskLevel
from app.models.summary import JobSummary
from app.models.transaction import Transaction
from app.services.llm.summary import SummaryNarrativeService


class ReportingService:
    def __init__(self, narrative_service: SummaryNarrativeService | None = None):
        self.narrative_service = narrative_service or SummaryNarrativeService()

    async def build_summary(
        self,
        job_id: UUID,
        transactions: list[Transaction] | None = None,
        session: AsyncSession | None = None,
    ) -> tuple[JobSummary, bool]:
        if session is not None:
            from app.repositories.transaction_repository import TransactionRepository

            tx_repo = TransactionRepository(session)
            aggs = await tx_repo.get_summary_aggregates(job_id)
            total_by_currency = aggs["total_by_currency"]
            top_merchants = aggs["top_merchants"]
            anomaly_count = aggs["anomaly_count"]
            max_score = aggs["max_score"]
        else:
            # Fallback to in-memory aggregation for tests or cases without session
            from collections import Counter, defaultdict

            txs = transactions or []
            total_by_currency = defaultdict(lambda: Decimal("0.00"))
            merchant_totals = Counter()
            anomaly_count = 0
            max_score = 0
            for tx in txs:
                total_by_currency[tx.currency] += tx.amount
                merchant_totals[tx.merchant] += tx.amount
                anomaly_count += int(tx.is_anomaly)
                max_score = max(max_score, tx.risk_score)
            top_merchants = [
                {"merchant": merchant, "total": str(total)}
                for merchant, total in merchant_totals.most_common(3)
            ]

        total_spend_inr = total_by_currency.get("INR", Decimal("0.00"))
        total_spend_usd = total_by_currency.get("USD", Decimal("0.00"))

        risk_level = self._overall_risk(max_score, anomaly_count)
        narrative, llm_risk_level, llm_success = await self.narrative_service.create_narrative(
            total_spend_inr=total_spend_inr,
            total_spend_usd=total_spend_usd,
            anomaly_count=anomaly_count,
            top_merchants=top_merchants,
            risk_level=risk_level,
        )
        if llm_success:
            risk_level = llm_risk_level

        return (
            JobSummary(
                job_id=job_id,
                total_spend_inr=total_spend_inr,
                total_spend_usd=total_spend_usd,
                top_merchants=top_merchants,
                currency_breakdown={
                    currency: str(total) for currency, total in total_by_currency.items()
                },
                anomaly_count=anomaly_count,
                narrative=narrative,
                risk_level=risk_level,
            ),
            llm_success,
        )

    def _overall_risk(self, max_score: int, anomaly_count: int) -> RiskLevel:
        if max_score >= 60 or anomaly_count >= 10:
            return RiskLevel.HIGH
        if max_score >= 30 or anomaly_count > 0:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW
