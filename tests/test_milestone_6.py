"""Public-mode contracts under HTTPS cookies, real isolated SQL, no live APIs."""
import json
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from backend.language import LanguageService
from backend.main import create_app
from backend.public_demo import COOKIE, PublicConfig
from tests.test_milestone_2 import finish,decode_events
from tests.test_milestone_5 import CONFIG,TOKEN,AUTH,ResendMock
from tests.test_llm_providers import mock_groq

PUBLIC=PublicConfig(enabled=True,secret='different-session-secret-12345678901234567890',owner_token=TOKEN)


def app_for(store_factory,language=None,config=PUBLIC):
    return create_app(store_factory(),language=language or LanguageService(),public_config=config)


def test_https_session_run_history_isolation_and_all_mutation_routes(store_factory):
    with TestClient(app_for(store_factory),base_url='https://demo.test') as a:
        run,_=finish(a);rid=run['run_id']
        cookie=a.cookies.get(COOKIE)
        assert cookie and a.get('/api/runs').json()['runs'][0]['run_id']==rid
        headers=a.get('/').headers
        assert 'Secure' in headers['set-cookie'] and 'HttpOnly' in headers['set-cookie'] and 'SameSite=lax' in headers['set-cookie']
        with TestClient(app_for(store_factory),base_url='https://demo.test') as b:
            assert b.get('/api/runs').json()['runs']==[]
            assert b.get(f'/api/runs/{rid}').status_code==404
            assert b.get(f'/api/runs/{rid}/events').status_code==404
            assert b.post(f'/api/runs/{rid}/invoices/INV-10287/dry-run').status_code==404
            assert b.post(f'/api/runs/{rid}/invoices/INV-10287/classify-example',json={'example_id':'paid'}).status_code==404
            assert b.get(f'/api/runs/{rid}/email').status_code==401
            b.cookies.set(COOKIE,cookie+'tampered')
            assert b.get(f'/api/runs/{rid}').status_code==404


def test_run_daily_quota_and_cookie_survives_restart(store_factory,database):
    with TestClient(app_for(store_factory),base_url='https://demo.test') as c:
        for _ in range(3):finish(c)
        assert c.post('/api/runs').status_code==429
        cookie=c.cookies.get(COOKIE)
    with TestClient(app_for(store_factory),base_url='https://demo.test') as fresh:
        fresh.cookies.set(COOKIE,cookie)
        assert len(fresh.get('/api/runs').json()['runs'])==3
        assert fresh.post('/api/runs').status_code==429
    assert database.sql("select attempts from ca_demo_usage where actor='global' and kind='run'")[0]['attempts']==3


def test_global_run_cap_is_not_bypassed_by_new_cookies(store_factory,database):
    for index in range(20):
        assert database.call(command='rpc',name='ca_public_reserve',params={'p_actor':str(index),'p_kind':'run'})['data']
    with TestClient(app_for(store_factory),base_url='https://demo.test') as c:
        assert c.post('/api/runs').status_code==429
        assert c.get('/api/runs').json()['runs']==[]
    assert database.sql('select count(*) as count from ca_run_access')[0]['count']==0


def test_private_email_events_removed_from_run_sse_and_action_responses(store_factory,database):
    with TestClient(app_for(store_factory),base_url='https://demo.test') as c:
        run,_=finish(c);rid=run['run_id']
        database.sql("select ca_mail_event($1,'followup_scheduled','completed','private-owner-message',$2)",
            [rid,json.dumps({'evidence_quote':'private inbox quote owner@example.com'})])
        data=c.get(f'/api/runs/{rid}').json()
        assert 'private inbox' not in json.dumps(data) and len(data['events'])==13
        events=decode_events(c.get(f'/api/runs/{rid}/events').text)
        assert len(events)==13 and 'private-owner-message' not in json.dumps(events)
        response=c.post(f'/api/runs/{rid}/invoices/INV-10287/dry-run')
        assert 'private inbox' not in response.text
        response=c.post(f'/api/runs/{rid}/invoices/INV-10287/classify-example',json={'example_id':'paid'})
        assert 'private inbox' not in response.text
        owner=c.get(f'/api/runs/{rid}',headers=AUTH)
        assert 'private inbox' in owner.text


def test_owner_login_private_access_logout_and_csrf(store_factory):
    with TestClient(app_for(store_factory),base_url='https://demo.test') as owner:
        run,_=finish(owner);rid=run['run_id']
        assert owner.post('/api/operator/login',headers={'X-Collections-Owner':'wrong'}).status_code==401
        assert owner.post('/api/operator/login',headers=AUTH).status_code==200
        assert owner.get(f'/api/runs/{rid}/email').status_code==200
        assert owner.post('/api/runs',headers={'Origin':'https://attacker.test'}).status_code==403
        assert owner.post('/api/operator/logout',headers={'Origin':'https://demo.test'}).status_code==200
        assert owner.get(f'/api/runs/{rid}/email').status_code==401


def test_llm_per_browser_budget_and_restart_use_sql_not_only_process_counter(store_factory,database):
    language,requests=mock_groq()
    with TestClient(app_for(store_factory,language),base_url='https://demo.test') as c:
        for _ in range(2):
            run,_=finish(c)
            assert run['result']['drafting']['counts']['llm']==4
        run,_=finish(c)
        assert run['result']['drafting']['counts']['fallback']==4 and len(requests)==8
        cookie=c.cookies.get(COOKIE)
    assert database.sql("select attempts from ca_demo_usage where actor='global' and kind='llm'")[0]['attempts']==8
    fresh_language,fresh_requests=mock_groq()
    with TestClient(app_for(store_factory,fresh_language),base_url='https://demo.test') as c:
        c.cookies.set(COOKIE,cookie)
        # A new synthetic example still uses the original browser's exhausted LLM budget.
        response=c.post(f"/api/runs/{run['run_id']}/invoices/INV-10287/classify-example",json={'example_id':'paid'})
        assert response.status_code==200 and not fresh_requests
        assert response.json()['run']['events'][-1]['result']['review']['status']=='manual_review'


def test_llm_global_quota_applies_to_new_browser_and_webhook_actor(store_factory,database):
    for index in range(40):
        assert database.call(command='rpc',name='ca_public_reserve',params={'p_actor':'test'+str(index),'p_kind':'llm'})['data']
    language,requests=mock_groq()
    with TestClient(app_for(store_factory,language),base_url='https://demo.test') as c:
        run,_=finish(c)
        assert run['result']['drafting']['counts']['fallback']==4 and not requests
    assert database.call(command='rpc',name='ca_public_reserve',params={'p_actor':'webhook','p_kind':'llm'})['data'] is False


def test_public_mode_blocks_paid_provider_even_if_run_skips_health(store_factory):
    from tests.test_milestone_4 import mock_service
    language,requests=mock_service()
    with TestClient(app_for(store_factory,language),base_url='https://demo.test') as c:
        run,_=finish(c)
        assert not requests and run['result']['drafting']['counts']['fallback']==4
        assert c.get('/api/health').status_code==503


@pytest.mark.parametrize('config',[
    replace(PUBLIC,secret=''),
    replace(PUBLIC,secret=TOKEN),replace(PUBLIC,enabled=False,cloud=True),replace(PUBLIC,invalid=True),
])
def test_cloud_configuration_fail_closed(store_factory,config):
    with TestClient(app_for(store_factory,config=config),base_url='https://demo.test') as c:
        assert c.get('/').status_code==503
        assert c.post('/api/runs').status_code==503


def test_webhook_probe_is_public_but_actual_post_still_needs_signature(store_factory):
    from backend.mail.signatures import verify
    from tests.test_milestone_5 import signed
    import httpx
    provider=ResendMock()
    app=create_app(store_factory(),language=LanguageService(),mail_config=CONFIG,
        mail_transport=httpx.MockTransport(provider.handler),public_config=PUBLIC)
    with TestClient(app,base_url='https://demo.test') as c:
        assert c.get('/livez').json()['milestone']=='M6'
        probe=c.get('/api/webhooks/resend')
        assert probe.status_code==200 and probe.json()['status']=='reachable'
        assert c.post('/api/webhooks/resend',content=b'{}').status_code==401
        assert not provider.sent


def test_public_tables_and_functions_deny_anon(database):
    database.sql('set role anon')
    try:
        assert 'error' in database.call(command='sql',sql='select * from ca_demo_usage')
        assert 'error' in database.call(command='sql',sql="select ca_public_reserve('actor','llm')")
    finally:database.sql('reset role')


def test_budget_database_outage_blocks_provider_egress(store_factory,monkeypatch):
    from backend.storage import StorageError
    store=store_factory();original=store.rpc
    async def rpc(name,body=None):
        if name=='ca_public_reserve':raise StorageError('Test budget storage unavailable.')
        return await original(name,body)
    monkeypatch.setattr(store,'rpc',rpc)
    language,requests=mock_groq()
    with TestClient(create_app(store,language=language,public_config=PUBLIC),base_url='https://demo.test') as c:
        run,_=finish(c)
        assert run['result']['drafting']['counts']['fallback']==4 and not requests
        assert not any(r.get('draft_audit',{}).get('api_attempted') for r in run['result']['invoices'])
