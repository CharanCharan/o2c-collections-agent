"""Run outcome evidence with actual SQL and mocked providers; no live calls."""
from copy import deepcopy
from tests.test_case_agent import client,job
from tests.test_milestone_2 import finish
from tests.test_milestone_5 import ResendMock
from backend.public_demo import COOKIE


def results(report):
    return [v['result'] for v in report['invoices'].values() if v['completed']]


def test_run_report_frozen_approvals_and_new_run_do_not_claim_old_email(store_factory):
    provider=ResendMock()
    with client(store_factory,provider) as c:
        run,_=finish(c);rid=run['run_id'];saved=job(c,rid)
        report=deepcopy(saved['progress']['report'])
        assert len(results(report))==6
        assert sum(len(x['initial_mail_ids']) for x in results(report))==0
        assert sum(x['dispute_on_hold'] for x in results(report))==1
        case=next(x for x in c.get('/api/cases').json()['cases'] if x['workflow'].get('pending'))
        assert c.post(f"/api/cases/{case['id']}/send-email").status_code==200
        assert len(provider.sent)==1
        assert c.get(f'/api/runs/{rid}/agent').json()['progress']['report']==report
        second,_=finish(c);new=job(c,second['run_id'],'autopilot')
        assert sum(len(x['initial_mail_ids']) for x in results(new['progress']['report']))==0
        assert len(provider.sent)==1
        cookie=c.cookies.get(COOKIE)
    with client(store_factory,provider) as c:
        c.cookies.set(COOKIE,cookie)
        assert c.get(f'/api/runs/{rid}/agent').json()['progress']['report']==report


def test_report_autopilot_counts_distinct_accepted_and_resume_keeps_baseline(store_factory,database):
    provider=ResendMock()
    with client(store_factory,provider) as c:
        run,_=finish(c);rid=run['run_id'];saved=job(c,rid,'autopilot')
        progress=saved['progress'];entries=progress['report']['invoices']
        assert sum(len(x['initial_mail_ids']) for x in results(progress['report']))==3
        accepted=next(v for v in entries.values() if v['result']['initial_mail_ids'])
        baseline=deepcopy(accepted['before']);accepted['completed']=False
        # Model a crash after email and business state persisted, before report commit.
        database.sql("update ca_agent_jobs set status='interrupted',progress=$1::jsonb where run_id=$2",[__import__('json').dumps(progress),rid])
        resumed=job(c,rid,'autopilot')['progress']['report']
        assert next(v for v in resumed['invoices'].values() if v['case_id']==accepted['case_id'])['before']==baseline
        assert sum(len(x['initial_mail_ids']) for x in results(resumed))==3
        assert len(provider.sent)==3
        assert len(results(resumed))==6


def test_invoice_error_does_not_abandon_portfolio_and_diagnostics_are_safe(store_factory,monkeypatch):
    from backend.storage import StorageError
    provider=ResendMock()
    with client(store_factory,provider) as c:
        run,_=finish(c);rid=run['run_id'];agent=c.app.state.agent
        original=agent.invoke;first=[True]
        async def fail_once(*args,**kwargs):
            if first[0]:
                first[0]=False
                exc=StorageError('PRIVATE KEY AND PROVIDER RESPONSE MUST NOT APPEAR',code='schema_missing')
                exc.operation='ca_checkpoint'
                raise exc
            return await original(*args,**kwargs)
        monkeypatch.setattr(agent,'invoke',fail_once)
        saved=job(c,rid)
        assert saved['status']=='completed'
        assert saved['progress']['processed']==5 and saved['progress']['failed']==1
        assert saved['progress']['attempted']==saved['progress']['total']==6
        errors=[v['error'] for v in saved['progress']['report']['invoices'].values() if v.get('error')]
        assert errors[0]['code']=='schema_missing' and errors[0]['operation']=='ca_checkpoint'
        assert 'PRIVATE' not in str(saved)
        monkeypatch.setattr(agent,'invoke',original)
        recovered=job(c,rid)
        assert recovered['progress']['processed']==6 and recovered['progress']['failed']==0
        assert not any(v.get('error') for v in recovered['progress']['report']['invoices'].values())
        assert not provider.sent


def test_system_failure_retains_partial_report_and_safe_operation(store_factory,monkeypatch):
    from backend.storage import StorageError
    with client(store_factory) as c:
        run,_=finish(c);rid=run['run_id'];store=c.app.state.agent.store
        original=store.rpc;writes=[0]
        async def fail_save(name,body=None):
            if name=='ca_agent_job' and body.get('p_action')=='update':
                writes[0]+=1
                if writes[0]==3:
                    exc=StorageError('PRIVATE DATABASE BODY',code='network_unavailable');exc.operation=name;raise exc
            return await original(name,body)
        monkeypatch.setattr(store,'rpc',fail_save)
        assert c.post(f'/api/runs/{rid}/agent',json={'mode':'limited'}).status_code==200
        import time
        for _ in range(1500):
            saved=c.get(f'/api/runs/{rid}/agent').json()
            if saved['status']!='running':break
            time.sleep(.005)
        assert saved['status']=='interrupted'
        assert saved['progress']['processed']==1
        assert saved['progress']['failure']['code']=='network_unavailable'
        assert len([v for v in saved['progress']['report']['invoices'].values() if v['completed']])==1
        assert 'PRIVATE' not in str(saved)
        monkeypatch.setattr(store,'rpc',original)
        recovered=job(c,rid)
        assert recovered['progress']['processed']==6 and 'failure' not in recovered['progress']
