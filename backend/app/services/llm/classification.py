import json

from app.services.cleaning.engine import CleanTransaction
from app.services.llm.client import LLMClient
from app.services.llm.response_validator import ResponseValidator


class ClassificationService:
    def __init__(self, client: LLMClient | None = None, validator: ResponseValidator | None = None):
        self.client = client or LLMClient()
        self.validator = validator or ResponseValidator()

    async def classify_batch(
        self, transactions: list[CleanTransaction]
    ) -> tuple[dict[str, str], str, bool]:
        candidates = [
            {
                "txn_id": tx.txn_id or f"row-{idx}",
                "merchant": tx.merchant,
                "amount": str(tx.amount),
                "currency": tx.currency,
                "existing_category": tx.category,
            }
            for idx, tx in enumerate(transactions)
        ]
        prompt = (
            "Classify these financial transactions. Return JSON only with shape "
            '{"categories":{"txn_id":"Category"}}. Choose the category for each transaction '
            "from one of: Food, Shopping, Travel, Transport, Utilities, Cash Withdrawal, Entertainment, or Other. "
            "Do not use any other category names. Keep categories concise.\n"
            f"{json.dumps(candidates)}"
        )
        raw, llm_success = await self.client.generate_json(
            prompt,
            lambda: self._fallback(candidates),
            validator=self.validator.categories,
        )
        try:
            categories = self.validator.categories(raw)
        except ValueError:
            fallback_raw = json.dumps(self._fallback(candidates))
            return self.validator.categories(fallback_raw), fallback_raw, False
        return categories, raw, llm_success

    def _fallback(self, candidates: list[dict]) -> dict:
        categories: dict[str, str] = {}
        for item in candidates:
            merchant = item["merchant"].lower()
            if any(word in merchant for word in ("uber", "taxi", "fuel")):
                category = "Transport"
            elif any(word in merchant for word in ("amazon", "flipkart", "store")):
                category = "Shopping"
            elif any(word in merchant for word in ("hotel", "air", "travel")):
                category = "Travel"
            elif any(word in merchant for word in ("cafe", "restaurant", "food")):
                category = "Food"
            else:
                existing = item.get("existing_category")
                if existing and existing != "Uncategorised":
                    category = existing
                else:
                    category = "Other"
            categories[str(item["txn_id"])] = category
        return {"categories": categories}
