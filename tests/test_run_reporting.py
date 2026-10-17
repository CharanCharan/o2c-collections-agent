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
