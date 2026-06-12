import json

import pytest

from app.infrastructure.resilience.circuit_breaker import CircuitBreaker, CircuitState
from app.infrastructure.storage.local import LocalStorageProvider
from app.services.llm.classification import ClassificationService
from app.services.llm.response_validator import ResponseValidator
from app.utils.fingerprint import transaction_fingerprint


class BadLLMClient:
    async def generate_json(self, prompt, fallback, validator=None):
        return "not-json", True


class FakeUpload:
    def __init__(self, chunks):
        self.chunks = list(chunks)

    async def read(self, size):
        if not self.chunks:
            return b""
        return self.chunks.pop(0)


def test_circuit_breaker_opens_after_threshold():
    breaker = CircuitBreaker(failure_threshold=2)

    breaker.record_failure()
    assert breaker.state == CircuitState.CLOSED

    breaker.record_failure()
    assert breaker.state == CircuitState.OPEN
    assert breaker.allow_request() is False


def test_transaction_fingerprint_is_stable():
    first = transaction_fingerprint(
        None, __import__("datetime").date(2026, 1, 1), " Amazon ", 10, "inr", "Acct"
    )
    second = transaction_fingerprint(
        None, __import__("datetime").date(2026, 1, 1), "amazon", 10, "INR", "acct"
    )

    assert first == second


@pytest.mark.asyncio
async def test_local_storage_provider_writes_upload(tmp_path):
    provider = LocalStorageProvider(str(tmp_path))

    async def chunks():
        yield b"a,b\n"
        yield b"1,2\n"

    stored = await provider.save_upload("sample.csv", chunks())

    assert stored.bytes_written == 8
    assert await provider.exists(stored.key)
    assert (await provider.resolve_local_path(stored.key)).read_text() == "a,b\n1,2\n"


@pytest.mark.asyncio
async def test_classification_falls_back_on_invalid_llm_json():
    from datetime import date
    from decimal import Decimal

    from app.services.cleaning.engine import CleanTransaction

    service = ClassificationService(client=BadLLMClient(), validator=ResponseValidator())
    categories, raw, success = await service.classify_batch(
        [
            CleanTransaction(
                txn_id="t1",
                date=date(2026, 1, 1),
                merchant="Amazon",
                amount=Decimal("10"),
                currency="INR",
                status="COMPLETED",
                category="Uncategorised",
                account_id="acct",
            )
        ]
    )

    assert success is False
    assert categories["t1"] == "Shopping"
    assert json.loads(raw)["categories"]["t1"] == "Shopping"


def test_opentelemetry_initialization():
    from app.services.observability.tracing import get_tracer, init_tracer

    tracer = init_tracer()
    assert tracer is not None
    assert get_tracer() is not None
