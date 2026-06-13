import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum


class CircuitState(StrEnum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


@dataclass
class CircuitBreaker:
    failure_threshold: int = 3
    recovery_seconds: int = 60
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    opened_at: datetime | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def allow_request(self) -> bool:
        with self._lock:
            if self.state == CircuitState.CLOSED:
                return True
            if self.state == CircuitState.OPEN and self.opened_at:
                if datetime.now(UTC) - self.opened_at >= timedelta(seconds=self.recovery_seconds):
                    self.state = CircuitState.HALF_OPEN
                    return True
            return self.state == CircuitState.HALF_OPEN

    def record_success(self) -> None:
        with self._lock:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.opened_at = None

    def record_failure(self) -> None:
        with self._lock:
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                self.opened_at = datetime.now(UTC)


_llm_breaker = CircuitBreaker()


def get_llm_circuit_breaker() -> CircuitBreaker:
    return _llm_breaker


# Backwards-compat alias (will be removed in future)
get_gemini_circuit_breaker = get_llm_circuit_breaker
