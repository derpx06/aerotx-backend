from decimal import Decimal

from app.services.cleaning.engine import TransactionCleaner


def test_cleaner_normalizes_dates_amounts_status_and_category(tmp_path):
    csv_path = tmp_path / "transactions.csv"
    csv_path.write_text(
        "txn_id,date,merchant,amount,currency,status,category,account_id,notes\n"
        't1,31-12-2025,Amazon India,"₹1,234.50",INR,completed,,acct-1,\n'
        "t2,2025/12/30,Cafe,$10.00,USD,pending,Food,acct-1,urgent review\n",
        encoding="utf-8",
    )

    result = TransactionCleaner().clean_file(csv_path)

    assert result.raw_count == 2
    assert result.clean_count == 2
    assert result.transactions[0].date.isoformat() == "2025-12-31"
    assert result.transactions[0].amount == Decimal("1234.50")
    assert result.transactions[0].status == "COMPLETED"
    assert result.transactions[0].category == "Uncategorised"


def test_cleaner_removes_duplicate_rows(tmp_path):
    csv_path = tmp_path / "transactions.csv"
    row = "t1,2025-12-31,Amazon India,100,INR,completed,Shopping,acct-1,\n"
    csv_path.write_text(
        "txn_id,date,merchant,amount,currency,status,category,account_id,notes\n" + row + row,
        encoding="utf-8",
    )

    result = TransactionCleaner().clean_file(csv_path)

    assert result.raw_count == 2
    assert result.clean_count == 1
