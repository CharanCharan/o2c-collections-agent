"""Durable simulation dates and actual LangGraph follow-up tools; no live providers."""
import time
from pathlib import Path
from uuid import uuid4

import pytest

from tests.test_case_agent import client,job,seed,mock_language
from tests.test_milestone_2 import finish
from tests.test_milestone_5 import ResendMock,signed
from tests.test_visitor_cases import reply
from backend.public_demo import COOKIE

ROOT=Path(__file__).resolve().parents[1]


def find(c,invoice):return next(x for x in c.get('/api/cases').json()['cases'] if x['invoice_id']==invoice)


def promise(c,invoice):
    case=find(c,invoice)
    response=reply(c,case,text=f'We will pay invoice {invoice} on 2026-10-24.')
    assert response.status_code==200,response.text
    case=response.json()['case']
    if (case['workflow'].get('pending') or {}).get('tool')=='record_promise':
        response=c.post(f"/api/cases/{case['id']}/approve",json={'event_key':case['workflow']['pending']['event_key'],'approved':True})
        assert response.status_code==200,response.text
        case=response.json()['case']
    assert case['workflow']['status']=='promise_recorded',case['workflow']
    return case


def advance(c,value='2026-10-25'):
    response=c.post('/api/demo-clock',json={'demo_date':value})
    assert response.status_code==200,response.text
    return response.json()


def check(c,key=None):
    response=c.post('/api/followup-checks',json={'request_id':key or str(uuid4())})
    assert response.status_code==200,response.text
    ident=response.json()['job']['id']
    for _ in range(1500):
        response=c.get('/api/followup-checks/'+ident)
        assert response.status_code==200,response.text
        if response.json()['status']!='running':
            assert response.json()['status']=='completed',response.text
            return response.json()
        time.sleep(.005)
    pytest.fail('Due check did not finish')


def test_limited_promise_due_date_followup_send_delivery_and_dedup(store_factory,database):
    seed(database);language,calls=mock_language();provider=ResendMock()
    with client(store_factory,provider,language) as c:
        run,_=finish(c);job(c,run['run_id']);case=promise(c,'INV-10601');source=c.get('/api/portfolio').json()
        advance(c,'2026-10-24');check(c)
        assert find(c,'INV-10601')['workflow']['status']=='promise_recorded'
        advance(c);key=str(uuid4());result=check(c,key)
        case=find(c,'INV-10601');w=case['workflow']
        assert w['pending']['tool']=='send_followup_email' and w['followup']['draft']['remaining_amount']=='12000.00'
        assert not provider.sent and len(calls)==5
        response=c.post(f"/api/cases/{case['id']}/followup-email")
        assert response.status_code==200,response.text
        case=response.json()['case'];out=case['followups'][0]
        assert out['state']=='accepted' and len(provider.sent)==1 and case['outbound'] is None
        assert '2026-10-24' in out['body'] and '12,000.00' in out['body']
        raw,headers=signed({'type':'email.delivered','data':{'email_id':out['provider_id']}})
        assert c.post('/api/webhooks/resend',content=raw,headers=headers).status_code==200
        assert find(c,'INV-10601')['followups'][0]['events'][0]['type']=='email.delivered'
        check(c,key);check(c)
        assert len(provider.sent)==1 and len(find(c,'INV-10601')['followups'])==1
        assert c.get('/api/portfolio').json()==source
        assert len(calls)==5
        cookie=c.cookies.get(COOKIE)
    with client(store_factory,provider) as c:
        c.cookies.set(COOKIE,cookie)
        assert c.get('/api/demo-clock').json()['demo_date']=='2026-10-25'
        assert find(c,'INV-10601')['workflow']['followup']['status']=='accepted'


@pytest.mark.parametrize('invoice,expected,remaining',[('INV-10607','demo_payment_matched','0.00'),('INV-10608','awaiting_approval','15000.00'),('INV-10609','awaiting_approval','8500.00')])
def test_full_partial_unmatched_promises_check_evidence_before_draft(store_factory,database,invoice,expected,remaining):
    seed(database);language,calls=mock_language();provider=ResendMock()
    with client(store_factory,provider,language) as c:
        run,_=finish(c);job(c,run['run_id']);promise(c,invoice);advance(c);check(c)
        case=find(c,invoice);w=case['workflow']
        assert w['status']==expected and w['reconciliation']['remaining_amount']==remaining
        if remaining=='0.00':assert not w.get('followup') and w['pending'] is None
        else:assert w['followup']['draft']['remaining_amount']==remaining
        assert not provider.sent and len(calls)==5


def test_autopilot_due_check_sends_once_and_uses_case_mode(store_factory,database):
    seed(database);language,calls=mock_language();provider=ResendMock()
    with client(store_factory,provider,language) as c:
        run,_=finish(c);job(c,run['run_id'],'autopilot');promise(c,'INV-10601');advance(c)
        before=len(provider.sent);result=check(c)
        assert find(c,'INV-10601')['workflow']['followup']['status']=='accepted'
        assert 1<=len(provider.sent)-before<=3
        count=len(provider.sent);check(c)
        assert len(provider.sent)==count and len(calls)==5


def test_dispute_or_new_unsupported_reply_prevents_due_outreach(store_factory,database):
    seed(database);language,calls=mock_language();provider=ResendMock()
    with client(store_factory,provider,language) as c:
        run,_=finish(c);job(c,run['run_id']);case=promise(c,'INV-10601')
        response=reply(c,case,text='We dispute the price on this invoice.')
        assert response.status_code==200
        advance(c);check(c)
        case=find(c,'INV-10601')
        assert case['workflow']['status']=='dispute_hold_review_required' and not case['workflow'].get('followup')
        assert not provider.sent


def test_clock_scope_bounds_and_service_only_tables(store_factory,database):
    with client(store_factory) as a:
        clock=a.get('/api/demo-clock').json()
        assert clock['demo_date']=='2026-10-17'
        assert a.post('/api/demo-clock',json={'demo_date':'2026-10-16'}).status_code==409
        assert a.post('/api/demo-clock',json={'demo_date':'2028-01-01'}).status_code==409
        advance(a)
        with client(store_factory) as b:
            assert b.get('/api/demo-clock').json()['demo_date']=='2026-10-17'
            done=check(a)
            assert b.get('/api/followup-checks/'+done['id']).status_code==404
            assert b.post('/api/followup-checks/'+done['id']+'/resume').status_code==404
    database.sql('set role anon')
    try:
        assert 'error' in database.call(command='sql',sql='select * from ca_demo_clocks')
        assert 'error' in database.call(command='sql',sql="select ca_demo_clock('x')")
        assert 'error' in database.call(command='sql',sql='select ca_mail_public(null)')
    finally:database.sql('reset role')


def test_followup_migration_reapply_preserves_history(store_factory,database):
    seed(database)
    with client(store_factory) as c:
        run,_=finish(c);job(c,run['run_id']);advance(c)
        assert database.call(command='exec',sql=(ROOT/'sql/012_promise_followups.sql').read_text())['data']
        assert len(c.get('/api/cases').json()['cases'])==24
        assert c.get('/api/demo-clock').json()['demo_date']=='2026-10-25'
        assert c.get('/api/health').json()['followups']['ready']


def test_new_dispute_supersedes_pending_followup_and_stale_approval(store_factory,database):
    seed(database);language,calls=mock_language();provider=ResendMock()
    with client(store_factory,provider,language) as c:
        run,_=finish(c);job(c,run['run_id']);promise(c,'INV-10601');advance(c);check(c)
        case=find(c,'INV-10601');key=case['workflow']['pending']['event_key']
        assert reply(c,case,text='We dispute this invoice.').status_code==200
        assert c.post(f"/api/cases/{case['id']}/approve",json={'event_key':key,'approved':True}).status_code==409
        assert c.post(f"/api/cases/{case['id']}/followup-email").status_code==409
        assert not provider.sent


def test_unknown_followup_no_automatic_retry_but_explicit_same_intent(store_factory,database):
    seed(database);provider=ResendMock()
    with client(store_factory,provider) as c:
        run,_=finish(c);job(c,run['run_id']);advance(c);check(c)
        case=find(c,'INV-10602');provider.fail=True
        response=c.post(f"/api/cases/{case['id']}/followup-email")
        assert response.status_code==200,response.text
        case=response.json()['case'];assert case['workflow']['followup']['status']=='unknown'
        ident=case['followups'][0]['id'];attempts=len(provider.sent)
        check(c);assert len(provider.sent)==attempts
        provider.fail=False
        response=c.post(f"/api/cases/{case['id']}/followup-email")
        assert response.status_code==200,response.text
        assert response.json()['case']['followups'][0]['id']==ident
        assert response.json()['case']['workflow']['followup']['status']=='accepted'
        assert len(provider.sent)==attempts+1


def test_daily_email_quota_wait_and_explicit_retry(store_factory,database):
    seed(database);provider=ResendMock()
    with client(store_factory,provider) as c:
        run,_=finish(c);job(c,run['run_id']);advance(c);check(c);case=find(c,'INV-10602')
        database.sql("insert into ca_mail_messages(id,run_id,invoice_id,payload,reply_to) select gen_random_uuid(),$1,'quota-'||n,'{}'::jsonb,'quota-'||n||'@demo.resend.app' from generate_series(1,10)n",[run['run_id']])
        response=c.post(f"/api/cases/{case['id']}/followup-email")
        assert response.status_code==200,response.text
        assert response.json()['case']['workflow']['followup']['status']=='quota_wait'
        assert not provider.sent
        database.sql("delete from ca_mail_messages where invoice_id like 'quota-%'")
        response=c.post(f"/api/cases/{case['id']}/followup-email")
        assert response.status_code==200,response.text
        assert response.json()['case']['workflow']['followup']['status']=='accepted' and len(provider.sent)==1


def test_interrupted_due_job_resumes_saved_authority_without_duplicates(store_factory,database,monkeypatch):
    from backend.storage import StorageError
    seed(database);language,calls=mock_language();provider=ResendMock()
    with client(store_factory,provider,language) as c:
        run,_=finish(c);job(c,run['run_id'],'autopilot');promise(c,'INV-10601');advance(c)
        agent=c.app.state.agent;original=agent.invoke;seen=[0]
        async def fail_second(*args,**kwargs):
            seen[0]+=1
            if seen[0]==2:raise StorageError('Test interruption')
            return await original(*args,**kwargs)
        monkeypatch.setattr(agent,'invoke',fail_second)
        response=c.post('/api/followup-checks',json={'request_id':str(uuid4())});ident=response.json()['job']['id']
        for _ in range(1000):
            saved=c.get('/api/followup-checks/'+ident).json()
            if saved['status']!='running':break
            time.sleep(.005)
        assert saved['status']=='interrupted'
        assert c.post('/api/demo-clock',json={'demo_date':'2026-10-26'}).status_code==409
        assert c.post('/api/followup-checks',json={'request_id':str(uuid4())}).status_code==409
        reserved=saved['progress']['auto_case_ids']
        monkeypatch.setattr(agent,'invoke',original)
        response=c.post('/api/followup-checks/'+ident+'/resume');assert response.status_code==200
        for _ in range(1000):
            saved=c.get('/api/followup-checks/'+ident).json()
            if saved['status']!='running':break
            time.sleep(.005)
        assert saved['status']=='completed' and set(reserved)<=set(saved['progress']['auto_case_ids'])
        assert len(saved['progress']['auto_case_ids'])<=3
        total=len(provider.sent);check(c);assert len(provider.sent)==total


def test_accepted_followup_survives_effect_checkpoint_failure_without_resend(store_factory,database,monkeypatch):
    from backend.storage import StorageError
    seed(database);provider=ResendMock()
    with client(store_factory,provider) as c:
        run,_=finish(c);job(c,run['run_id']);advance(c);check(c);case=find(c,'INV-10602')
        store=c.app.state.agent.store;original=store.rpc;failed=[False]
        async def fail_once(name,body=None):
            if name=='ca_workflow_effect' and body.get('p_tool')=='send_followup_email' and not failed[0]:
                failed[0]=True;raise StorageError('Test failed effect persistence after acceptance')
            return await original(name,body)
        monkeypatch.setattr(store,'rpc',fail_once)
        response=c.post(f"/api/cases/{case['id']}/followup-email")
        assert response.status_code==503 and len(provider.sent)==1
        response=c.post(f"/api/cases/{case['id']}/resume")
        assert response.status_code==200,response.text
        assert response.json()['case']['workflow']['followup']['status']=='accepted'
        assert len(provider.sent)==1


def test_autopilot_due_check_reserves_at_most_three_automatic_followups(store_factory,database):
    seed(database);language,calls=mock_language();provider=ResendMock()
    with client(store_factory,provider,language) as c:
        run,_=finish(c);job(c,run['run_id'],'autopilot')
        for invoice in ['INV-10601','INV-10603','INV-10608','INV-10609']:promise(c,invoice)
        advance(c);before=len(provider.sent);result=check(c)
        assert len(result['progress']['auto_case_ids'])==3
        assert len(provider.sent)-before==3
        cases=c.get('/api/cases').json()['cases']
        assert sum((x['workflow'].get('pending') or {}).get('tool')=='send_followup_email' for x in cases)==2
        assert len(calls)==8


def test_draft_patch_before_node_checkpoint_replays_into_approval(store_factory,database,monkeypatch):
    from backend.storage import StorageError
    seed(database);provider=ResendMock()
    with client(store_factory,provider) as c:
        run,_=finish(c);job(c,run['run_id']);advance(c)
        agent=c.app.state.agent;original=agent.patch;failed=[False]
        async def fail_after_draft(s,patch,node,message,status='completed'):
            value=await original(s,patch,node,message,status)
            if node=='plan_followup' and patch.get('followup') and not failed[0]:
                failed[0]=True;raise StorageError('Test crash after draft business patch')
            return value
        monkeypatch.setattr(agent,'patch',fail_after_draft)
        response=c.post('/api/followup-checks',json={'request_id':str(uuid4())});ident=response.json()['job']['id']
        for _ in range(1000):
            saved=c.get('/api/followup-checks/'+ident).json()
            if saved['status']!='running':break
            time.sleep(.005)
        assert saved['status']=='interrupted'
        assert c.post('/api/followup-checks/'+ident+'/resume').status_code==200
        for _ in range(1000):
            saved=c.get('/api/followup-checks/'+ident).json()
            if saved['status']!='running':break
            time.sleep(.005)
        assert saved['status']=='completed'
        case=find(c,'INV-10602')
        assert case['workflow']['pending']['tool']=='send_followup_email'
        assert c.post(f"/api/cases/{case['id']}/followup-email").status_code==200
        assert len(provider.sent)==1
