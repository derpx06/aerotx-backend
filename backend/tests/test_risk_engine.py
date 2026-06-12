from datetime import date
from decimal import Decimal

from app.models.enums import RiskLevel
from app.services.cleaning.engine import CleanTransaction
from app.services.risk.scoring import RiskEngine


def tx(
    amount: str, merchant: str = "Amazon India", txn_id: str | None = "t1", notes: str | None = None
):
    return CleanTransaction(
        txn_id=txn_id,
        date=date(2026, 1, 1),
        merchant=merchant,
        amount=Decimal(amount),
        currency="USD",
        status="COMPLETED",
        category="Shopping",
        account_id="acct-1",
        notes=notes,
    )


def test_risk_engine_scores_combined_signals_as_high_risk():
    transactions = [
        tx("100", "Local Store", txn_id="t1"),
        tx("110", "Local Store", txn_id="t2"),
        tx("120", "Local Store", txn_id="t3"),
        tx("5000", txn_id="t4", notes="urgent wire"),
    ]

    scores, signals = RiskEngine().evaluate(transactions)
    high_risk = max(scores.values(), key=lambda item: item[0])

    assert len(signals) >= 3
    assert high_risk[0] >= 60
    assert high_risk[1] == RiskLevel.HIGH
    assert high_risk[2] is True


def test_missing_transaction_id_is_low_risk_signal():
    scores, signals = RiskEngine().evaluate([tx("100", txn_id=None, merchant="Global Merchant")])

    assert signals[0].signal_type == "MISSING_TXN_ID"
    assert next(iter(scores.values()))[1] == RiskLevel.LOW


def test_domestic_merchants_usd_trigger_mismatch():
    engine = RiskEngine()

    tx_swiggy = CleanTransaction(
        txn_id="t1",
        date=date(2026, 1, 1),
        merchant="Swiggy",
        amount=Decimal("100"),
        currency="USD",
        status="COMPLETED",
        category="Food",
        account_id="acct-1",
    )
    tx_ola = CleanTransaction(
        txn_id="t2",
        date=date(2026, 1, 1),
        merchant="Ola Cab",
        amount=Decimal("150"),
        currency="USD",
        status="COMPLETED",
        category="Transport",
        account_id="acct-1",
    )
    tx_irctc = CleanTransaction(
        txn_id="t3",
        date=date(2026, 1, 1),
        merchant="IRCTC Ticket",
        amount=Decimal("200"),
        currency="USD",
        status="COMPLETED",
        category="Travel",
        account_id="acct-1",
    )

    _, signals = engine.evaluate([tx_swiggy, tx_ola, tx_irctc])

    mismatches = [sig for sig in signals if sig.signal_type == "CURRENCY_MISMATCH"]
    assert len(mismatches) == 3
