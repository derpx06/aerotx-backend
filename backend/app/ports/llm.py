from collections.abc import Callable
from typing import Any, Protocol


class LLMPort(Protocol):
    async def generate_json(
        self, prompt: str, fallback: Callable[[], dict[str, Any]]
    ) -> tuple[str, bool]:
        raise NotImplementedError
