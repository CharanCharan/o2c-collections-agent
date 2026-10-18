"""Manual editing and real revision contracts; mock providers, actual local SQL."""
import json
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

from backend.language import LanguageService
from backend.llm.config import LLMConfig
from backend.public_demo import COOKIE
from tests.test_case_agent import client,job
from tests.test_milestone_2 import finish
from tests.test_milestone_4 import draft_value
from tests.test_milestone_5 import ResendMock
from tests.test_visitor_cases import open_case,reply
from tests.test_ai_draft import generate,actor

ROOT=Path(__file__).resolve().parents[1]
CONTEXT='We spoke with Priya. Mention purchase-order reference PO-7781 and ask for confirmation.'


def revision_language(mode='context'):
    calls=[]
    def handler(request):
        payload=json.loads(request.content);calls.append(payload)
        data=json.loads(payload['messages'][1]['content'])
        assert payload['response_format']['json_schema']['name']=='revise_reminder'
        assert data['existing_draft']['body'] and data['existing_draft']['subject']
        value=draft_value(data['facts'])
        value.update(additional_context='Following our conversation with Priya, please confirm purchase-order reference PO-7781.',
                     context_quotes=[CONTEXT],change_summary='Added the prior conversation and purchase-order reference.')
        prior='Please contact our AR team for document copies.'
        if prior in data['existing_draft']['body']:
            value['additional_context'] += ' ' + prior
            value['context_quotes'].append(prior)
        if mode=='invented':value['additional_context']='Please confirm purchase-order reference PO-9999.'
        if mode=='unsupported_quote':value['context_quotes']=['Invented source quote.']
        if mode=='policy':value['additional_context']='The invoice is paid.'
        return httpx.Response(200,json={'id':'mock-revision','model':payload['model'],
            'choices':[{'finish_reason':'stop','message':{'content':json.dumps(value)}}]})
    return LanguageService(config=replace(LLMConfig(enabled=True,key='mock-revision-only'),max_run=0),transport=httpx.MockTransport(handler)),calls


def edit(c,case,subject=None,body=None,expected=None,ident=None,**extra):
    draft=case['snapshot']['invoice']['draft']
    return c.post(f"/api/cases/{case['id']}/draft/edit",json={
        'request_id':ident or str(uuid4()),'expected_draft':expected or draft,
        'subject':subject or draft['subject'],'body':body or draft['body']+'\n\nPlease contact our AR team for document copies.',**extra})


def test_revision_sends_current_draft_and_incorporates_user_context_then_detects_no_change(store_factory):
    llm,calls=revision_language()
    with client(store_factory,language=llm) as c:
        run,_=finish(c);case=open_case(c,run['run_id']);old=case['snapshot']['invoice']['draft']
        response=generate(c,case,CONTEXT);assert response.status_code==200,response.text
        result=response.json();assert result['generated']
        updated=result['case'];draft=updated['snapshot']['invoice']['draft']
        assert 'Priya' in draft['body'] and 'PO-7781' in draft['body'] and draft['body']!=old['body']
        assert draft['context_review_required'] is True and 'prior conversation' in draft['change_summary']
        data=json.loads(calls[0]['messages'][1]['content'])
        assert data['existing_draft']=={'subject':old['subject'],'body':old['body']}
        assert data['revision_request']==CONTEXT and CONTEXT not in calls[0]['messages'][0]['content']
        again=generate(c,updated,CONTEXT).json()
        assert not again['generated'] and 'same draft' in again['reason']
        assert again['case']['snapshot']['invoice']['draft']==draft and len(calls)==2


@pytest.mark.parametrize('mode',['invented','unsupported_quote','policy'])
def test_unsupported_revision_context_keeps_original(store_factory,mode):
    llm,calls=revision_language(mode)
    with client(store_factory,language=llm) as c:
        run,_=finish(c);case=open_case(c,run['run_id']);old=case['snapshot']['invoice']['draft']
        result=generate(c,case,CONTEXT).json()
        assert not result['generated'] and result['reason']
        assert result['case']['snapshot']['invoice']['draft']==old and len(calls)==1


def test_manual_save_without_llm_preserves_authority_then_sends_edited_body_and_replays(store_factory,database):
    mail=ResendMock();ident=str(uuid4())
    with client(store_factory,mail) as c:
        run,_=finish(c);job(c,run['run_id']);case=open_case(c,run['run_id'])
        old=case['snapshot']['invoice']['draft'];body=old['body']+'\n\nPriya requested purchase-order reference PO-7781.'
        subject=old['subject']+' — Follow-up'
        response=edit(c,case,subject,body,ident=ident);assert response.status_code==200,response.text
        updated=response.json()['case'];draft=updated['snapshot']['invoice']['draft']
        assert draft['body']==body and draft['subject']==subject and draft['generation_mode']=='human_edited'
        assert updated['snapshot']['invoice']['draft_audit']['api_attempted'] is False
        assert updated['workflow']['pending']==case['workflow']['pending']
        assert updated['messages'][0]['text']==body
        assert c.get(f"/api/runs/{run['run_id']}").json()['result']==run['result']
        assert not mail.sent
        cookie=c.cookies.get(COOKIE)
    with client(store_factory,mail) as fresh:
        fresh.cookies.set(COOKIE,cookie)
        assert not edit(fresh,case,subject,body,ident=ident).json()['recorded']
        sent=fresh.post(f"/api/cases/{case['id']}/send-email")
        assert sent.status_code==200,sent.text
        assert mail.sent[0]['body']['text'].endswith(body)
        assert mail.sent[0]['body']['subject']=='[O2C DEMO] '+subject
        assert edit(fresh,updated).status_code==409


def test_manual_edit_conflicts_fact_changes_and_foreign_cases_rejected(store_factory):
    with client(store_factory) as c:
        run,_=finish(c);case=open_case(c,run['run_id']);old=case['snapshot']['invoice']['draft']
        with client(store_factory) as stranger:assert edit(stranger,case).status_code==404
        assert edit(c,case,body=old['body'].replace('115,200.00','1.00')).status_code==422
        assert edit(c,case,subject='Different invoice').status_code==422
        assert edit(c,case,subject=old['subject']+'\r\nInjected header').status_code==422
        assert edit(c,case,recipient='other@example.com').status_code==422
        first=edit(c,case).json()['case']
        assert edit(c,case,body=old['body']+'\nStale edit.').status_code==409
        assert c.get('/api/cases').json()['cases'][0]['snapshot']==first['snapshot']


def test_manual_edit_blocks_active_generation_and_retires_stale_result(store_factory,database):
    with client(store_factory) as c:
        run,_=finish(c);case=open_case(c,run['run_id']);key=actor(database,case);ident=str(uuid4())
        params={'p_action':'claim','p_session_key':key,'p_case_id':case['id'],'p_request_id':ident,'p_instructions_hash':'f'*64}
        assert database.call(command='rpc',name='ca_ai_draft',params=params)['data']['recorded']
        assert edit(c,case).status_code==409
        database.sql("update ca_draft_attempts set created_at=created_at-interval '6 minutes' where id=$1",[ident])
        updated=edit(c,case).json()['case']
        params.update(p_action='complete',p_draft=case['snapshot']['invoice']['draft'])
        late=database.call(command='rpc',name='ca_ai_draft',params=params)['data']
        assert late['status']=='superseded' and late['case']['snapshot']==updated['snapshot']


def test_ai_revision_uses_manually_edited_draft_as_its_starting_point(store_factory):
    llm,calls=revision_language()
    with client(store_factory,language=llm) as c:
        run,_=finish(c);case=open_case(c,run['run_id'])
        updated=edit(c,case).json()['case'];draft=updated['snapshot']['invoice']['draft']
        result=generate(c,updated,CONTEXT).json();assert result['generated']
        assert 'Please contact our AR team for document copies.' in result['case']['snapshot']['invoice']['draft']['body']
        assert json.loads(calls[0]['messages'][1]['content'])['existing_draft']=={'subject':draft['subject'],'body':draft['body']}


def test_manual_migration_repeatable_private_and_missing_health_does_not_call_llm(store_factory,database):
    sql=(ROOT/'sql/017_manual_draft.sql').read_text()
    for _ in range(2):assert database.call(command='exec',sql=sql).get('data') is True
    with client(store_factory) as c:
        run,_=finish(c);case=open_case(c,run['run_id'])
        assert c.get('/api/health').json()['draft_edit']['ready']
        database.sql('drop function ca_draft_edit_health()')
        try:
            assert c.get('/api/health').json()['draft_edit']['ready'] is False
            assert edit(c,case).status_code==503
        finally:assert database.call(command='exec',sql=sql).get('data') is True
    database.sql('set role anon')
    try:assert 'error' in database.call(command='sql',sql='select ca_draft_edit_health()')
    finally:database.sql('reset role')
