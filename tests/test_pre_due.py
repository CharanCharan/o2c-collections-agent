import copy
from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend import risk_model
from backend.main import create_app
from ml.generate_pre_due import generate
from ml.train import labeled_row, load_history, train
from tests.test_milestone_2 import finish

SEED = Path(__file__).resolve().parents[1] / 'sql/003_seed_pre_due.sql'


def add_pre_due(database):
    result = database.call(command='exec', sql=SEED.read_text())
    assert 'error' not in result, result


def test_pre_due_features_history_sensitivity_and_stage_separation():
    model = risk_model.load_model(stage='pre_due')
    low = risk_model.predict_pre_due(model, '28000', 10, 1, 0)
    high = risk_model.predict_pre_due(model, '28000', 10, 8, 1)
    assert low['probability_overdue'] < high['probability_overdue']
    assert 'days_overdue_capped' not in low['features']
    assert 'probability_unpaid_30d' not in low
    assert high['risk_type'] == 'pre_due_overdue'
    assert len(high['features']) == 4
    with pytest.raises(risk_model.ModelError):
        risk_model.load_model(risk_model.ARTIFACT, stage='pre_due')


def test_labels_due_day_and_following_day_and_scoring_cutoff(tmp_path):
    rows = generate(tmp_path / 'pre.csv', count=1200)
    row = rows[0].copy()
    snapshot, due = date.fromisoformat(row['snapshot_date']), date.fromisoformat(row['due_date'])
    row['settled_date'] = due.isoformat()
    on_time = labeled_row(row, 'pre_due')
    row['settled_date'] = (due + timedelta(days=1)).isoformat()
    late = labeled_row(row, 'pre_due')
    assert on_time[1] == late[1] and on_time[2] == 0 and late[2] == 1
    row['settled_date'] = ''
    row['outcome_observed_through'] = due.isoformat()
    with pytest.raises(ValueError, match='Immature'):
        labeled_row(row, 'pre_due')
    row['outcome_observed_through'] = (due + timedelta(days=1)).isoformat()
    row['snapshot_date'] = (snapshot + timedelta(days=1)).isoformat()
    with pytest.raises(ValueError, match='seven days'):
        labeled_row(row, 'pre_due')


def test_pre_due_reproducibility_temporal_split_and_sklearn_export(tmp_path):
    pytest.importorskip('sklearn', reason='Optional training: requirements-ml.txt')
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    a, b = tmp_path / 'a.csv', tmp_path / 'b.csv'
    generate(a, 1200); generate(b, 1200)
    assert a.read_bytes() == b.read_bytes()
    groups = load_history(a, 'pre_due')
    artifact = train(a, tmp_path / 'pre.json', stage='pre_due')
    x, y = np.array([r[1] for r in groups['train']]), np.array([r[2] for r in groups['train']])
    estimator = make_pipeline(StandardScaler(), LogisticRegression(C=artifact['evaluation']['selected_C'], max_iter=1000))
    estimator.fit(x, y)
    holdout = np.array([r[1] for r in groups['test']])
    actual = [risk_model.score(artifact, values)[0] for values in holdout]
    np.testing.assert_allclose(actual, estimator.predict_proba(holdout)[:, 1], rtol=0, atol=1e-12)
    np.testing.assert_allclose(artifact['mean'], x.mean(axis=0), atol=1e-12)
    assert risk_model.load_model(tmp_path / 'pre.json', stage='pre_due')['model_version'].startswith('ar-predue-7d-')
    for left, right in [('train', 'validation'), ('validation', 'test')]:
        assert date.fromisoformat(max(r[0] for r in groups[left])) + timedelta(days=8) < date.fromisoformat(min(r[0] for r in groups[right]))


def test_optional_seed_idempotence_totals_models_and_review_guards(database, store_factory):
    add_pre_due(database); add_pre_due(database)
    assert database.sql('select count(*) as n from ca_invoices')[0]['n'] == 9
    with TestClient(create_app(store_factory())) as client:
        card = client.get('/api/model/pre-due').json()
        run, events = finish(client)
        assert run['status'] == 'completed'
        result, rid = run['result'], run['run_id']
        summary = result['summary']
        assert summary['open_balance'] == '431700.00'
        assert summary['past_due_balance'] == '372200.00'
        assert summary['eligible_balance'] == '308000.00'
        assert summary['pre_due_balance'] == '59500.00'
        assert summary['preventive_review_count'] == 2 and summary['draft_count'] == 4
        assert result['models']['pre_due'] == card
        records = {r['id']: r for r in result['invoices']}
        high, low, future = [records[key] for key in ['INV-10501', 'INV-10502', 'INV-10503']]
        assert high['prediction']['probability_overdue'] > low['prediction']['probability_overdue']
        assert high['prediction']['scored_as_of'] == '2026-10-17'
        assert high['prediction']['horizon_date'] == '2026-10-24'
        assert high['prediction']['outcome_check_date'] == '2026-10-25'
        assert high['score'] is None and not high['eligible'] and high['preventive_eligible']
        assert high['draft'] is None
        assert client.post(f'/api/runs/{rid}/invoices/INV-10501/dry-run').status_code == 409
        assert future['prediction']['status'] == 'not_scored'
        prediction_event = next(e for e in events if e['stage'] == 'predict' and e['status'] == 'completed')
        assert prediction_event['result']['counts'] == {'overdue': 6, 'pre_due': 2, 'not_scored': 1}
        assert len(events) == 13


def test_pre_due_dispute_pauses_and_snapshot_changes_do_not_rewrite_old_run(database, store_factory):
    add_pre_due(database)
    with TestClient(create_app(store_factory())) as client:
        before, _ = finish(client)
        original = copy.deepcopy(before['result'])
        database.sql("update ca_invoices set disputed=true where id='INV-10501'")
        after, _ = finish(client)
        row = next(r for r in after['result']['invoices'] if r['id'] == 'INV-10501')
        assert row['prediction']['status'] == 'scored'
        assert not row['preventive_eligible'] and not row['eligible'] and row['draft'] is None
        assert 'dispute' in row['action']
        assert client.get(f"/api/runs/{before['run_id']}").json()['result'] == original
        database.sql("update ca_invoices set disputed=false,late_payments=0,broken_promises=0 where id='INV-10501'")
        changed, _ = finish(client)
        lower = next(r for r in changed['result']['invoices'] if r['id'] == 'INV-10501')
        earlier = next(r for r in original['invoices'] if r['id'] == 'INV-10501')
        assert lower['prediction']['probability_overdue'] < earlier['prediction']['probability_overdue']
        assert client.get(f"/api/runs/{before['run_id']}").json()['result'] == original


def test_window_boundary_and_transition_between_model_targets(database, store_factory):
    add_pre_due(database)
    with TestClient(create_app(store_factory())) as client:
        first, _ = finish(client)
        for remaining in [6, 0]:
            database.sql(f"update ca_invoices set due='2026-10-17'::date+{remaining} where id='INV-10501'")
            run, _ = finish(client)
            row = next(r for r in run['result']['invoices'] if r['id'] == 'INV-10501')
            assert row['prediction']['status'] == 'not_scored' and not row['preventive_eligible']
        database.sql("update ca_invoices set due='2026-10-16' where id='INV-10501'")
        overdue, _ = finish(client)
        row = next(r for r in overdue['result']['invoices'] if r['id'] == 'INV-10501')
        assert row['prediction']['risk_type'] == 'overdue_30d'
        assert 'probability_overdue' not in row['prediction'] and row['eligible']
        assert client.get(f"/api/runs/{first['run_id']}").json()['result']['models']['pre_due']


def test_missing_pre_due_model_fails_without_silent_single_model_fallback(store_factory, monkeypatch, tmp_path):
    monkeypatch.setattr(risk_model, 'PREDUE_ARTIFACT', tmp_path / 'missing-pre.json')
    with TestClient(create_app(store_factory())) as client:
        assert client.get('/api/health').status_code == 503
        assert client.get('/api/model/pre-due').status_code == 503
        assert client.get('/api/model').status_code == 200
        run, events = finish(client)
        assert run['status'] == 'failed' and events[-1]['stage'] == 'predict'
        assert 'pre_due' in events[-1]['error']['detail']
