import asyncio
import copy
import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.language import LanguageError, LanguageService, validate_draft, validate_reply
from backend.main import create_app
from tests.test_milestone_2 import finish

FACTS = {'invoice_id':'INV-10287','amount':'115200.00','currency':'USD','due_date':'2026-08-22','as_of_date':'2026-10-17'}


def draft_value(facts):
    return {'facts':facts,'opening':'I hope your team is doing well.',
        'request':'Could you share an update on the expected payment timing?', 'closing':'Thank you for your assistance.'}


def mock_service(mode='valid', **kwargs):
    requests = []
    def transport(request):
        payload = json.loads(request.content)
        requests.append(payload)
        assert request.url == 'https://api.openai.com/v1/responses'
        assert payload['store'] is False and payload['text']['format']['strict'] is True
        assert payload['reasoning']['effort'] == 'none' and payload['max_output_tokens'] == 1024
        assert payload['model'] == 'gpt-5.6-luna'
        assert 'secret-test' not in str(payload)
        if mode == 'timeout':
            raise httpx.ConnectError('private provider body secret-test', request=request)
        if mode == 'error':
            return httpx.Response(429, json={'error':'private provider body secret-test'})
        facts = json.loads(payload['input'])['facts']
        task = payload['text']['format']['name']
        if task == 'draft_reminder':
            value = draft_value(facts)
            if mode == 'bad_facts': value['facts'] = {**facts,'amount':'1.00'}
            if mode == 'bad_prose': value['request'] = 'Please transfer USD 9999 to a new bank account.'
        else:
            text = json.loads(payload['input'])['reply_text']
            intent = 'promise_to_pay' if '2026-10-30' in text else 'payment_claim' if text.startswith('We paid') else 'dispute' if text.startswith('We dispute') else 'request_info' if text.startswith('Please send') else 'other'
            value = {'invoice_id':facts['invoice_id'],'intent':intent,
                'promise_date':'2026-10-30' if intent=='promise_to_pay' else None,
                'promise_amount':'1000.00' if intent=='promise_to_pay' else None,'evidence_quote':text}
        if mode == 'bad_reply' and task == 'classify_reply': value['promise_date']='2030-01-01'
        content = [{'type':'output_text','text':json.dumps(value)}]
        if mode == 'refusal': content=[{'type':'refusal','refusal':'Cannot comply.'}]
        return httpx.Response(200,json={'id':'resp_test','model':'gpt-5.6-luna','status':'completed',
            'output':[{'type':'message','content':content}], 'usage':{'input_tokens':300,'output_tokens':100,'total_tokens':400}})
    return LanguageService(enabled=True,key='secret-test',provider='openai',free_only=False,transport=httpx.MockTransport(transport),**kwargs), requests


def test_strict_fact_echo_and_prose_guards():
    assert validate_draft(draft_value(FACTS), FACTS)
    wrong = draft_value({**FACTS,'due_date':'2026-11-01'})
    with pytest.raises(LanguageError): validate_draft(wrong, FACTS)
    wrong = draft_value(FACTS); wrong['request']='A penalty of USD 500 is due tomorrow.'
    with pytest.raises(LanguageError): validate_draft(wrong, FACTS)


def test_reply_literal_evidence_and_promise_boundaries():
    text='We will pay 1000.00 on 2026-10-30.'
    value={'invoice_id':FACTS['invoice_id'],'intent':'promise_to_pay','promise_date':'2026-10-30','promise_amount':'1000.00','evidence_quote':text}
    assert validate_reply(value,FACTS,text)
    for change in [{'promise_date':'2027-01-01'}, {'promise_amount':'999999.00'}, {'evidence_quote':'invented'}, {'intent':'payment_claim'}]:
        with pytest.raises((LanguageError, ValueError)):
            validate_reply({**value,**change},FACTS,text)


def test_llm_drafts_persist_exact_facts_policy_and_tool_events(store_factory):
    language, requests = mock_service()
    with TestClient(create_app(store_factory(), language=language)) as c:
        run, events = finish(c)
        assert run['status']=='completed'
        assert len(requests)==4 and len(events)==21
        rows=run['result']['invoices']
        assert run['result']['drafting']['counts']['llm']==4
        for row in rows:
            if row['draft']:
                assert row['draft']['generation_mode']=='llm_assisted_validated_facts'
                assert row['draft_audit']['api_attempted'] is True
                assert row['draft_audit']['usage']['total_tokens']==400
                assert row['id'] in row['draft']['body']
                assert row['amount'] in row['draft_audit']['facts']['amount']
            if row['dispute']: assert row['draft'] is None and row['draft_audit']['status']=='policy_skipped'
        rid=run['run_id']
        assert c.post(f'/api/runs/{rid}/invoices/INV-10287/dry-run').json()['recorded']
        assert c.post(f'/api/runs/{rid}/invoices/INV-10317/dry-run').status_code==409


@pytest.mark.parametrize('mode',['bad_facts','bad_prose','timeout','error','refusal'])
def test_untrusted_or_failed_generation_is_labelled_fallback(store_factory, mode):
    language, requests = mock_service(mode)
    with TestClient(create_app(store_factory(),language=language)) as c:
        run, events=finish(c)
        assert run['status']=='completed' and len(requests)==4
        assert run['result']['drafting']['counts']['fallback']==4
        assert any(e['status']=='warning' for e in events)
        for row in run['result']['invoices']:
            if row['draft']:
                assert row['draft']['generation_mode']=='template_fallback_no_llm_approval'
                assert row['draft_audit']['api_attempted'] is True
        assert 'secret-test' not in json.dumps(run)


def test_disabled_missing_key_and_call_caps_make_no_unexpected_requests(store_factory):
    language, requests=mock_service(max_run=1,max_process=1)
    with TestClient(create_app(store_factory(),language=language)) as c:
        first,_=finish(c)
        second,_=finish(c)
        assert len(requests)==1
        assert first['result']['drafting']['counts']['llm']==1
        assert second['result']['drafting']['counts']['fallback']==4
    language=LanguageService(enabled=True,key='')
    with TestClient(create_app(store_factory(),language=language)) as c:
        run,_=finish(c)
        assert run['result']['drafting']['counts']['fallback']==4
        assert not any(r.get('draft_audit',{}).get('api_attempted') for r in run['result']['invoices'])


def test_reply_examples_classify_deduplicate_and_never_mark_paid(store_factory):
    language, requests=mock_service()
    with TestClient(create_app(store_factory(),language=language)) as c:
        run,_=finish(c)
        rid=run['run_id']; original=copy.deepcopy(run['result']['summary'])
        route=f'/api/runs/{rid}/invoices/INV-10287/classify-example'
        for case in ['promise','paid','dispute','documents','injection']:
            reply=c.post(route,json={'example_id':case})
            assert reply.status_code==200,reply.text
            assert reply.json()['recorded'] is True
            review=next(r for r in reply.json()['run']['result']['invoices'] if r['id']=='INV-10287')['reply_reviews'][case]
            expected=next(e for e in json.loads(Path('fixtures/replies.json').read_text()) if e['id']==case)['expected_intent']
            assert review['classification']['intent']==expected
            assert review['review_required'] and not review['invoice_payment_updated']
            assert reply.json()['run']['result']['summary']==original
        calls=len(requests)
        assert not c.post(route,json={'example_id':'paid'}).json()['recorded']
        assert len(requests)==calls
        assert c.post(route,json={'example_id':'unknown'}).status_code==404
        assert c.post(route,json={'example_id':'paid','text':'not allowed'}).status_code==422
    with TestClient(create_app(store_factory(),language=LanguageService())) as fresh:
        saved=fresh.get(f'/api/runs/{rid}').json()
        row=next(r for r in saved['result']['invoices'] if r['id']=='INV-10287')
        assert len(row['reply_reviews'])==5 and row['draft'] and not row['contacted']


def test_template_only_and_manual_reply_review_are_truthful(store_factory):
    with TestClient(create_app(store_factory(),language=LanguageService())) as c:
        run,events=finish(c)
        assert len(events)==13 and run['result']['drafting']['counts']['template']==4
        response=c.post(f"/api/runs/{run['run_id']}/invoices/INV-10287/classify-example",json={'example_id':'paid'})
        review=response.json()['run']['events'][-1]['result']['review']
        assert review['status']=='manual_review' and review['classification'] is None
        assert review['simulated_input'] and not review['invoice_payment_updated']


def test_reply_rpc_denies_anonymous(database):
    database.sql('set role anon')
    try:
        assert 'error' in database.call(command='sql',sql='select ca_language_health()')
    finally:
        database.sql('reset role')


def test_rejected_reply_keeps_attempt_and_usage_evidence():
    async def run():
        language, requests = mock_service('bad_reply')
        try:
            result = await language.classify(FACTS, 'We will pay 1000.00 on 2026-10-30.')
            assert result['status'] == 'manual_review' and len(requests) == 1
            assert result['audit']['api_attempted'] is True
            assert result['audit']['usage']['total_tokens'] == 400
        finally:
            await language.close()
    asyncio.run(run())
