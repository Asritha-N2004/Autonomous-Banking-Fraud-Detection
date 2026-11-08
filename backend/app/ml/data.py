"""Seeded synthetic research data. Labels are simulated, never real customer findings."""
from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd

def generate(n=2400, seed=42):
    rng = np.random.default_rng(seed)
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    rows = []
    for i in range(n):
        a = int(rng.integers(0, 70))
        fraud = bool(rng.random() < .065)
        # Overlapping distributions prevent labels from being encoded by a single field.
        amount = float(round(rng.lognormal(7.0 + (1.1 if fraud else 0), .95), 2))
        beneficiary = int(rng.integers(0, 80)) if fraud else (a + int(rng.integers(1, 8))) % 80
        rows.append(dict(id=f'SYN-T{i:06d}', account_id=f'SYN-A{a:03d}', beneficiary_id=f'SYN-A{beneficiary:03d}',
            merchant_id=f'SYN-M{int(rng.integers(0, 14)):02d}', device_id=f'SYN-D{int(rng.integers(0, 15)) if fraud else a:03d}',
            timestamp=(start + timedelta(minutes=i * 20 + int(rng.integers(0, 15)))).isoformat(),
            amount=amount, currency='INR', transaction_type=str(rng.choice(['transfer', 'purchase', 'withdrawal', 'deposit'])),
            channel=str(rng.choice(['mobile', 'web', 'atm', 'branch'], p=[.55,.3,.1,.05] if fraud else [.4,.25,.2,.15])),
            synthetic=True, historical_label=int(fraud), source=f'synthetic-generator-v1-seed-{seed}'))
    return pd.DataFrame(rows)
