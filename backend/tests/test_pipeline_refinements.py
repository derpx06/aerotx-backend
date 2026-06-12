import sys
from unittest.mock import MagicMock
import types


# Define a DummyBase class for SQLAlchemy models to subclass
class DummyBase:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


# Create a mock database module and populate Base, SessionLocal, and AsyncSession
db_module = types.ModuleType("database")
db_module.Base = DummyBase
db_module.SessionLocal = MagicMock()
db_module.AsyncSession = MagicMock()

# Inject it into sys.modules before any imports
sys.modules["app.core.database"] = db_module
sys.modules["structlog"] = MagicMock()

import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from app.models.enums import RiskLevel, JobStatus, JobEventType
from app.models.transaction import Transaction
from app.services.job.stages import ClassificationStage, PipelineContext
from app.services.llm.summary import SummaryNarrativeService


@pytest.mark.asyncio
async def test_classification_stage_skips_when_no_uncategorized():
    mock_session = AsyncMock()
    context = PipelineContext(job_id=__import__("uuid").uuid4(), session=mock_session)

    with patch(
        "app.repositories.transaction_repository.TransactionRepository.get_uncategorized_for_job",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = []

        with (
            patch(
                "app.services.llm.classification.ClassificationService.classify_batch",
                new_callable=AsyncMock,
            ) as mock_classify,
            patch("app.services.observability.events.EventTimeline.emit", new_callable=AsyncMock),
            patch(
                "app.infrastructure.events.SqlAlchemyDomainEventPublisher.publish",
                new_callable=AsyncMock,
            ),
        ):
            stage = ClassificationStage()
            res = await stage.run(context)

            assert res is True
            mock_classify.assert_not_called()


@pytest.mark.asyncio
async def test_classification_stage_runs_only_on_uncategorized():
    mock_session = AsyncMock()
    context = PipelineContext(job_id=__import__("uuid").uuid4(), session=mock_session)

    tx1 = Transaction(
        txn_id="t1",
        category="Uncategorised",
        date=date(2026, 1, 1),
        merchant="Swiggy",
        amount=Decimal("100"),
        currency="USD",
        status="COMPLETED",
        account_id="acct",
    )
    with patch(
        "app.repositories.transaction_repository.TransactionRepository.get_uncategorized_for_job",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = [tx1]

        with (
            patch(
                "app.services.llm.classification.ClassificationService.classify_batch",
                new_callable=AsyncMock,
            ) as mock_classify,
            patch("app.services.observability.events.EventTimeline.emit", new_callable=AsyncMock),
            patch(
                "app.infrastructure.events.SqlAlchemyDomainEventPublisher.publish",
                new_callable=AsyncMock,
            ),
        ):
            mock_classify.return_value = ({"t1": "Food"}, "raw_resp", True)

            stage = ClassificationStage()
            res = await stage.run(context)

            assert res is True
            mock_classify.assert_called_once()
            called_args = mock_classify.call_args[0][0]
            assert len(called_args) == 1
            assert called_args[0].txn_id == "t1"

            assert tx1.category == "Food"
            assert tx1.llm_category == "Food"
            assert tx1.llm_failed is False
            assert tx1.llm_raw_response == "raw_resp"


@pytest.mark.asyncio
async def test_classification_stage_sets_llm_failed_on_failure():
    mock_session = AsyncMock()
    context = PipelineContext(job_id=__import__("uuid").uuid4(), session=mock_session)

    tx1 = Transaction(
        txn_id="t1",
        category="Uncategorised",
        date=date(2026, 1, 1),
        merchant="Swiggy",
        amount=Decimal("100"),
        currency="USD",
        status="COMPLETED",
        account_id="acct",
    )

    with patch(
        "app.repositories.transaction_repository.TransactionRepository.get_uncategorized_for_job",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = [tx1]

        with (
            patch(
                "app.services.llm.classification.ClassificationService.classify_batch",
                new_callable=AsyncMock,
            ) as mock_classify,
            patch("app.services.observability.events.EventTimeline.emit", new_callable=AsyncMock),
            patch(
                "app.infrastructure.events.SqlAlchemyDomainEventPublisher.publish",
                new_callable=AsyncMock,
            ),
        ):
            mock_classify.return_value = ({"t1": "Other"}, "raw_resp", False)

            stage = ClassificationStage()
            res = await stage.run(context)

            assert res is False
            assert tx1.llm_failed is True
            assert tx1.category == "Other"
            assert tx1.llm_category == "Other"


@pytest.mark.asyncio
async def test_summary_narrative_service_produces_json_summary():
    mock_client = AsyncMock()
    mock_client.generate_json.return_value = (
        '{"narrative": "Spending is normal.", "risk_level": "medium"}',
        True,
    )

    service = SummaryNarrativeService(client=mock_client)
    narrative, risk, success = await service.create_narrative(
        total_spend_inr=Decimal("1000.00"),
        total_spend_usd=Decimal("50.00"),
        anomaly_count=1,
        top_merchants=[{"merchant": "M1", "total": "500.00"}],
        risk_level=RiskLevel.LOW,
    )

    assert success is True
    assert narrative == "Spending is normal."
    assert risk == RiskLevel.MEDIUM


def test_case_insensitive_enum_parsing():
    assert JobStatus("pending") == JobStatus.PENDING
    assert JobStatus("PROCESSING") == JobStatus.PROCESSING
    assert RiskLevel("high") == RiskLevel.HIGH
    assert JobEventType("file_uploaded") == JobEventType.FILE_UPLOADED
