"""Shared feature contract and JSON logistic-regression inference.

Training uses scikit-learn; serving needs only Python's standard library.
The stored means/scales/coefficients are learned offline, never fitted per run.
"""
import hashlib
import json
import math
from pathlib import Path

ARTIFACT = Path(__file__).resolve().parents[1] / 'artifacts' / 'payment_risk.json'
FEATURE_VERSION = 'ar-snapshot-features-v1'
FEATURES = ['days_overdue_capped', 'late_rate', 'broken_promises_capped', 'log_balance', 'no_history']
TARGET = 'Outstanding balance remains 30 days after the snapshot date'
LIMITATION = 'Trained and evaluated only on synthetic history; not validated on real customer receivables.'


class ModelError(ValueError):
    pass


def feature_values(days, amount, previous, late, broken):
    """Only facts known at scoring time; future settlements/labels never enter."""
    amount = float(amount)
    if (not all(math.isfinite(float(x)) for x in [days, amount, previous, late, broken])
            or days < 1 or amount <= 0 or min(previous, late, broken) < 0 or late > previous):
        raise ModelError('Payment model requires a positive overdue balance and consistent snapshot history.')
    return [float(min(days, 180)), late / previous if previous else 0.0,
            float(min(broken, 4)), math.log1p(min(amount, 250000)), float(previous == 0)]


def sigmoid(value):
    if value >= 0:
        return 1 / (1 + math.exp(-value))
    exp = math.exp(value)
    return exp / (1 + exp)


def load_model(path=None):
    try:
        content = Path(path or ARTIFACT).read_bytes()
        model = json.loads(content)
        valid = (model['schema_version'] == 1 and model['feature_version'] == FEATURE_VERSION
                 and model['features'] == FEATURES and model['target'] == TARGET
                 and model['training_data']['synthetic'] is True
                 and model['model_type'] == 'standardized_logistic_regression'
                 and len(model['mean']) == len(model['scale']) == len(model['coefficients']) == len(FEATURES)
                 and all(math.isfinite(float(x)) for key in ['mean', 'scale', 'coefficients'] for x in model[key])
                 and all(x > 0 for x in model['scale']) and math.isfinite(model['intercept']))
        # Version binds every learned parameter and report field, not just a label.
        payload = {key: value for key, value in model.items() if key != 'model_version'}
        version = 'ar-logreg-30d-v1-' + hashlib.sha256(canonical(payload)).hexdigest()[:12]
        if not valid or model['model_version'] != version:
            raise ValueError('Unsupported model')
        model['artifact_sha256'] = hashlib.sha256(content).hexdigest()
        return model
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ModelError('Payment-risk artifact missing or invalid. Restore artifacts/payment_risk.json or retrain with python -m ml.train.') from exc


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def model_card(model):
    card = {key: model[key] for key in ['model_version', 'artifact_sha256', 'model_type',
        'feature_version', 'features', 'target', 'horizon_days', 'training_data', 'training_environment', 'evaluation', 'limitation']}
    card['parameters'] = {key: model[key] for key in ['mean', 'scale', 'coefficients', 'intercept']}
    return card


def score(model, values):
    if len(values) != len(FEATURES) or not all(math.isfinite(x) for x in values):
        raise ModelError('Unexpected model feature vector.')
    contributions = [coef * (value - mean) / scale for coef, value, mean, scale
                     in zip(model['coefficients'], values, model['mean'], model['scale'])]
    log_odds = model['intercept'] + sum(contributions)
    return sigmoid(log_odds), contributions


def predict_invoice(model, days, amount, previous, late, broken):
    values = feature_values(days, amount, previous, late, broken)
    probability, contributions = score(model, values)
    warnings = []
    if previous == 0:
        warnings.append('No previous-invoice history: rate defaults to zero with a separate no-history feature.')
    if days > 180 or float(amount) > 250000 or broken > 4 or float(amount) < 100 or previous > 40:
        warnings.append('Outside synthetic training ranges; capped transforms where defined. Treat as review-only evidence.')
    return {'status': 'scored', 'probability_unpaid_30d': round(probability, 6),
        'model_version': model['model_version'], 'artifact_sha256': model['artifact_sha256'],
        'features': dict(zip(FEATURES, values)), 'intercept_log_odds': model['intercept'],
        'contributions': [{'feature': name, 'value': value, 'log_odds_contribution': contribution,
                           'direction': 'increases' if contribution > 0 else 'decreases' if contribution < 0 else 'neutral'}
                          for name, value, contribution in zip(FEATURES, values, contributions)],
        'explanation_basis': 'Contributions relative to training feature means, in log-odds; associations, not causes.',
        'warnings': warnings}
