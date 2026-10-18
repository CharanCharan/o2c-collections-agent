"""Fresh browser workspace; retain provider receipts, source AR and durable quotas."""
import hashlib
from backend.public_demo import COOKIE,PublicAccess
from tests.test_case_agent import client,job,mock_language
from tests.test_milestone_2 import finish
from tests.test_milestone_5 import ResendMock
from tests.test_milestone_6 import PUBLIC


def session(c):
    return PublicAccess(PUBLIC,None).decode(c.cookies.get(COOKIE))


def test_fresh_workspace_preserves_business_data_and_uses_current_llm_mode(store_factory,database):
    provider=ResendMock()
    with client(store_factory,provider) as c:
        run,_=finish(c);job(c,run['run_id'])
        old=c.get('/api/cases').json()['cases'];case=next(x for x in old if x['invoice_id']=='INV-10287')
        assert c.post(f"/api/cases/{case['id']}/send-email").status_code==200
        assert len(provider.sent)==1
        initial=session(c)
        # Advancing this workspace clock must not affect the next workspace.
        assert c.post('/api/demo-clock',json={'demo_date':'2026-10-25'}).status_code==200
        before=database.sql('select (select count(*) from ca_collection_cases) cases,(select count(*) from ca_graph_checkpoints) checkpoints,(select count(*) from ca_mail_messages) mails,(select count(*) from ca_demo_usage) counters')
        invoices=database.sql('select * from ca_invoices order by id')
        result=c.post('/api/demo/fresh')
        assert result.status_code==200,result.text
        assert result.json()=={'fresh':True,'source_reset':False,'usage_reset':False}
        fresh=session(c)
        assert fresh['id']!=initial['id'] and fresh['budget_id']==initial['id'] and fresh['owner_until']==0
        assert c.get('/api/cases').json()['cases']==[]
        assert c.get('/api/runs').json()['runs']==[]
        assert c.get('/api/agent-jobs').json()['job'] is None
        assert c.get(f"/api/runs/{run['run_id']}").status_code==404
        assert c.post(f"/api/cases/{case['id']}/send-email").status_code==404
        assert c.get('/api/demo-clock').json()['demo_date']=='2026-10-17'
        assert database.sql('select (select count(*) from ca_collection_cases) cases,(select count(*) from ca_graph_checkpoints) checkpoints,(select count(*) from ca_mail_messages) mails,(select count(*) from ca_demo_usage) counters')==before
        assert database.sql('select * from ca_invoices order by id')==invoices
        assert 'set-cookie' not in c.get('/api/cases').headers
        cookie=c.cookies.get(COOKIE)
    language,calls=mock_language()
    with client(store_factory,provider,language) as c:
        c.cookies.set(COOKIE,cookie)
        run,_=finish(c);result=job(c,run['run_id'],'autopilot')
        current=c.get('/api/cases').json()['cases']
        assert len(calls)==4 and len(provider.sent)==4
        assert all(x['workflow']['mode']=='autopilot' for x in current)
        assert not ({x['id'] for x in current}&{x['id'] for x in old})
        assert next(x for x in current if x['invoice_id']=='INV-10287')['snapshot']['invoice']['draft']['generation_mode']=='llm_assisted_validated_facts'
        assert result['progress']['retained']==0


def test_fresh_demo_keeps_same_browser_llm_budget(store_factory,database):
    language,calls=mock_language()
    with client(store_factory,language=language) as c:
        c.get('/api/cases');initial=session(c);budget=hashlib.sha256(initial['id'].encode()).hexdigest()
        for round in range(3):
            if round:assert c.post('/api/demo/fresh').status_code==200
            finish(c)
        assert len(calls)==8  # Third workspace cannot refill the eight-attempt allowance.
        assert database.sql("select attempts from ca_demo_usage where actor=$1 and kind='llm'",[budget])[0]['attempts']==8
        assert database.sql("select attempts from ca_demo_usage where actor='global' and kind='llm'")[0]['attempts']==8


def test_fresh_demo_blocked_during_run_and_cross_origin(store_factory,database):
    with client(store_factory) as c:
        run,_=finish(c);before=c.cookies.get(COOKIE);actor=hashlib.sha256(session(c)['id'].encode()).hexdigest()
        assert 'error' not in database.call(command='rpc',name='ca_agent_plan',params={'p_session_key':actor,'p_run_id':run['run_id'],'p_mode':'limited'})
        response=c.post('/api/demo/fresh')
        assert response.status_code==409 and c.cookies.get(COOKIE)==before
        response=c.post('/api/demo/fresh',headers={'Origin':'https://elsewhere.test'})
        assert response.status_code==403 and c.cookies.get(COOKIE)==before


def test_fresh_demo_checks_in_process_work_even_without_latest_database_job(store_factory):
    import asyncio
    with client(store_factory) as c:
        c.get('/api/cases');before=c.cookies.get(COOKIE);actor=hashlib.sha256(session(c)['id'].encode()).hexdigest()
        tasks=[]
        @c.app.post('/qa/start-held-action')
        async def held():
            task=asyncio.create_task(asyncio.Event().wait())
            c.app.state.runs.track_task(task,actor);tasks.append(task)
            return {'ok':True}
        @c.app.post('/qa/release-held-action')
        async def release():
            for task in tasks:task.cancel()
            await asyncio.gather(*tasks,return_exceptions=True)
            return {'ok':True}
        assert c.post('/qa/start-held-action').status_code==200
        assert c.post('/api/demo/fresh').status_code==409
        assert c.cookies.get(COOKIE)==before
        assert c.post('/qa/release-held-action').status_code==200
        assert c.post('/api/demo/fresh').status_code==200
