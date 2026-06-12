import csv
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class CleanTransaction:
    txn_id: str | None
    date: date
    merchant: str
    amount: Decimal
    currency: str
    status: str
    category: str
    account_id: str
    notes: str | None = None


@dataclass(frozen=True)
class CleaningResult:
    raw_count: int
    clean_count: int
    transactions: list[CleanTransaction]
    errors: list[str]


class TransactionCleaner:
    required_columns = {"date", "merchant", "amount", "currency", "status", "account_id"}
    date_formats = ("%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d")

    def clean_file(self, path: Path) -> CleaningResult:
        errors: list[str] = []
        transactions: list[CleanTransaction] = []
        seen: set[tuple] = set()
        raw_count = 0

        with path.open(newline="", encoding="utf-8-sig") as csvfile:
            reader = csv.DictReader(csvfile)
            missing = self.required_columns - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"CSV is missing required columns: {', '.join(sorted(missing))}")

            for row in reader:
                raw_count += 1
                try:
                    tx = self.clean_row(row)
                except ValueError as exc:
                    errors.append(f"row {raw_count}: {exc}")
                    continue

                signature = (
                    tx.txn_id,
                    tx.date.isoformat(),
                    tx.merchant.lower(),
                    str(tx.amount),
                    tx.currency,
                    tx.account_id,
                )
                if signature in seen:
                    continue
                seen.add(signature)
                transactions.append(tx)

        return CleaningResult(
            raw_count=raw_count,
            clean_count=len(transactions),
            transactions=transactions,
            errors=errors,
        )

    def clean_row(self, row: dict[str, str | None]) -> CleanTransaction:
        merchant = self._text(row.get("merchant"))
        account_id = self._text(row.get("account_id"))
        if not merchant:
            raise ValueError("merchant is required")
        if not account_id:
            raise ValueError("account_id is required")

        return CleanTransaction(
            txn_id=self._optional_text(row.get("txn_id") or row.get("transaction_id")),
            date=self._date(row.get("date")),
            merchant=merchant,
            amount=self._amount(row.get("amount")),
            currency=self._currency(row.get("currency")),
            status=self._text(row.get("status")).upper(),
            category=self._optional_text(row.get("category")) or "Uncategorised",
            account_id=account_id,
            notes=self._optional_text(row.get("notes")),
        )

    def _date(self, value: str | None) -> date:
        raw = self._text(value)
        for fmt in self.date_formats:
            try:
                return datetime.strptime(raw, fmt).date()
            except ValueError:
                pass
        raise ValueError(f"unsupported date format: {raw}")

    def _amount(self, value: str | None) -> Decimal:
        raw = self._text(value)
        cleaned = re.sub(r"[^0-9.\-]", "", raw)
        try:
            return Decimal(cleaned).quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError(f"invalid amount: {raw}") from exc

    def _currency(self, value: str | None) -> str:
        raw = self._text(value).upper()
        if len(raw) != 3:
            raise ValueError(f"invalid currency: {raw}")
        return raw

    def _text(self, value: str | None) -> str:
        text = (value or "").strip()
        if not text:
            raise ValueError("blank value")
        return text

    def _optional_text(self, value: str | None) -> str | None:
        text = (value or "").strip()
        return text or None


def chunked(items: list[CleanTransaction], size: int) -> Iterable[list[CleanTransaction]]:
    for index in range(0, len(items), size):
        yield items[index : index + size]
