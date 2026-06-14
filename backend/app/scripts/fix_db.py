import asyncio
from sqlalchemy import select, delete
from collections import defaultdict

from app.core.database import SessionLocal
from app.models.transaction import Transaction, RiskSignal
from app.services.risk.detectors import MedianDetector, CurrencyDetector, DuplicateDetector, NotesDetector
from app.services.risk.scoring import RiskAggregator
from app.services.cleaning.engine import CleanTransaction

def get_median(lst):
    n = len(lst)
    if n == 0:
        return 0.0
    s_lst = sorted(lst)
    mid = n // 2
    if n % 2 == 1:
        return float(s_lst[mid])
    else:
        return float((s_lst[mid - 1] + s_lst[mid]) / 2.0)

async def fix_all():
    async with SessionLocal() as session:
        # Fetch all transactions
        result = await session.execute(select(Transaction))
        txs = result.scalars().all()
        print(f"Loaded {len(txs)} transactions from database.")
        
        if not txs:
            print("No transactions found in database.")
            return
            
        # Prepare clean transactions for detectors
        clean_txs = []
        tx_map = {}
        for tx in txs:
            ctx = CleanTransaction(
                txn_id=tx.txn_id,
                date=tx.date,
                merchant=tx.merchant,
                amount=tx.amount,
                currency=tx.currency,
                status=tx.status,
                category=tx.category,
                account_id=tx.account_id,
                notes=tx.notes
            )
            clean_txs.append(ctx)
            # Use same key structure as detectors
            key = (tx.txn_id, tx.date, tx.merchant, tx.amount, tx.currency, tx.account_id)
            tx_map[key] = tx

        # 1. Run detectors to get all risk signals
        detectors = [
            MedianDetector(),
            CurrencyDetector(),
            DuplicateDetector(),
            NotesDetector()
        ]
        
        # Precompute medians for MedianDetector
        acct_amounts = defaultdict(list)
        for tx in txs:
            acct_amounts[tx.account_id].append(float(tx.amount))
        
        medians = {}
        for acct, amts in acct_amounts.items():
            medians[acct] = get_median(amts)
            
        detectors[0].medians = medians
        
        all_signals = []
        for d in detectors:
            signals = d.detect(clean_txs)
            all_signals.extend(signals)
            
        # 2. Score them
        agg = RiskAggregator()
        scores = agg.score(all_signals)
        
        # 3. Update in database
        # First, delete all existing risk signals
        await session.execute(delete(RiskSignal))
        
        updated_count = 0
        for key, tx in tx_map.items():
            score, level, is_anomaly = scores.get(key, (0, "LOW", False))
            
            # Find anomaly reason if any
            anomaly_reason = None
            tx_signals = [s for s in all_signals if s.txn_key == key]
            for s in tx_signals:
                if s.signal_type == "AMOUNT_OUTLIER":
                    anomaly_reason = s.description
                    break
            
            tx.risk_score = score
            tx.risk_level = level
            tx.is_anomaly = is_anomaly
            tx.anomaly_reason = anomaly_reason
            
            # Create RiskSignal records
            for s in tx_signals:
                sig_model = RiskSignal(
                    transaction_id=tx.id,
                    signal_type=s.signal_type,
                    signal_score=s.signal_score,
                    description=s.description
                )
                session.add(sig_model)
                
            updated_count += 1
            
        await session.commit()
        print(f"Successfully updated {updated_count} transactions and their risk signals.")

if __name__ == "__main__":
    asyncio.run(fix_all())
