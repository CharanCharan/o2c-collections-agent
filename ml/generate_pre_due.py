"""Independent synthetic snapshots at due-7; outcomes observed after due.

Not real ERP data. No current-invoice aging or future settlement enters features.
"""
import argparse
import csv
import hashlib
import json
import math
import random
from datetime import timedelta
from pathlib import Path

from .generate import FIELDS, START, END


def generate(path='ml/data/pre_due_history.csv', count=4000, seed=123):
    rng, rows = random.Random(seed), []
    for i in range(count):
        snapshot = START + timedelta(days=rng.randrange((END - START).days + 1))
        due = snapshot + timedelta(days=7)
        amount = round(math.exp(rng.uniform(math.log(100), math.log(250000))), 2)
        previous = 0 if rng.random() < .12 else rng.randint(2, 40)
        customer_rate = rng.betavariate(1.6, 2.4)
        late = sum(rng.random() < customer_rate for _ in range(previous))
        broken = rng.choices([0, 1, 2, 3, 4], [65, 22, 8, 4, 1])[0]
        rate = late / previous if previous else 0
        logit = (-2.6 + 3.2 * rate + .65 * broken + .25 * math.log1p(amount / 10000)
                 + .6 * (previous == 0) + rng.gauss(0, .7))
        becomes_overdue = rng.random() < 1 / (1 + math.exp(-logit))
        settlement = snapshot + timedelta(days=rng.randint(8, 60) if becomes_overdue else rng.randint(1, 7))
        observed = due + timedelta(days=1)
        rows.append({'invoice_id': f'PRE-{i:05d}', 'customer_id': f'PRE-C-{i:05d}',
            'snapshot_date': snapshot.isoformat(), 'due_date': due.isoformat(), 'amount': f'{amount:.2f}',
            'previous_invoices': previous, 'late_payments': late, 'broken_promises': broken,
            'settled_date': settlement.isoformat() if settlement <= observed else '',
            'outcome_observed_through': observed.isoformat()})
    rows.sort(key=lambda row: (row['snapshot_date'], row['invoice_id']))
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator='\n')
        writer.writeheader(); writer.writerows(rows)
    manifest = {'synthetic': True, 'generator': 'ml/generate_pre_due.py v1', 'seed': seed,
                'rows': count, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                'observation_cutoff': max(row['outcome_observed_through'] for row in rows)}
    path.with_suffix('.meta.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return rows


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='ml/data/pre_due_history.csv')
    parser.add_argument('--rows', type=int, default=4000)
    parser.add_argument('--seed', type=int, default=123)
    args = parser.parse_args()
    if args.rows < 100:
        parser.error('Use at least 100 rows; default 4000 supports chronological splits.')
    generate(args.output, args.rows, args.seed)
    print(f'Generated {args.rows} synthetic pre-due snapshots; seed {args.seed}.')
