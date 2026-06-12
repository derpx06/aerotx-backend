import json
from typing import Any


class ResponseValidator:
    def parse_json_object(self, raw: str) -> dict[str, Any]:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("LLM response was not valid JSON") from exc
        if not isinstance(parsed, dict):
            raise ValueError("LLM response must be a JSON object")
        return parsed

    def categories(self, raw: str) -> dict[str, str]:
        parsed = self.parse_json_object(raw)
        categories = parsed.get("categories")
        if not isinstance(categories, dict):
            raise ValueError("LLM category response must include a categories object")
        return {str(key): str(value) for key, value in categories.items()}

    def narrative(self, raw: str) -> str:
        parsed = self.parse_json_object(raw)
        narrative = parsed.get("narrative")
        if not isinstance(narrative, str) or not narrative.strip():
            raise ValueError("LLM summary response must include a narrative")
        return narrative.strip()
