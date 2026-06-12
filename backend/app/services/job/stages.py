from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.domain.events import (
    ClassificationCompleted,
    FileValidated,
    JobCompleted,
    RiskAnalysisCompleted,
    SummaryGenerated,
    TransactionsCleaned,
)
from app.infrastructure.events import SqlAlchemyDomainEventPublisher
from app.infrastructure.storage import get_storage_provider
from app.models.enums import JobEventType, JobStatus
from app.models.risk_signal import RiskSignal
from app.models.transaction import Transaction
from app.repositories.job_repository import JobRepository
from app.repositories.event_repository import EventRepository
from app.repositories.transaction_repository import TransactionRepository
from app.ports.storage import StorageProvider
from app.services.cleaning.engine import (
    CleanTransaction,
    CleaningResult,
    TransactionCleaner,
    chunked,
)
from app.services.llm.classification import ClassificationService
from app.services.observability.events import EventTimeline
from app.services.reporting.service import ReportingService
from app.services.risk.detectors import RiskSignalDTO, StatisticalDetector
from app.services.risk.scoring import RiskEngine
from app.utils.fingerprint import transaction_fingerprint


@dataclass
class PipelineContext:
    job_id: UUID
    session: AsyncSession
    storage: StorageProvider = field(default_factory=get_storage_provider)
    file_path: Path | None = None
    cleaning_result: CleaningResult | None = None
    risk_scores: dict[tuple, tuple[int, str, bool]] = field(default_factory=dict)
    risk_signals: list[RiskSignalDTO] = field(default_factory=list)


class FileValidationStage:
    async def run(self, context: PipelineContext) -> None:
        timeline = EventTimeline(context.session)
        await timeline.emit(context.job_id, JobEventType.VALIDATION_STARTED)
        job = await JobRepository(context.session).get(context.job_id)
        if not job or not job.storage_path:
            raise ValueError("Job or uploaded file was not found")
        if not await context.storage.exists(job.storage_path):
            raise ValueError(f"Uploaded file does not exist: {job.storage_path}")
        path = await context.storage.resolve_local_path(job.storage_path)
        context.file_path = path
        publisher = SqlAlchemyDomainEventPublisher(EventRepository(context.session))
        await publisher.publish(FileValidated(context.job_id, path.stat().st_size))


class CleaningStage:
    async def run(self, context: PipelineContext) -> None:
        timeline = EventTimeline(context.session)
        await timeline.emit(context.job_id, JobEventType.CLEANING_STARTED)
        if not context.file_path:
            raise ValueError("File must be validated before cleaning")
        result = TransactionCleaner().clean_file(context.file_path)
        context.cleaning_result = result
        await JobRepository(context.session).update_counts(
            context.job_id, result.raw_count, result.clean_count
        )
        publisher = SqlAlchemyDomainEventPublisher(EventRepository(context.session))
        await publisher.publish(
            TransactionsCleaned(
                context.job_id,
                raw_count=result.raw_count,
                clean_count=result.clean_count,
                error_count=len(result.errors),
            )
        )


class DeduplicationStage:
    async def run(self, context: PipelineContext) -> None:
        if not context.cleaning_result:
            raise ValueError("Cleaning must complete before deduplication")

        # Deduplication is performed during parsing in TransactionCleaner.
        # This logs the stats of the deduplication.
        import structlog

        structlog.get_logger(__name__).info(
            "deduplication_stage_completed",
            job_id=str(context.job_id),
            raw_count=context.cleaning_result.raw_count,
            clean_count=context.cleaning_result.clean_count,
            duplicates_removed=context.cleaning_result.raw_count
            - context.cleaning_result.clean_count,
        )


class AnomalyDetectionStage:
    async def run(self, context: PipelineContext) -> None:
        timeline = EventTimeline(context.session)
        await timeline.emit(context.job_id, JobEventType.ANOMALY_DETECTION_STARTED)
        if not context.cleaning_result:
            raise ValueError("Cleaning must complete before anomaly detection")
        context.risk_scores, context.risk_signals = RiskEngine().evaluate(
            context.cleaning_result.transactions
        )
        publisher = SqlAlchemyDomainEventPublisher(EventRepository(context.session))
        await publisher.publish(
            RiskAnalysisCompleted(
                context.job_id,
                signal_count=len(context.risk_signals),
                anomaly_count=len(context.risk_scores),
            )
        )


class PersistenceStage:
    async def run(self, context: PipelineContext) -> None:
        if not context.cleaning_result:
            raise ValueError("Cleaning must complete before persistence")
        tx_repo = TransactionRepository(context.session)
        settings = get_settings()

        # Build signals by transaction key
        signals_by_key: dict[tuple, list[RiskSignalDTO]] = {}
        for sig in context.risk_signals:
            if sig.txn_key not in signals_by_key:
                signals_by_key[sig.txn_key] = []
            signals_by_key[sig.txn_key].append(sig)

        model_by_key: dict[tuple, Transaction] = {}
        await tx_repo.delete_for_job(context.job_id)
        for batch in chunked(context.cleaning_result.transactions, settings.csv_batch_size):
            models = [
                self._to_model(
                    context.job_id,
                    tx,
                    context.risk_scores,
                    signals_by_key.get(StatisticalDetector.key(tx), []),
                )
                for tx in batch
            ]
            await tx_repo.bulk_create(models)
            for model in models:
                model_by_key[
                    (
                        model.txn_id,
                        model.date,
                        model.merchant,
                        model.amount,
                        model.currency,
                        model.account_id,
                    )
                ] = model

        signal_models: list[RiskSignal] = []
        for signal in context.risk_signals:
            transaction = model_by_key.get(signal.txn_key)
            if transaction:
                signal_models.append(
                    RiskSignal(
                        transaction_id=transaction.id,
                        signal_type=signal.signal_type,
                        signal_score=signal.signal_score,
                        description=signal.description,
                    )
                )
        if signal_models:
            await tx_repo.add_risk_signals(signal_models)

    def _to_model(
        self,
        job_id: UUID,
        tx: CleanTransaction,
        scores: dict[tuple, tuple[int, str, bool]],
        signals: list[RiskSignalDTO],
    ) -> Transaction:
        score, level, _ = scores.get(StatisticalDetector.key(tx), (0, "LOW", False))

        # Flag transactions where amount exceeds 3x median or domestic USD mismatch
        anomaly_signals = [
            sig for sig in signals if sig.signal_type in ("AMOUNT_OUTLIER", "CURRENCY_MISMATCH")
        ]
        is_anomaly = len(anomaly_signals) > 0
        anomaly_reason = (
            "; ".join(sig.description for sig in anomaly_signals) if is_anomaly else None
        )

        return Transaction(
            job_id=job_id,
            txn_id=tx.txn_id,
            date=tx.date,
            merchant=tx.merchant,
            amount=tx.amount,
            currency=tx.currency,
            status=tx.status,
            category=tx.category,
            account_id=tx.account_id,
            fingerprint=transaction_fingerprint(
                tx.txn_id, tx.date, tx.merchant, tx.amount, tx.currency, tx.account_id
            ),
            notes=tx.notes,
            is_anomaly=is_anomaly,
            anomaly_reason=anomaly_reason,
            risk_score=score,
            risk_level=level,
        )


class ClassificationStage:
    async def run(self, context: PipelineContext) -> bool:
        timeline = EventTimeline(context.session)
        await timeline.emit(context.job_id, JobEventType.CLASSIFICATION_STARTED)
        repo = TransactionRepository(context.session)
        uncategorized_txs = await repo.get_uncategorized_for_job(context.job_id)
        if not uncategorized_txs:
            publisher = SqlAlchemyDomainEventPublisher(EventRepository(context.session))
            await publisher.publish(ClassificationCompleted(context.job_id, True))
            return True

        classifier = ClassificationService()
        llm_success = True
        for batch_start in range(0, len(uncategorized_txs), 500):
            batch = uncategorized_txs[batch_start : batch_start + 500]
            clean_transactions = [
                CleanTransaction(
                    txn_id=tx.txn_id or f"row-{batch_start + idx}",
                    date=tx.date,
                    merchant=tx.merchant,
                    amount=tx.amount,
                    currency=tx.currency,
                    status=tx.status,
                    category=tx.category,
                    account_id=tx.account_id,
                    notes=tx.notes,
                )
                for idx, tx in enumerate(batch)
            ]
            categories, raw_response, batch_success = await classifier.classify_batch(
                clean_transactions
            )
            llm_success = llm_success and batch_success
            for idx, tx in enumerate(batch):
                lookup_id = tx.txn_id or f"row-{batch_start + idx}"
                assigned_category = categories.get(lookup_id)
                if assigned_category:
                    tx.category = assigned_category
                    tx.llm_category = assigned_category
                tx.llm_raw_response = raw_response
                tx.llm_failed = not batch_success
        publisher = SqlAlchemyDomainEventPublisher(EventRepository(context.session))
        await publisher.publish(ClassificationCompleted(context.job_id, llm_success))
        return llm_success


class SummaryGenerationStage:
    async def run(self, context: PipelineContext) -> bool:
        timeline = EventTimeline(context.session)
        await timeline.emit(context.job_id, JobEventType.SUMMARY_GENERATION_STARTED)
        from app.repositories.summary_repository import SummaryRepository

        summary, llm_success = await ReportingService().build_summary(
            context.job_id, session=context.session
        )
        await SummaryRepository(context.session).upsert(summary)
        publisher = SqlAlchemyDomainEventPublisher(EventRepository(context.session))
        await publisher.publish(SummaryGenerated(context.job_id, llm_success))
        return llm_success


class CompletionStage:
    async def run(self, context: PipelineContext) -> None:
        publisher = SqlAlchemyDomainEventPublisher(EventRepository(context.session))
        await publisher.publish(JobCompleted(context.job_id))
        await JobRepository(context.session).set_status(context.job_id, JobStatus.COMPLETED)
