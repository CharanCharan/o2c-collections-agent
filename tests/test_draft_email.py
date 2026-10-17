"""Draft button send tool, no owner token; fixed recipient and case isolation."""
from dataclasses import replace
from uuid import uuid4

import httpx
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.public_demo import COOKIE
from tests.test_milestone_2 import finish
from tests.test_milestone_5 import CONFIG,ResendMock,signed,receive
from tests.test_milestone_6 import PUBLIC
from tests.test_visitor_cases import open_case,reply


def client(store_factory,provider,config=None):
    return TestClient(create_app(store_factory(),public_config=replace(PUBLIC,owner_token=''),
        mail_config=config or replace(CONFIG,owner_token=''),mail_transport=httpx.MockTransport(provider.handler)),base_url='https://demo.test')


def send(c,case,**kwargs):
    return c.post(f"/api/cases/{case['id']}/send-email",**kwargs)


def test_send_without_owner_token_real_payload_dedup_delivery_and_restart(store_factory,database):
    provider=ResendMock()
    with client(store_factory,provider) as c:
        assert c.get('/api/health').json()['email']['ready']
        run,_=finish(c);case=open_case(c,run['run_id'])
        response=send(c,case);assert response.status_code==200,response.text
        sent=response.json()['case'];assert sent['collection_status']=='awaiting_response'
        assert sent['outbound']['state']=='accepted' and sent['outbound']['events']==[]
        assert provider.sent[0]['body']['text'].endswith(case['snapshot']['invoice']['draft']['body'])
        assert provider.sent[0]['body']['to']==[CONFIG.recipient]
        assert send(c,case).status_code==200 and len(provider.sent)==1
        raw,headers=signed({'type':'email.delivered','data':{'email_id':sent['outbound']['provider_id']}})
        assert c.post('/api/webhooks/resend',content=raw,headers=headers).status_code==200
        saved=c.get('/api/cases').json()['cases'][0]
        assert saved['outbound']['events'][0]['type']=='email.delivered'
        assert c.get(f"/api/runs/{run['run_id']}").json()['result']==run['result']
        cookie=c.cookies.get(COOKIE)
        # Actual private inbound reply is still not returned in the visitor projection.
        message=database.sql('select * from ca_mail_messages')[0]
        assert receive(c,provider,message,text='Private real inbox response.')[0].status_code==200
        assert 'Private real inbox response' not in c.get('/api/cases').text
    with client(store_factory,provider) as fresh:
        fresh.cookies.set(COOKIE,cookie)
        assert send(fresh,case).status_code==200 and len(provider.sent)==1
        assert fresh.get('/api/cases').json()['cases'][0]['outbound']['events'][0]['type']=='email.delivered'


def test_foreign_session_and_request_overrides_cannot_send(store_factory):
    provider=ResendMock()
    with client(store_factory,provider) as a:
        run,_=finish(a);case=open_case(a,run['run_id'])
        with client(store_factory,provider) as b:
            assert send(b,case).status_code==404
        for override in [{'to':'stranger@example.com'},{'text':'Replaced body'},{'mode':'auto'}]:
            assert send(a,case,json=override).status_code==422
        assert not provider.sent


def test_case_reply_or_dispute_blocks_reminder_before_egress(store_factory):
    provider=ResendMock()
    with client(store_factory,provider) as c:
        run,_=finish(c);case=open_case(c,run['run_id'])
        assert reply(c,case).status_code==200
        assert send(c,case).status_code==409
        disputed=next(r['id'] for r in run['result']['invoices'] if r['dispute'])
        assert send(c,open_case(c,run['run_id'],disputed)).status_code==409
        assert not provider.sent


def test_unknown_outcome_retries_same_intent_and_payload(store_factory):
    provider=ResendMock();provider.fail=True
    with client(store_factory,provider) as c:
        run,_=finish(c);case=open_case(c,run['run_id'])
        response=send(c,case).json()['case']
        assert response['outbound']['state']=='uncertain'
        assert len(provider.sent)==1
        provider.fail=False
        response=send(c,case).json()['case']
        assert response['outbound']['state']=='accepted'
        assert provider.sent[0]==provider.sent[1]
        assert send(c,case).status_code==200 and len(provider.sent)==2


def test_daily_mail_cap_still_bounds_cost_for_token_free_button(store_factory,database):
    provider=ResendMock()
    with client(store_factory,provider) as c:
        run,_=finish(c);case=open_case(c,run['run_id'])
        database.sql("insert into ca_mail_messages(id,run_id,invoice_id,payload,reply_to) select gen_random_uuid(),$1,'quota-'||n,'{}'::jsonb,'quota-'||n||'@demo.resend.app' from generate_series(1,10)n",[run['run_id']])
        assert send(c,case).status_code==429 and not provider.sent


def test_email_disabled_and_no_draft_never_calls_provider(store_factory):
    provider=ResendMock()
    with client(store_factory,provider,replace(CONFIG,enabled=False,owner_token='')) as c:
        run,_=finish(c);case=open_case(c,run['run_id'])
        assert send(c,case).status_code==409 and not provider.sent


def test_case_mail_link_is_service_private(database):
    database.sql('set role anon')
    try:
        assert 'error' in database.call(command='sql',sql='select * from ca_case_mail')
        assert 'error' in database.call(command='sql',sql="select ca_case_mail_prepare('x',gen_random_uuid(),gen_random_uuid(),'{}','x')")
    finally:database.sql('reset role')
