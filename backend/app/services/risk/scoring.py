from collections import defaultdict
from decimal import Decimal

from app.models.enums import RiskLevel
from app.services.cleaning.engine import CleanTransaction
from app.services.risk.detectors import (
    CurrencyDetector,
    DuplicateDetector,
    MedianDetector,
    NotesDetector,
    RiskSignalDTO,
)


class RiskAggregator:
    def score(self, signals: list[RiskSignalDTO]) -> dict[tuple, tuple[int, RiskLevel, bool]]:
        scores: dict[tuple, int] = defaultdict(int)
        for signal in signals:
            scores[signal.txn_key] += signal.signal_score

        result: dict[tuple, tuple[int, RiskLevel, bool]] = {}
        for key, score in scores.items():
            result[key] = (score, self.level(score), score > 0)
        return result

    def level(self, score: int) -> RiskLevel:
        if score >= 60:
            return RiskLevel.HIGH
        if score >= 30:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW


class RiskEngine:
    def __init__(self, medians: dict[str, Decimal] | None = None) -> None:
        self.detectors = [
            MedianDetector(medians=medians),
            CurrencyDetector(),
            NotesDetector(),
            DuplicateDetector(),
        ]
        self.aggregator = RiskAggregator()

    def evaluate(
        self, transactions: list[CleanTransaction]
    ) -> tuple[dict[tuple, tuple[int, RiskLevel, bool]], list[RiskSignalDTO]]:
        signals: list[RiskSignalDTO] = []
        for detector in self.detectors:
            signals.extend(detector.detect(transactions))
        return self.aggregator.score(signals), signals
