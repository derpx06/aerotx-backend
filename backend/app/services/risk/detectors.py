from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from statistics import median
from typing import Protocol

from app.services.cleaning.engine import CleanTransaction


@dataclass(frozen=True)
class RiskSignalDTO:
    txn_key: tuple
    signal_type: str
    signal_score: int
    description: str


class RiskDetector(Protocol):
    def detect(self, transactions: list[CleanTransaction]) -> list[RiskSignalDTO]:
        """Detect risk signals in a list of transactions."""
        ...


class MedianDetector:
    def __init__(self, medians: dict[str, Decimal] | None = None) -> None:
        self.medians = medians

    def detect(self, transactions: list[CleanTransaction]) -> list[RiskSignalDTO]:
        medians = self.medians
        if medians is None:
            by_account: dict[str, list[Decimal]] = defaultdict(list)
            for tx in transactions:
                by_account[tx.account_id].append(abs(tx.amount))
            medians = {
                account: median(amounts)
                for account, amounts in by_account.items()
                if amounts and median(amounts) > Decimal("0")
            }

        signals: list[RiskSignalDTO] = []
        for tx in transactions:
            account_median = medians.get(tx.account_id)
            if account_median and abs(tx.amount) > account_median * 3:
                signals.append(
                    RiskSignalDTO(
                        txn_key=self.key(tx),
                        signal_type="AMOUNT_OUTLIER",
                        signal_score=40,
                        description=f"Amount exceeds 3x account median ({account_median})",
                    )
                )
        return signals

    @staticmethod
    def key(tx: CleanTransaction) -> tuple:
        return (tx.txn_id, tx.date, tx.merchant, tx.amount, tx.currency, tx.account_id)


class CurrencyDetector:
    def detect(self, transactions: list[CleanTransaction]) -> list[RiskSignalDTO]:
        signals: list[RiskSignalDTO] = []
        for tx in transactions:
            if tx.currency == "USD" and self._looks_domestic(tx.merchant):
                signals.append(
                    RiskSignalDTO(
                        MedianDetector.key(tx),
                        "CURRENCY_MISMATCH",
                        30,
                        "Domestic-looking merchant charged in USD",
                    )
                )
        return signals

    def _looks_domestic(self, merchant: str) -> bool:
        text = merchant.lower()
        return any(
            marker in text
            for marker in (
                "india",
                "bharat",
                "upi",
                "mumbai",
                "delhi",
                "bangalore",
                "swiggy",
                "ola",
                "irctc",
                "zomato",
                "makemytrip",
            )
        )


class NotesDetector:
    suspicious_terms = {
        "urgent",
        "wire",
        "crypto",
        "gift card",
        "refund reversal",
        "manual override",
        "suspicious",
        "duplicate",
        "refund",
    }

    def detect(self, transactions: list[CleanTransaction]) -> list[RiskSignalDTO]:
        signals: list[RiskSignalDTO] = []
        for tx in transactions:
            key = MedianDetector.key(tx)
            if tx.notes and any(term in tx.notes.lower() for term in self.suspicious_terms):
                signals.append(
                    RiskSignalDTO(
                        key,
                        "SUSPICIOUS_NOTE",
                        20,
                        "Notes contain suspicious language",
                    )
                )
            if not tx.txn_id:
                signals.append(
                    RiskSignalDTO(
                        key, "MISSING_TXN_ID", 10, "Transaction ID is missing"
                    )
                )
        return signals


class DuplicateDetector:
    def __init__(self, seen_patterns: set[tuple] | None = None) -> None:
        self.seen_patterns = seen_patterns if seen_patterns is not None else set()

    def detect(self, transactions: list[CleanTransaction]) -> list[RiskSignalDTO]:
        signals: list[RiskSignalDTO] = []
        for tx in transactions:
            duplicate_pattern = (tx.date, tx.merchant.lower(), tx.amount, tx.account_id)
            if duplicate_pattern in self.seen_patterns:
                signals.append(
                    RiskSignalDTO(
                        MedianDetector.key(tx),
                        "DUPLICATE_PATTERN",
                        15,
                        "Duplicate transaction pattern",
                    )
                )
            self.seen_patterns.add(duplicate_pattern)
        return signals


# Backwards compatibility alias for stages.py or external components
StatisticalDetector = MedianDetector
