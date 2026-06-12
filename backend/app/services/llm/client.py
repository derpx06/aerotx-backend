import asyncio
import json
import random
from collections.abc import Callable
from typing import Any

import httpx
import structlog

from app.core.config import get_settings
from app.infrastructure.resilience.circuit_breaker import get_gemini_circuit_breaker

log = structlog.get_logger(__name__)


class LLMClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def generate_json(
        self,
        prompt: str,
        fallback: Callable[[], dict[str, Any]],
        validator: Callable[[str], Any] | None = None,
    ) -> tuple[str, bool]:
        breaker = get_gemini_circuit_breaker()
        if not self.settings.gemini_api_key:
            return json.dumps(fallback()), False

        if not breaker.allow_request():
            log.warning("llm_circuit_open_using_fallback", provider="gemini")
            return json.dumps(fallback()), False

        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.settings.gemini_model}:generateContent"
        )
        params = {"key": self.settings.gemini_api_key}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"},
        }
        last_error: Exception | None = None

        for attempt in range(1, self.settings.llm_max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.settings.llm_timeout_seconds) as client:
                    response = await client.post(url, params=params, json=payload)

                    if response.status_code == 429:
                        # Rate limited, back off with jitter
                        backoff = (2**attempt) + random.uniform(0.5, 1.5)
                        log.warning(
                            "llm_rate_limit_encountered",
                            attempt=attempt,
                            backoff_seconds=round(backoff, 2),
                        )
                        await asyncio.sleep(backoff)
                        continue

                    response.raise_for_status()
                    data = response.json()

                text = data["candidates"][0]["content"]["parts"][0]["text"]

                # Structured Output Validation
                if validator is not None:
                    validator(text)

                breaker.record_success()
                return text, True

            except Exception as exc:
                last_error = exc
                breaker.record_failure()
                log.warning(
                    "llm_call_failed",
                    attempt=attempt,
                    error_context={"type": type(exc).__name__, "message": str(exc)},
                )
                # Exponential backoff with jitter
                backoff = (2**attempt) + random.uniform(0.1, 0.9)
                await asyncio.sleep(backoff)

        log.error(
            "llm_retries_exhausted",
            error_context={"type": type(last_error).__name__ if last_error else None},
        )
        return json.dumps(fallback()), False
