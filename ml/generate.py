"""Generate independently sampled, explicitly synthetic invoice snapshots/outcomes.

One unique customer/invoice per record. Not ERP data, not copies of the six
Supabase rows. Outcomes are stochastic from an invented mechanism, not proof of
real-world predictive performance. No external/private dataset or service needed.
"""
import argparse
import csv
import math
import hashlib
import json
import random
from datetime import date, timedelta
from pathlib import Path

SEED = 42
FIELDS = ['invoice_id', 'customer_id', 'snapshot_date', 'due_date', 'amount',
          'previous_invoices', 'late_payments', 'broken_promises', 'settled_date', 'outcome_observed_through']
START, END = date(2024, 1, 1), date(2026, 8, 31)


def generate(path, count=4000, seed=SEED):
    rng = random.Random(seed)
    rows = []
    for i in range(count):
        snapshot = START + timedelta(days=rng.randrange((END - START).days + 1))
        days = rng.randint(1, 180)
        amount = round(math.exp(rng.uniform(math.log(100), math.log(250000))), 2)
        previous = 0 if rng.random() < .12 else rng.randint(2, 40)
        late = sum(rng.random() < rng.betavariate(2, 3) for _ in range(previous))
        # Independent snapshot feature, known before the new outcome.
        broken = rng.choices([0, 1, 2, 3, 4], [65, 22, 8, 4, 1])[0]
        rate = late / previous if previous else 0
        # Invented nonlinear + noisy world; model does not receive this formula.
        logit = (-3.2 + .018 * days + 2.0 * rate + .55 * min(broken, 4)
                 + .20 * math.log1p(amount / 10000) + .45 * (previous == 0)
                 + .40 * (days > 90 and broken > 0) + rng.gauss(0, .65))
        remains = rng.random() < 1 / (1 + math.exp(-logit))
        delay = rng.randint(31, 150) if remains else rng.randint(1, 30)
        settlement = snapshot + timedelta(days=delay)
        observed = snapshot + timedelta(days=30)
        rows.append({'invoice_id': f'SYN-{i:05d}', 'customer_id': f'SYN-C-{i:05d}',
            'snapshot_date': snapshot.isoformat(), 'due_date': (snapshot - timedelta(days=days)).isoformat(),
            'amount': f'{amount:.2f}', 'previous_invoices': previous, 'late_payments': late,
            'broken_promises': broken,
            # Outcomes beyond observation horizon are right-censored: blank.
            'settled_date': settlement.isoformat() if settlement <= observed else '',
            'outcome_observed_through': observed.isoformat()})
    rows.sort(key=lambda row: (row['snapshot_date'], row['invoice_id']))
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    manifest = {'synthetic': True, 'generator': 'ml/generate.py v1', 'seed': seed,
                'rows': count, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                'observation_cutoff': max(row['outcome_observed_through'] for row in rows)}
    path.with_suffix('.meta.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return rows


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='ml/data/synthetic_history.csv')
    parser.add_argument('--rows', type=int, default=4000)
    parser.add_argument('--seed', type=int, default=SEED)
    args = parser.parse_args()
    if args.rows < 100:
        parser.error('Use at least 100 rows; default 4000 supports the chronological splits.')
    generate(args.output, args.rows, args.seed)
    print(f'Wrote {args.rows} synthetic snapshots to {args.output}; seed {args.seed}.')
