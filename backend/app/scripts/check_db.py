import asyncio
from sqlalchemy import select
from collections import Counter

from app.core.database import SessionLocal
from app.models.transaction import Transaction
from app.models.job import Job  # noqa: F401
from app.models.event import JobEvent  # noqa: F401
from app.models.summary import JobSummary  # noqa: F401

async def check():
    async with SessionLocal() as session:
        res = await session.execute(select(Transaction))
        txs = res.scalars().all()
        print(f"Total transactions: {len(txs)}")
        
        # Check duplicate patterns
        patterns = [(tx.date, tx.merchant.lower(), float(tx.amount), tx.account_id) for tx in txs]
        counts = Counter(patterns)
        print(f"Unique patterns count: {len(counts)}")
        print("Most common patterns:")
        for pat, cnt in counts.most_common(10):
            print(f"  Count: {cnt} | {pat}")
            
        # Check notes
        notes_cnt = 0
        for tx in txs:
            if tx.notes:
                notes_cnt += 1
        print(f"Transactions with notes: {notes_cnt}")
        
        # Check how many have risk_score > 0
        non_zero = sum(1 for tx in txs if tx.risk_score > 0)
        print(f"Transactions with non-zero risk score: {non_zero}")

if __name__ == "__main__":
    asyncio.run(check())
