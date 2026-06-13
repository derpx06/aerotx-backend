"""
LLM Client — Amazon Bedrock (Nova / Claude via boto3)

Supports the Bedrock Converse API which provides a unified interface across
all Bedrock models (Nova, Claude, Titan, etc.), eliminating the need for
model-specific request/response shaping.
"""

import asyncio
import json
import random
from collections.abc import Callable
from typing import Any

import boto3
import structlog

from app.core.config import get_settings
from app.infrastructure.resilience.circuit_breaker import get_llm_circuit_breaker

log = structlog.get_logger(__name__)


class LLMClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _get_bedrock_client(self):
        """Create a synchronous boto3 Bedrock Runtime client."""
        kwargs: dict[str, Any] = {"region_name": self.settings.aws_region}
        if self.settings.aws_access_key_id:
            kwargs["aws_access_key_id"] = self.settings.aws_access_key_id
        if self.settings.aws_secret_access_key:
            kwargs["aws_secret_access_key"] = self.settings.aws_secret_access_key
        return boto3.client("bedrock-runtime", **kwargs)

    def _has_credentials(self) -> bool:
        """Return True if AWS credentials are explicitly configured or available via IAM role."""
        if self.settings.aws_access_key_id and self.settings.aws_secret_access_key:
            return True
        # Fall back to checking for ambient creds (IAM role, env, ~/.aws/credentials)
        try:
            session = boto3.Session()
            creds = session.get_credentials()
            return creds is not None
        except Exception:
            return False

    async def generate_json(
        self,
        prompt: str,
        fallback: Callable[[], dict[str, Any]],
        validator: Callable[[str], Any] | None = None,
    ) -> tuple[str, bool]:
        """
        Call Amazon Bedrock (Converse API) and return (json_text, llm_was_used).

        Falls back to fallback() if credentials are absent or the circuit breaker
        is open.
        """
        breaker = get_llm_circuit_breaker()

        if not self._has_credentials():
            log.warning("bedrock_no_credentials_using_fallback")
            return json.dumps(fallback()), False

        if not breaker.allow_request():
            log.warning("llm_circuit_open_using_fallback", provider="bedrock")
            return json.dumps(fallback()), False

        last_error: Exception | None = None

        for attempt in range(1, self.settings.llm_max_retries + 1):
            try:
                text = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None,
                        self._invoke_bedrock_sync,
                        prompt,
                    ),
                    timeout=self.settings.llm_timeout_seconds,
                )

                if validator is not None:
                    validator(text)

                breaker.record_success()
                return text, True

            except asyncio.TimeoutError as exc:
                last_error = exc
                breaker.record_failure()
                log.warning(
                    "llm_call_timeout",
                    attempt=attempt,
                    timeout=self.settings.llm_timeout_seconds,
                )
            except Exception as exc:
                last_error = exc
                error_str = str(exc)

                # Throttling — back off and retry
                if "ThrottlingException" in error_str or "TooManyRequestsException" in error_str:
                    backoff = (2**attempt) + random.uniform(0.5, 1.5)
                    log.warning(
                        "llm_rate_limit_encountered",
                        attempt=attempt,
                        backoff_seconds=round(backoff, 2),
                    )
                    await asyncio.sleep(backoff)
                    continue

                breaker.record_failure()
                log.warning(
                    "llm_call_failed",
                    attempt=attempt,
                    error_context={"type": type(exc).__name__, "message": error_str},
                )

            # Exponential backoff with jitter before next attempt
            backoff = (2**attempt) + random.uniform(0.1, 0.9)
            await asyncio.sleep(backoff)

        log.error(
            "llm_retries_exhausted",
            error_context={"type": type(last_error).__name__ if last_error else None},
        )
        return json.dumps(fallback()), False

    def _invoke_bedrock_sync(self, prompt: str) -> str:
        """
        Synchronous Bedrock Converse API call (run in an executor thread).

        Uses the Converse API — a unified interface that works for Nova, Claude,
        Titan and all other Bedrock-hosted models without model-specific schemas.
        """
        client = self._get_bedrock_client()

        # Append a JSON-only instruction to the prompt so the model returns
        # a raw JSON object regardless of its default formatting behaviour.
        json_prompt = (
            prompt
            + "\n\nIMPORTANT: Respond with ONLY a valid JSON object. "
            "Do not include markdown code fences, explanations, or any text outside the JSON."
        )

        response = client.converse(
            modelId=self.settings.bedrock_model_id,
            messages=[
                {
                    "role": "user",
                    "content": [{"text": json_prompt}],
                }
            ],
            inferenceConfig={
                "maxTokens": 2048,
                "temperature": 0.1,  # Low temp for deterministic JSON output
            },
        )

        # Converse API returns a unified response regardless of underlying model
        raw_text: str = response["output"]["message"]["content"][0]["text"].strip()

        # Strip markdown fences if the model wraps output despite our instruction
        if raw_text.startswith("```"):
            lines = raw_text.splitlines()
            # Remove first fence line (```json or ```) and last fence line
            inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
            raw_text = "\n".join(inner).strip()

        return raw_text
