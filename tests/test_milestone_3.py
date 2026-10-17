import copy
import json
import math
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from backend import pipeline, risk_model
from backend.main import create_app
from ml.generate import generate
from ml.train import labeled_row, load_history
from tests.test_milestone_2 import finish


def test_learned_artifact_explanations_and_history_sensitivity():
    model = risk_model.load_model()
    low = risk_model.predict_invoice(model, 30, '50000', 10, 1, 0)
    high = risk_model.predict_invoice(model, 30, '50000', 10, 9, 2)
    assert 0 < low['probability_unpaid_30d'] < high['probability_unpaid_30d'] < 1
    logit = low['intercept_log_odds'] + sum(c['log_odds_contribution'] for c in low['contributions'])
    assert abs(1 / (1 + math.exp(-logit)) - low['probability_unpaid_30d']) < 5e-7
    assert list(low['features']) == risk_model.FEATURES
    assert 'settled_date' not in low['features']
    missing = risk_model.predict_invoice(model, 25, '1000', 0, 0, 0)
    assert missing['features']['no_history'] == 1 and missing['warnings']
    extreme = risk_model.predict_invoice(model, 999, '999999999', 10, 3, 9)
    assert extreme['features']['days_overdue_capped'] == 180 and extreme['warnings']


def test_reject_missing_corrupt_or_incompatible_artifact(tmp_path):
    with pytest.raises(risk_model.ModelError):
        risk_model.load_model(tmp_path / 'absent.json')
    data = json.loads(risk_model.ARTIFACT.read_text())
    data['coefficients'][0] += 1  # Stale identity after changing trained parameters.
    corrupt = tmp_path / 'model.json'
    corrupt.write_text(json.dumps(data))
    with pytest.raises(risk_model.ModelError):
        risk_model.load_model(corrupt)
    corrupt.write_text('{bad json')
    with pytest.raises(risk_model.ModelError):
        risk_model.load_model(corrupt)


def test_generator_reproducibility_temporal_maturity_and_no_overlap(tmp_path):
    a, b = tmp_path / 'a.csv', tmp_path / 'b.csv'
    rows = generate(a, 1200, 42)
    generate(b, 1200, 42)
    assert a.read_bytes() == b.read_bytes()
    groups = load_history(a)
    for left, right in [('train', 'validation'), ('validation', 'test')]:
        latest_label = date.fromisoformat(max(r[0] for r in groups[left])) + timedelta(days=30)
        earliest_score = date.fromisoformat(min(r[0] for r in groups[right]))
        assert latest_label < earliest_score
    example = rows[0].copy()
    snapshot = date.fromisoformat(example['snapshot_date'])
    example['outcome_observed_through'] = (snapshot + timedelta(days=29)).isoformat()
    with pytest.raises(ValueError, match='Immature'):
        labeled_row(example)
    example['outcome_observed_through'] = (snapshot + timedelta(days=30)).isoformat()
    example['settled_date'] = (snapshot + timedelta(days=30)).isoformat()
    before = labeled_row(example)
    example['settled_date'] = ''
    after = labeled_row(example)
    assert before[1] == after[1] and before[2] == 0 and after[2] == 1


def test_export_matches_independent_sklearn_prediction_and_train_only_scaler(tmp_path):
    pytest.importorskip('sklearn', reason='Optional offline training: install requirements-ml.txt')
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from ml.train import train
    data = tmp_path / 'history.csv'
    generate(data, 1200, 42)
    artifact = train(data, tmp_path / 'trained.json')
    groups = load_history(data)
    x, y = np.array([r[1] for r in groups['train']]), np.array([r[2] for r in groups['train']])
    estimator = make_pipeline(StandardScaler(), LogisticRegression(C=artifact['evaluation']['selected_C'], max_iter=1000))
    estimator.fit(x, y)
    holdout = np.array([r[1] for r in groups['test']])
    actual = np.array([risk_model.score(artifact, values)[0] for values in holdout])
    np.testing.assert_allclose(actual, estimator.predict_proba(holdout)[:, 1], atol=1e-12, rtol=0)
    np.testing.assert_allclose(artifact['mean'], x.mean(axis=0), atol=1e-12)
    model = risk_model.load_model(tmp_path / 'trained.json')
    assert model['model_version'].startswith('ar-logreg-30d-v1-')
    test = artifact['evaluation']['splits']['test']
    assert test['logistic']['brier'] < test['constant_baseline']['brier']


def test_live_pipeline_persists_model_and_preserves_policy(store_factory, database):
    with TestClient(create_app(store_factory())) as client:
        health = client.get('/api/health').json()
        assert health['milestone'] == 'M6' and health['stage_count'] == 6
        card = client.get('/api/model').json()
        assert card['training_data']['synthetic'] is True
        run, events = finish(client)
        assert len(events) == 13 and run['status'] == 'completed'
        output = run['result']
        assert output['model'] == card
        model_event = next(e for e in events if e['stage'] == 'predict' and e['status'] == 'completed')
        assert model_event['result']['scored_count'] == 6
        assert output['ranking_formula'].startswith('open_balance * probability')
        for row in output['invoices']:
            assert row['prediction']['model_version'] == card['model_version']
            assert row['prediction']['horizon_date'] == '2026-11-16'
            if row['dispute']:
                assert not row['draft'] and not row['eligible']
        baseline = copy.deepcopy(output)
        database.sql("update ca_invoices set late_payments=0,broken_promises=0 where id='INV-10287'")
        updated, _ = finish(client)
        saved = client.get(f"/api/runs/{run['run_id']}").json()['result']
        assert saved == baseline
        old = next(r for r in output['invoices'] if r['id'] == 'INV-10287')
        new = next(r for r in updated['result']['invoices'] if r['id'] == 'INV-10287')
        assert new['prediction']['probability_unpaid_30d'] < old['prediction']['probability_unpaid_30d']


def test_nonoverdue_and_zero_balance_are_not_scored(store_factory, database):
    database.sql("update ca_invoices set due='2026-10-18' where id='INV-10482'")
    database.sql("update ca_invoices set amount=0 where id='INV-10431'")
    with TestClient(create_app(store_factory())) as client:
        run, _ = finish(client)
        assert run['status'] == 'completed'
        excluded = [r for r in run['result']['invoices'] if r['id'] in ['INV-10482', 'INV-10431']]
        assert len(excluded) == 2
        for row in excluded:
            assert row['prediction']['status'] == 'not_scored'
            assert row['priority_index'] == '0.00'
            assert row['draft'] is None and not row['eligible']


def test_missing_model_fails_health_and_run_truthfully(store_factory, monkeypatch, tmp_path):
    monkeypatch.setattr(risk_model, 'ARTIFACT', tmp_path / 'missing.json')
    with TestClient(create_app(store_factory())) as client:
        assert client.get('/api/health').status_code == 503
        assert client.get('/api/model').status_code == 503
        run, events = finish(client)
        assert run['status'] == 'failed'
        assert events[-1]['stage'] == 'predict' and events[-1]['error']['type'] == 'ModelError'
        assert not any(e['stage'] == 'run' and e['status'] == 'completed' for e in events)
        assert not any(r['draft'] for r in run['result']['invoices'])


def test_ranking_uses_risk_not_urgency_and_dispute_stays_last():
    context = pipeline.Context()
    context.invoices = [
        {'id': 'a', 'amount': '100.00', 'days': 5, 'eligible': True, 'customer': 'A', 'score': 90,
         'prediction': {'probability_unpaid_30d': .1}},
        {'id': 'b', 'amount': '100.00', 'days': 5, 'eligible': True, 'customer': 'B', 'score': 10,
         'prediction': {'probability_unpaid_30d': .8}},
        {'id': 'c', 'amount': '10000.00', 'days': 5, 'eligible': False, 'customer': 'Dispute', 'score': 99,
         'prediction': {'probability_unpaid_30d': .9}},
    ]
    pipeline.prioritize(context)
    assert [r['id'] for r in context.invoices] == ['b', 'a', 'c']
