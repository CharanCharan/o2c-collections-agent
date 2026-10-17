"""Fit on past snapshots, select C on validation Brier, report untouched holdout.

Run from repository root: python -m ml.generate; python -m ml.train.
Outcome columns are used only for labels and maturity checks, never features.
"""
import argparse
import csv
import hashlib
import json
import platform
from datetime import date, timedelta
from pathlib import Path

from backend.risk_model import FEATURES, FEATURE_VERSION, TARGET, LIMITATION, canonical, feature_values, score

CANDIDATES = [.1, 1.0, 10.0]


def split_name(snapshot):
    if snapshot <= date(2025, 11, 30):
        return 'train'
    if date(2026, 1, 1) <= snapshot <= date(2026, 3, 31):
        return 'validation'
    if date(2026, 5, 1) <= snapshot <= date(2026, 8, 31):
        return 'test'
    return 'embargo'


def labeled_row(row):
    snapshot, due, observed = (date.fromisoformat(row[key]) for key in
                              ['snapshot_date', 'due_date', 'outcome_observed_through'])
    horizon = snapshot + timedelta(days=30)
    if observed < horizon:
        raise ValueError('Immature outcome: cannot label a snapshot before its 30-day horizon.')
    settled = date.fromisoformat(row['settled_date']) if row['settled_date'] else None
    if settled is not None and (settled <= snapshot or settled > observed):
        raise ValueError('Settlement must follow the scoring snapshot and be observed.')
    # Blank settlement + adequate observation means still outstanding at horizon.
    label = int(settled is None or settled > horizon)
    features = feature_values((snapshot - due).days, row['amount'], int(row['previous_invoices']),
                              int(row['late_payments']), int(row['broken_promises']))
    return snapshot, features, label


def load_history(path):
    groups = {name: [] for name in ['train', 'validation', 'test', 'embargo']}
    ids, customers = set(), set()
    with Path(path).open(newline='', encoding='utf-8') as stream:
        for row in csv.DictReader(stream):
            if row['invoice_id'] in ids or row['customer_id'] in customers:
                raise ValueError('This POC expects independent, unique invoice/customer snapshots.')
            ids.add(row['invoice_id']); customers.add(row['customer_id'])
            snapshot, features, label = labeled_row(row)
            groups[split_name(snapshot)].append((snapshot.isoformat(), features, label))
    for name in ['train', 'validation', 'test']:
        values = groups[name]
        if len(values) < 30 or len({r[2] for r in values}) != 2:
            raise ValueError(f'Need at least 30 mature rows and both classes in {name}.')
    for past, future in [('train', 'validation'), ('validation', 'test')]:
        if (date.fromisoformat(max(r[0] for r in groups[past])) + timedelta(days=30)
                >= date.fromisoformat(min(r[0] for r in groups[future]))):
            raise ValueError('Label horizons overlap the next chronological split.')
    return groups


def metrics(y, probabilities):
    import numpy as np
    from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score
    p, y = np.asarray(probabilities), np.asarray(y)
    count = max(1, math_ceil(len(y) * .2))
    top = np.argsort(-p, kind='stable')[:count]
    bins = []
    for low, high in [(0, .2), (.2, .4), (.4, .6), (.6, .8), (.8, 1.0)]:
        mask = (p >= low) & ((p < high) if high < 1 else (p <= high))
        if mask.any():
            bins.append({'range': [low, high], 'count': int(mask.sum()),
                         'mean_prediction': float(p[mask].mean()), 'observed_rate': float(y[mask].mean())})
    prevalence = float(y.mean())
    # Constant-score baseline has no ranking: expected top-fifth rate is prevalence.
    top_precision = prevalence if np.all(p == p[0]) else float(y[top].mean())
    return {'roc_auc': float(roc_auc_score(y, p)), 'average_precision': float(average_precision_score(y, p)),
            'brier': float(brier_score_loss(y, p)), 'log_loss': float(log_loss(y, p, labels=[0, 1])),
            'top_20_percent_precision': top_precision, 'top_20_percent_lift': top_precision / prevalence,
            'calibration_bins': bins}


def math_ceil(value):
    import math
    return math.ceil(value)


def train(source, output):
    import numpy as np
    import sklearn
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    manifest = json.loads(Path(source).with_suffix('.meta.json').read_text(encoding='utf-8'))
    digest = hashlib.sha256(Path(source).read_bytes()).hexdigest()
    if manifest.get('synthetic') is not True or manifest.get('sha256') != digest:
        raise ValueError('This lesson expects generated synthetic history with a matching manifest. Regenerate it.')
    groups = load_history(source)
    if sum(map(len, groups.values())) != manifest['rows']:
        raise ValueError('Manifest row count mismatch.')
    arrays = {name: (np.asarray([r[1] for r in rows]), np.asarray([r[2] for r in rows]))
              for name, rows in groups.items() if name != 'embargo'}
    xt, yt = arrays['train']; xv, yv = arrays['validation']
    candidates = []
    for c in CANDIDATES:
        estimator = make_pipeline(StandardScaler(), LogisticRegression(C=c, solver='lbfgs', max_iter=1000))
        estimator.fit(xt, yt)
        report = metrics(yv, estimator.predict_proba(xv)[:, 1])
        candidates.append((report['brier'], c, estimator, report))
    _, chosen_c, estimator, _ = min(candidates, key=lambda item: (item[0], item[1]))
    # No refit on validation/test: fitted parameters and scaler use training only.
    scaler, classifier = estimator.steps[0][1], estimator.steps[1][1]
    evaluation = {'selection_metric': 'validation Brier (lower is better)', 'selected_C': chosen_c,
        'candidates': [{'C': c, 'validation_brier': loss} for loss, c, _, _ in candidates],
        'split_policy': 'Chronological; December 2025 and April 2026 embargo; 30-day label maturity gaps.',
        'splits': {}}
    base_rate = float(yt.mean())
    max_difference = 0.0
    export = {'mean': scaler.mean_.tolist(), 'scale': scaler.scale_.tolist(),
              'coefficients': classifier.coef_[0].tolist(), 'intercept': float(classifier.intercept_[0])}
    for name, (x, y) in arrays.items():
        probability = estimator.predict_proba(x)[:, 1]
        portable = np.asarray([score(export, row)[0] for row in x])
        max_difference = max(max_difference, float(np.max(np.abs(probability - portable))))
        evaluation['splits'][name] = {'rows': len(y), 'snapshot_start': min(r[0] for r in groups[name]),
            'snapshot_end': max(r[0] for r in groups[name]), 'positive_rate': float(y.mean()),
            'logistic': metrics(y, probability), 'constant_baseline': metrics(y, np.full(len(y), base_rate))}
    if max_difference > 1e-12:
        raise ValueError('Exported inference differs from sklearn.')
    evaluation['max_export_probability_difference'] = max_difference
    artifact = {'schema_version': 1, 'model_type': 'standardized_logistic_regression',
        'feature_version': FEATURE_VERSION, 'features': FEATURES, 'target': TARGET, 'horizon_days': 30,
        **export, 'training_data': {'synthetic': True, 'generator': manifest['generator'], 'seed': manifest['seed'],
            'source': str(Path(source).as_posix()), 'sha256': digest,
            'total_rows': sum(map(len, groups.values())), 'embargo_rows': len(groups['embargo']),
            'observation_cutoff': manifest['observation_cutoff'],
            'provenance': 'Project-generated synthetic records; no real customers or public ERP data.',
            'snapshot_assumption': 'History counts and balances are known at snapshot time; settlement follows snapshot.'},
        'training_environment': {'python': platform.python_version(), 'scikit_learn': sklearn.__version__, 'numpy': np.__version__},
        'evaluation': evaluation, 'limitation': LIMITATION}
    artifact['model_version'] = 'ar-logreg-30d-v1-' + hashlib.sha256(canonical(artifact)).hexdigest()[:12]
    output = Path(output); output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps({'model_version': artifact['model_version'], 'selected_C': chosen_c,
                      'test': evaluation['splits']['test']}, indent=2))
    return artifact


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', default='ml/data/synthetic_history.csv')
    parser.add_argument('--output', default='artifacts/payment_risk.json')
    args = parser.parse_args()
    train(args.source, args.output)
