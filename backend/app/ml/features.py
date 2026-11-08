from collections import defaultdict
import numpy as np
import pandas as pd

FEATURES = ['log_amount', 'hour', 'day_of_week', 'prior_count', 'prior_mean', 'amount_ratio', 'velocity_24h', 'unique_counterparties', 'new_beneficiary', 'new_device', 'account_degree']
CATEGORICAL = ['transaction_type', 'channel']

def engineer(frame):
    """Strictly earlier records only; equal timestamp records share the same snapshot."""
    frame = frame.copy().drop_duplicates('id')
    frame['timestamp'] = pd.to_datetime(frame['timestamp'], utc=True)
    frame = frame.sort_values(['timestamp', 'id']).reset_index(drop=True)
    histories = defaultdict(list)
    links = defaultdict(set)
    rows = []
    for timestamp, group in frame.groupby('timestamp', sort=True):
        for t in group.to_dict('records'):
            prior = histories[t['account_id']]
            amounts = [r['amount'] for r in prior]
            mean = float(np.mean(amounts)) if amounts else t['amount']
            recent = [r for r in prior if (timestamp-r['timestamp']).total_seconds() <= 86400]
            rows.append({**t, 'log_amount': float(np.log1p(t['amount'])), 'hour': timestamp.hour,
                'day_of_week': timestamp.dayofweek, 'prior_count': len(prior), 'prior_mean': mean,
                'amount_ratio': t['amount']/max(mean, 1), 'velocity_24h': len(recent),
                'unique_counterparties': len({r['beneficiary_id'] for r in prior}),
                'new_beneficiary': int(t['beneficiary_id'] not in {r['beneficiary_id'] for r in prior}),
                'new_device': int(t.get('device_id') not in {r.get('device_id') for r in prior}),
                'account_degree': len(links[t['account_id']])})
        for t in group.to_dict('records'):
            histories[t['account_id']].append(t)
            links[t['account_id']].add(t['beneficiary_id'])
            links[t['beneficiary_id']].add(t['account_id'])
    return pd.DataFrame(rows)
