from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.risk_signal import RiskSignal
from app.models.transaction import Transaction
from app.models.enums import RiskLevel


class TransactionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def bulk_create(self, transactions: list[Transaction]) -> None:
        self.session.add_all(transactions)
        await self.session.flush()

    async def add_risk_signals(self, signals: list[RiskSignal]) -> None:
        self.session.add_all(signals)
        await self.session.flush()

    async def delete_for_job(self, job_id: UUID) -> None:
        await self.session.execute(delete(Transaction).where(Transaction.job_id == job_id))

    async def list_for_job(
        self, job_id: UUID, limit: int = 100, offset: int = 0
    ) -> list[Transaction]:
        stmt = (
            select(Transaction)
            .where(Transaction.job_id == job_id)
            .options(selectinload(Transaction.risk_signals))
            .order_by(Transaction.date.asc(), Transaction.id.asc())
            .limit(limit)
            .offset(offset)
        )
        return list((await self.session.scalars(stmt)).all())

    async def count_for_job(self, job_id: UUID) -> int:
        stmt = select(func.count()).select_from(Transaction).where(Transaction.job_id == job_id)
        return int((await self.session.scalar(stmt)) or 0)

    async def all_for_job(self, job_id: UUID) -> list[Transaction]:
        stmt = select(Transaction).where(Transaction.job_id == job_id)
        return list((await self.session.scalars(stmt)).all())

    async def get_uncategorized_for_job(self, job_id: UUID) -> list[Transaction]:
        stmt = select(Transaction).where(
            Transaction.job_id == job_id, Transaction.category == "Uncategorised"
        )
        return list((await self.session.scalars(stmt)).all())

    async def get_anomalies_for_job(self, job_id: UUID) -> list[Transaction]:
        stmt = (
            select(Transaction)
            .where(Transaction.job_id == job_id, Transaction.is_anomaly)
            .options(selectinload(Transaction.risk_signals))
            .order_by(Transaction.date.asc(), Transaction.id.asc())
        )
        return list((await self.session.scalars(stmt)).all())

    async def get_category_spend_for_job(self, job_id: UUID) -> list[tuple]:
        stmt = (
            select(Transaction.category, Transaction.currency, func.sum(Transaction.amount))
            .where(Transaction.job_id == job_id)
            .group_by(Transaction.category, Transaction.currency)
        )
        result = await self.session.execute(stmt)
        return list(result.all())

    async def get_summary_aggregates(self, job_id: UUID) -> dict[str, Any]:
        # 1. Total spend by currency
        spend_stmt = (
            select(Transaction.currency, func.sum(Transaction.amount))
            .where(Transaction.job_id == job_id)
            .group_by(Transaction.currency)
        )
        spend_res = await self.session.execute(spend_stmt)
        total_by_currency = {curr: amt for curr, amt in spend_res.all()}

        # 2. Top 3 merchants by spend
        merchant_stmt = (
            select(Transaction.merchant, func.sum(Transaction.amount))
            .where(Transaction.job_id == job_id)
            .group_by(Transaction.merchant)
            .order_by(func.sum(Transaction.amount).desc())
            .limit(3)
        )
        merchant_res = await self.session.execute(merchant_stmt)
        top_merchants = [
            {"merchant": merch, "total": str(amt)} for merch, amt in merchant_res.all()
        ]

        # 3. Anomaly count
        anomaly_stmt = (
            select(func.count())
            .select_from(Transaction)
            .where(Transaction.job_id == job_id, Transaction.is_anomaly)
        )
        anomaly_count = int((await self.session.scalar(anomaly_stmt)) or 0)

        # 4. Max risk score
        max_score_stmt = (
            select(func.max(Transaction.risk_score))
            .select_from(Transaction)
            .where(Transaction.job_id == job_id)
        )
        max_score = int((await self.session.scalar(max_score_stmt)) or 0)

        return {
            "total_by_currency": total_by_currency,
            "top_merchants": top_merchants,
            "anomaly_count": anomaly_count,
            "max_score": max_score,
        }

    async def list_global(
        self,
        limit: int = 100,
        offset: int = 0,
        search: str | None = None,
        category: str | None = None,
        currency: str | None = None,
        risk_level: str | None = None,
        min_amount: float | None = None,
        max_amount: float | None = None,
    ) -> list[Transaction]:
        stmt = select(Transaction).options(selectinload(Transaction.risk_signals))
        stmt = self._apply_global_filters(stmt, search, category, currency, risk_level, min_amount, max_amount)
        stmt = stmt.order_by(Transaction.date.desc(), Transaction.created_at.desc(), Transaction.id.desc()).limit(limit).offset(offset)
        return list((await self.session.scalars(stmt)).all())

    async def count_global(
        self,
        search: str | None = None,
        category: str | None = None,
        currency: str | None = None,
        risk_level: str | None = None,
        min_amount: float | None = None,
        max_amount: float | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(Transaction)
        stmt = self._apply_global_filters(stmt, search, category, currency, risk_level, min_amount, max_amount)
        return int((await self.session.scalar(stmt)) or 0)

    def _apply_global_filters(
        self,
        stmt,
        search: str | None = None,
        category: str | None = None,
        currency: str | None = None,
        risk_level: str | None = None,
        min_amount: float | None = None,
        max_amount: float | None = None,
    ):
        from sqlalchemy import or_
        if search:
            search_clause = or_(
                Transaction.merchant.ilike(f"%{search}%"),
                Transaction.category.ilike(f"%{search}%"),
                Transaction.notes.ilike(f"%{search}%"),
                Transaction.txn_id.ilike(f"%{search}%"),
            )
            stmt = stmt.where(search_clause)
        if category:
            stmt = stmt.where(Transaction.category == category)
        if currency:
            stmt = stmt.where(Transaction.currency == currency.upper())
        if risk_level:
            try:
                rl = RiskLevel(risk_level.upper())
                stmt = stmt.where(Transaction.risk_level == rl)
            except ValueError:
                pass
        if min_amount is not None:
            stmt = stmt.where(Transaction.amount >= min_amount)
        if max_amount is not None:
            stmt = stmt.where(Transaction.amount <= max_amount)
        return stmt

    async def get_global_analytics(self) -> dict[str, Any]:
        # 1. Spend by Category
        cat_stmt = select(Transaction.category, Transaction.currency, func.sum(Transaction.amount)).group_by(Transaction.category, Transaction.currency)
        cat_res = await self.session.execute(cat_stmt)
        category_spend = {}
        for cat, curr, total_amt in cat_res.all():
            if cat not in category_spend:
                category_spend[cat] = {}
            category_spend[cat][curr] = float(total_amt or 0)

        # 2. Spend by Currency
        curr_stmt = select(Transaction.currency, func.sum(Transaction.amount)).group_by(Transaction.currency)
        curr_res = await self.session.execute(curr_stmt)
        currency_spend = {curr: float(amt or 0) for curr, amt in curr_res.all()}

        # 3. Top Merchants
        merch_stmt = select(Transaction.merchant, Transaction.currency, func.sum(Transaction.amount)).group_by(Transaction.merchant, Transaction.currency).order_by(func.sum(Transaction.amount).desc()).limit(10)
        merch_res = await self.session.execute(merch_stmt)
        top_merchants = [{"merchant": merch, "currency": curr, "total": float(amt or 0)} for merch, curr, amt in merch_res.all()]

        # 4. Risk Levels
        risk_stmt = select(Transaction.risk_level, func.count()).group_by(Transaction.risk_level)
        risk_res = await self.session.execute(risk_stmt)
        risk_levels = {str(level): count for level, count in risk_res.all()}

        # 5. Anomalies count
        anomaly_stmt = select(Transaction.is_anomaly, func.count()).group_by(Transaction.is_anomaly)
        anomaly_res = await self.session.execute(anomaly_stmt)
        anomalies = {str(is_anom): count for is_anom, count in anomaly_res.all()}

        # 6. Trend by Date
        trend_stmt = select(Transaction.date, func.count(), func.sum(Transaction.amount)).group_by(Transaction.date).order_by(Transaction.date.asc()).limit(30)
        trend_res = await self.session.execute(trend_stmt)
        trend = [{"date": str(d), "count": cnt, "amount": float(amt or 0)} for d, cnt, amt in trend_res.all()]

        return {
            "category_spend": category_spend,
            "currency_spend": currency_spend,
            "top_merchants": top_merchants,
            "risk_levels": risk_levels,
            "anomalies": anomalies,
            "trend": trend,
        }
