"""Optional SQL budget settings: no counter reset, same durable reservations."""
from pathlib import Path
from fastapi.testclient import TestClient
from tests.test_milestone_6 import app_for

ROOT=Path(__file__).resolve().parents[1]


def reserve(database, actor, kind='llm', owner=False):
    response=database.call(command='rpc',name='ca_public_reserve',params={
        'p_actor':actor,'p_kind':kind,'p_owner':owner})
    assert 'error' not in response,response
    return response['data']


def test_optional_budget_preserves_usage_and_enforces_new_caps_and_health(store_factory,database):
    for _ in range(8):assert reserve(database,'existing-browser')
    assert not reserve(database,'existing-browser')
    old_usage=database.sql('select * from ca_demo_usage order by actor')
    try:
        sql=(ROOT/'sql/016_demo_llm_budget.sql').read_text()
        for _ in range(2):assert database.call(command='exec',sql=sql).get('data') is True
        assert database.sql('select * from ca_demo_usage order by actor')==old_usage
        for _ in range(32):assert reserve(database,'existing-browser')
        assert not reserve(database,'existing-browser')
        # Every actor still shares a single global daily allowance.
        for index in range(60):assert reserve(database,'visitor-'+str(index))
        assert not reserve(database,'another-browser')
        assert not reserve(database,'webhook')
        assert not reserve(database,'owner',owner=True)
        for _ in range(50):assert reserve(database,'existing-browser','run')
        with TestClient(app_for(store_factory),base_url='https://demo.test') as c:
            status=c.get('/api/health');assert status.status_code==200,status.text
            assert status.json()['public_demo']['daily_llm_attempt_cap']==100
            assert status.json()['public_demo']['per_browser_llm_attempts']==40
            assert status.json()['public_demo']['daily_run_limit_enabled'] is False
        database.sql('set role anon')
        try:assert 'error' in database.call(command='sql',sql='select ca_llm_budget()')
        finally:database.sql('reset role')
    finally:
        assert database.call(command='exec',sql=(ROOT/'sql/011_unlimited_demo_starts.sql').read_text()).get('data') is True


def test_health_reports_original_caps_without_optional_migration(store_factory):
    with TestClient(app_for(store_factory),base_url='https://demo.test') as c:
        data=c.get('/api/health').json()['public_demo']
        assert data['daily_llm_attempt_cap']==40 and data['per_browser_llm_attempts']==8
