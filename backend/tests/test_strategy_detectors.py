from datetime import date
from decimal import Decimal

from app.services.cleaning.engine import CleanTransaction
from app.services.risk.detectors import (
    CurrencyDetector,
    DuplicateDetector,
    MedianDetector,
    NotesDetector,
)


def make_tx(
    txn_id="t1",
    amount="100.00",
    currency="INR",
    merchant="Merchant",
    notes=None,
    account_id="acct-1",
):
    return CleanTransaction(
        txn_id=txn_id,
        date=date(2026, 1, 1),
        merchant=merchant,
        amount=Decimal(amount),
        currency=currency,
        status="COMPLETED",
        category="Shopping",
        account_id=account_id,
        notes=notes,
    )


def test_median_detector_with_precomputed_medians():
    detector = MedianDetector(medians={"acct-1": Decimal("50.00")})
    txs = [
        make_tx(txn_id="t1", amount="40.00"),
        make_tx(txn_id="t2", amount="200.00"),  # > 3x 50.00
    ]
    signals = detector.detect(txs)
    assert len(signals) == 1
    assert signals[0].signal_type == "AMOUNT_OUTLIER"
    assert signals[0].txn_key[0] == "t2"


def test_median_detector_calculates_medians_automatically():
    detector = MedianDetector()
    txs = [
        make_tx(txn_id="t1", amount="50.00"),
        make_tx(txn_id="t2", amount="50.00"),
        make_tx(txn_id="t3", amount="50.00"),
        make_tx(txn_id="t4", amount="200.00"),  # > 3x 50.00
    ]
    signals = detector.detect(txs)
    assert len(signals) == 1
    assert signals[0].signal_type == "AMOUNT_OUTLIER"
    assert signals[0].txn_key[0] == "t4"


def test_currency_detector_flags_usd_domestic():
    detector = CurrencyDetector()
    txs = [
        make_tx(txn_id="t1", currency="USD", merchant="Swiggy Mumbai"),
        make_tx(txn_id="t2", currency="INR", merchant="Swiggy Mumbai"),
        make_tx(txn_id="t3", currency="USD", merchant="Amazon US"),
    ]
    signals = detector.detect(txs)
    assert len(signals) == 1
    assert signals[0].signal_type == "CURRENCY_MISMATCH"
    assert signals[0].txn_key[0] == "t1"


def test_notes_detector_flags_suspicious_notes_and_missing_id():
    detector = NotesDetector()
    txs = [
        make_tx(txn_id="t1", notes="regular spend"),
        make_tx(txn_id="t2", notes="urgent wire transfer"),
        make_tx(txn_id=None, notes="clean transaction"),
    ]
    signals = detector.detect(txs)
    types = [sig.signal_type for sig in signals]
    assert "SUSPICIOUS_NOTE" in types
    assert "MISSING_TXN_ID" in types
    assert len(signals) == 2


def test_duplicate_detector_flags_duplicates():
    detector = DuplicateDetector()
    txs = [
        make_tx(txn_id="t1", amount="100.00"),
        make_tx(txn_id="t2", amount="100.00"),  # duplicate pattern
        make_tx(txn_id="t3", amount="150.00"),
    ]
    signals = detector.detect(txs)
    assert len(signals) == 1
    assert signals[0].signal_type == "DUPLICATE_PATTERN"
    assert signals[0].txn_key[0] == "t2"
