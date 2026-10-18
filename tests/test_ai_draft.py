"""Explicit AI drafts: actual SQL, mock LLM/mail, saved authority and concurrency."""
import asyncio
import hashlib
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

from backend.language import LanguageService
from backend.llm.config import LLMConfig
from backend.public_demo import COOKIE
from tests.test_case_agent import client, job
from tests.test_llm_providers import mock_groq
from tests.test_milestone_2 import finish
from tests.test_milestone_5 import ResendMock
from tests.test_visitor_cases import open_case, reply


def language(mode='valid'):
    # Prepare initial templates without spending model quota; explicit drafts still call.
    return mock_groq(mode, replace(LLMConfig(enabled=True,key='groq-test-only'),max_run=0))


def generate(c, case, instructions='Make it warmer and shorter.', ident=None, **extra):
    return c.post(f"/api/cases/{case['id']}/draft",json={
        'request_id':ident or str(uuid4()),'instructions':instructions,**extra})


def actor(database, case):
    return database.sql('select session_key from ca_collection_cases where id=$1',[case['id']])[0]['session_key']


def test_generate_save_restart_replay_and_send_exact_reviewed_draft(store_factory,database):
    llm, calls = language(); mail = ResendMock(); ident = str(uuid4())
    with client(store_factory,mail,llm) as c:
        run,_=finish(c); job(c,run['run_id']); case=open_case(c,run['run_id'])
        assert case['workflow']['pending']['tool']=='send_email'
        original=case['snapshot']['invoice']['draft']; assert not calls
        response=generate(c,case,ident=ident); assert response.status_code==200,response.text
        result=response.json(); updated=result['case']; draft=updated['snapshot']['invoice']['draft']
        assert result['generated'] and draft!=original and len(calls)==1
        assert updated['workflow']['pending']==case['workflow']['pending']
        assert draft['generation_mode']=='llm_assisted_validated_facts'
        assert updated['snapshot']['invoice']['draft_audit']['generation_trigger']=='visitor_requested'
        assert updated['messages'][0]['text']==draft['body']
        assert updated['workflow']['activity'][-1]['node']=='redraft'
        assert 'timestamp' in updated['workflow']['activity'][-1]
        payload=calls[0]; data=json.loads(payload['messages'][1]['content'])
        assert data['draft_preferences']=='Make it warmer and shorter.'
        assert 'Make it warmer and shorter.' not in payload['messages'][0]['content']
        assert c.get(f"/api/runs/{run['run_id']}").json()['result']==run['result']
        assert not mail.sent
        stale_payload={'subject':'[O2C DEMO] '+original['subject'],
                       'text':'SYNTHETIC COLLECTIONS DEMO — no real debt or payment request.\n\n'+original['body']}
        stale=database.call(command='rpc',name='ca_case_mail_prepare',params={
            'p_session_key':actor(database,case),'p_case_id':case['id'],'p_id':str(uuid4()),
            'p_payload':stale_payload,'p_reply_to':'test@demo.resend.app'})
        assert stale['error']['code']=='PT409'
        assert database.sql('select count(*) as n from ca_mail_messages')[0]['n']==0
        cookie=c.cookies.get(COOKIE)
    llm2,calls2=language()
    with client(store_factory,mail,llm2) as fresh:
        fresh.cookies.set(COOKIE,cookie)
        replay=generate(fresh,case,ident=ident).json()
        assert not replay['recorded'] and replay['generated'] and not calls2
        assert replay['case']['snapshot']['invoice']['draft']==draft
        sent=fresh.post(f"/api/cases/{case['id']}/send-email")
        assert sent.status_code==200,sent.text
        assert mail.sent[0]['body']['text'].endswith(draft['body'])
        assert len(mail.sent)==1 and sent.json()['case']['workflow']['pending'] is None
        assert generate(fresh,case).status_code==409 and not calls2


@pytest.mark.parametrize('mode',['length','bad_facts','quota','timeout','bad_json'])
def test_failure_keeps_existing_draft_and_audit_with_no_retry(store_factory,mode):
    llm,calls=language(mode)
    with client(store_factory,language=llm) as c:
        run,_=finish(c);case=open_case(c,run['run_id']);ident=str(uuid4())
        original=case['snapshot']['invoice'];response=generate(c,case,ident=ident)
        assert response.status_code==200,response.text
        result=response.json();assert not result['generated']
        assert result['case']['snapshot']['invoice']==original
        assert result['reason'] and result['audit']['api_attempted'] is True
        assert len(calls)==1
        assert not generate(c,case,ident=ident).json()['recorded'] and len(calls)==1
        assert 'groq-test-only' not in response.text and 'private-reasoning' not in response.text


def test_foreign_case_overrides_input_limits_and_reply_holds_never_call_model(store_factory):
    llm,calls=language()
    with client(store_factory,language=llm) as c:
        run,_=finish(c);case=open_case(c,run['run_id'])
        with client(store_factory) as stranger:
            assert generate(stranger,case).status_code==404
        for extra in [{'recipient':'other@example.com'},{'draft':{'body':'override'}},{'mode':'autopilot'}]:
            assert generate(c,case,**extra).status_code==422
        for text in ['x'*601, 'plain\x00text']:
            assert generate(c,case,text).status_code==422
        disputed=next(x['id'] for x in run['result']['invoices'] if x['dispute'])
        assert generate(c,open_case(c,run['run_id'],disputed)).status_code==409
        llm.enabled=False
        assert reply(c,case).status_code==200
        assert generate(c,case).status_code==409 and not calls


def test_missing_migration_disables_only_feature_without_model_call(store_factory,database):
    llm,calls=language()
    with client(store_factory,language=llm) as c:
        run,_=finish(c);case=open_case(c,run['run_id'])
        database.sql('drop function ca_ai_draft_health()')
        try:
            health=c.get('/api/health');assert health.status_code==200
            assert not health.json()['ai_draft']['ready']
            response=generate(c,case)
            assert response.status_code==503 and '015_ai_draft.sql' in response.text and not calls
            assert c.get('/api/portfolio').status_code==200
        finally:
            sql=(Path(__file__).resolve().parents[1]/'sql/015_ai_draft.sql').read_text()
            assert database.call(command='exec',sql=sql).get('data') is True


def test_explicit_generation_obeys_durable_browser_llm_budget(store_factory):
    llm,calls=language()
    with client(store_factory,language=llm) as c:
        run,_=finish(c);case=open_case(c,run['run_id'])
        for _ in range(8):
            result=generate(c,case).json();assert result['generated'],result
        old=result['case']['snapshot']['invoice']['draft']
        result=generate(c,case).json()
        assert not result['generated'] and 'quota' in result['reason'].lower()
        assert result['case']['snapshot']['invoice']['draft']==old and len(calls)==8


def test_reserved_request_survives_restart_without_repeat_call_and_stale_can_be_superseded(store_factory,database):
    llm,calls=language(); ident=str(uuid4());instructions='Keep it concise.'
    with client(store_factory,language=llm) as c:
        run,_=finish(c);case=open_case(c,run['run_id']);key=actor(database,case)
        args={'p_action':'claim','p_session_key':key,'p_case_id':case['id'],'p_request_id':ident,
              'p_instructions_hash':hashlib.sha256(instructions.encode()).hexdigest()}
        assert database.call(command='rpc',name='ca_ai_draft',params=args)['data']['recorded']
        assert not generate(c,case,instructions,ident).json()['recorded'] and not calls
        assert generate(c,case).status_code==409 and not calls
        database.sql("update ca_draft_attempts set created_at=created_at-interval '6 minutes' where id=$1",[ident])
        assert generate(c,case).json()['generated'] and len(calls)==1
        # A late completion for the superseded reservation cannot overwrite the new draft.
        args.update(p_action='complete',p_draft={'body':'stale model result'},p_audit={})
        late=database.call(command='rpc',name='ca_ai_draft',params=args)['data']
        assert late['status']=='superseded' and not late['recorded']
        assert late['case']['snapshot']['invoice']['draft']['body']!='stale model result'


def test_generation_blocks_send_and_discards_result_if_case_changes(store_factory,database):
    llm,calls=language(); started=threading.Event(); release=threading.Event()
    original=llm.transport.handler
    async def delayed(req):
        started.set()
        await asyncio.to_thread(release.wait,5)
        return original(req)
    llm.transport=httpx.MockTransport(delayed);mail=ResendMock()
    with client(store_factory,mail,llm) as c:
        run,_=finish(c);job(c,run['run_id']);case=open_case(c,run['run_id']);old=case['snapshot']['invoice']['draft']
        with ThreadPoolExecutor() as pool:
            future=pool.submit(generate,c,case)
            try:
                assert started.wait(5)
                assert c.post(f"/api/cases/{case['id']}/send-email").status_code==409
                database.sql("update ca_collection_cases set collection_status='dispute_hold_review_required' where id=$1",[case['id']])
            finally:release.set()
            result=future.result(timeout=10).json()
        assert not result['generated'] and 'case changed' in result['reason'].lower()
        assert result['case']['snapshot']['invoice']['draft']==old and not mail.sent and len(calls)==1


def test_migration_is_repeatable_and_attempts_private(store_factory,database):
    sql=(Path(__file__).resolve().parents[1]/'sql/015_ai_draft.sql').read_text()
    assert database.call(command='exec',sql=sql).get('data') is True
    assert database.call(command='exec',sql=sql).get('data') is True
    database.sql('set role anon')
    try:
        assert 'error' in database.call(command='sql',sql='select * from ca_draft_attempts')
        assert 'error' in database.call(command='sql',sql='select ca_ai_draft_health()')
    finally:database.sql('reset role')
