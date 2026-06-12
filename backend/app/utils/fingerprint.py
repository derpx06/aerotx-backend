import hashlib
from datetime import date
from decimal import Decimal


def transaction_fingerprint(
    txn_id: str | None,
    txn_date: date,
    merchant: str,
    amount: Decimal,
    currency: str,
    account_id: str,
) -> str:
    payload = "|".join(
        [
            txn_id or "",
            txn_date.isoformat(),
            merchant.strip().lower(),
            str(amount),
            currency.upper(),
            account_id.strip().lower(),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
