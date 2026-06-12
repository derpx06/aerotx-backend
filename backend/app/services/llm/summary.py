import json
from decimal import Decimal

from app.models.enums import RiskLevel
from app.services.llm.client import LLMClient
from app.services.llm.response_validator import ResponseValidator


class SummaryNarrativeService:
    def __init__(self, client: LLMClient | None = None, validator: ResponseValidator | None = None):
        self.client = client or LLMClient()
        self.validator = validator or ResponseValidator()

    async def create_narrative(
        self,
        total_spend_inr: Decimal,
        total_spend_usd: Decimal,
        anomaly_count: int,
        top_merchants: list[dict],
        risk_level: RiskLevel,
    ) -> tuple[str, RiskLevel, bool]:
        facts = {
            "total_spend_by_currency": {"INR": str(total_spend_inr), "USD": str(total_spend_usd)},
            "top_3_merchants": top_merchants[:3],
            "anomaly_count": anomaly_count,
            "risk_level": risk_level.value.lower(),
        }
        prompt = (
            "Write an executive summary for a transaction risk report. "
            "Based on the input facts, produce a JSON object with these exact keys:\n"
            "- 'total_spend_by_currency': dict matching the input total spends by currency\n"
            "- 'top_3_merchants': list of the top 3 merchants from the input top merchants\n"
            "- 'anomaly_count': count of anomalies\n"
            "- 'narrative': a 2-3 sentence narrative explaining the spending behavior and why risk level is what it is\n"
            "- 'risk_level': the overall risk level ('low', 'medium', or 'high')\n"
            "Do not change or recalculate any numbers. Return JSON only.\n"
            f"Input Facts: {json.dumps(facts)}"
        )

        def validate_narrative_response(raw: str) -> dict:
            parsed = json.loads(raw)
            narr = parsed.get("narrative", "").strip()
            if not narr:
                raise ValueError("LLM summary response must include a non-empty narrative")
            return parsed

        raw, llm_success = await self.client.generate_json(
            prompt,
            lambda: self._fallback(facts),
            validator=validate_narrative_response,
        )
        parsed = json.loads(raw)
        narrative = parsed.get("narrative", "").strip()
        risk_str = parsed.get("risk_level", "").upper()
        try:
            out_risk_level = RiskLevel(risk_str)
        except ValueError:
            out_risk_level = risk_level

        return narrative, out_risk_level, llm_success

    def _fallback(self, facts: dict) -> dict:
        return {
            "total_spend_by_currency": facts["total_spend_by_currency"],
            "top_3_merchants": facts["top_3_merchants"],
            "anomaly_count": facts["anomaly_count"],
            "narrative": (
                f"Processed spend totals are INR {facts['total_spend_by_currency'].get('INR', '0')} and USD "
                f"{facts['total_spend_by_currency'].get('USD', '0')}. The overall risk level is {facts['risk_level']} "
                f"with {facts['anomaly_count']} anomalous transactions detected."
            ),
            "risk_level": facts["risk_level"],
        }
