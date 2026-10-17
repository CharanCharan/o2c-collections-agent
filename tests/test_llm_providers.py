"""Provider contracts use only mock transports, never real credentials/network."""
import asyncio
import json
from dataclasses import replace

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.language import LanguageError, LanguageService
from backend.llm.config import LLMConfig
from backend.main import create_app
from tests.test_milestone_2 import finish
from tests.test_milestone_4 import FACTS, draft_value


def mock_groq(mode='valid', config=None):
    requests = []
    def handler(request):
        payload = json.loads(request.content)
        requests.append(payload)
        assert str(request.url) == 'https://api.groq.com/openai/v1/chat/completions'
        assert request.headers['authorization'] == 'Bearer groq-test-only'
        assert payload['response_format']['json_schema']['strict'] is True
        assert payload['stream'] is False and payload['max_completion_tokens'] == 2048
        assert payload['include_reasoning'] is False
        assert payload['reasoning_effort'] == ('none' if payload['model'].startswith('qwen/') else 'low')
        assert 'groq-test-only' not in str(payload)
        assert 'maxLength' not in json.dumps(payload['response_format'])
        if mode == 'quota':
            return httpx.Response(429, json={'error':'private provider details groq-test-only'})
        if mode == 'timeout':
            raise httpx.ReadTimeout('private provider details', request=request)
        data = json.loads(payload['messages'][1]['content'])
        facts = data['facts']
        if payload['response_format']['json_schema']['name'] == 'draft_reminder':
            value = draft_value(facts)
            if mode == 'bad_facts': value['facts'] = {**facts, 'amount':'1.00'}
            if mode == 'length': value['closing'] = 'x' * 101
        else:
            text = data['reply_text']
            value = {'invoice_id':facts['invoice_id'],'intent':'payment_claim',
                     'promise_date':None,'promise_amount':None,'evidence_quote':text}
        message = {'content':json.dumps(value), 'reasoning':'private-reasoning-must-not-appear'}
        if mode == 'refusal': message['refusal'] = 'refused'
        if mode == 'bad_json': message['content'] = '{'
        if mode == 'array': message['content'] = '[]'
        if mode == 'tool': message['tool_calls'] = [{'name':'unexpected'}]
        return httpx.Response(200, json={'id':'chatcmpl_test','model':payload['model'],
            'choices':[{'finish_reason':'length' if mode=='incomplete' else 'stop','message':message}],
            'usage':{'prompt_tokens':300,'completion_tokens':100,'total_tokens':400}})
    config = config or LLMConfig(enabled=True,key='groq-test-only')
    return LanguageService(config=config,transport=httpx.MockTransport(handler)), requests


def test_env_defaults_keys_and_model_are_independent():
    default = LLMConfig.from_env({})
    assert default.provider=='groq' and default.model=='openai/gpt-oss-20b'
    assert default.free_only and not default.enabled and not default.key
    groq = LLMConfig.from_env({'GROQ_API_KEY':'groq-private', 'OPENAI_API_KEY':'openai-private'})
    assert groq.key == 'groq-private' and groq.key_variable == 'GROQ_API_KEY'
    assert 'groq-private' not in repr(groq)
    assert not LLMConfig.from_env({'OPENAI_API_KEY':'old-paid-key'}).key
    openai = LLMConfig.from_env({'LLM_PROVIDER':'openai','LLM_FREE_ONLY':'false','OPENAI_API_KEY':'openai-private'})
    assert openai.model=='gpt-5.6-luna' and openai.key=='openai-private' and not openai.error()
    assert LLMConfig.from_env({'LLM_MODEL':'openai/gpt-oss-120b'}).model=='openai/gpt-oss-120b'


@pytest.mark.parametrize('settings', [
    {'LLM_PROVIDER':'openai'}, {'LLM_PROVIDER':'unknown'}, {'LLM_MODEL':'unreviewed-model'},
    {'LLM_MAX_CALLS_PER_PROCESS':'101'}, {'LLM_MAX_CALLS_PER_RUN':'-1'},
    {'LLM_MAX_OUTPUT_TOKENS':'99999'}, {'LLM_TIMEOUT_SECONDS':'0'},
    {'LLM_FREE_ONLY':'typo'}, {'LLM_MAX_CALLS_PER_RUN':'not-an-int'},
])
def test_invalid_or_paid_configuration_never_calls_a_provider(settings):
    async def check():
        calls = []
        config = LLMConfig.from_env({'COLLECTIONS_LLM_ENABLED':'true','GROQ_API_KEY':'test',
            'OPENAI_API_KEY':'old-paid-key', **settings})
        service = LanguageService(config=config,transport=httpx.MockTransport(lambda req: calls.append(req)))
        with pytest.raises(LanguageError):
            await service.call('draft_reminder',FACTS)
        assert not calls and service.calls==0
        assert service.status()['configuration_error']
        assert 'old-paid-key' not in json.dumps(service.status())
        await service.close()
    asyncio.run(check())


def test_groq_run_and_reply_persist_normalized_evidence(store_factory):
    service, requests = mock_groq()
    with TestClient(create_app(store_factory(),language=service)) as c:
        run, events = finish(c)
        assert len(requests)==4 and len(events)==21
        for row in run['result']['invoices']:
            if row['draft']:
                assert row['draft']['provider']=='groq'
                assert row['draft']['generation_mode']=='llm_assisted_validated_facts'
                assert row['draft_audit']['usage']=={'input_tokens':300,'output_tokens':100,'total_tokens':400}
                assert row['draft_audit']['adapter_version']=='groq-chat-json-v1'
        route=f"/api/runs/{run['run_id']}/invoices/INV-10287/classify-example"
        review=c.post(route,json={'example_id':'paid'}).json()
        assert review['recorded'] and len(requests)==5
        assert review['run']['result']['summary']==run['result']['summary']
        assert not c.post(route,json={'example_id':'paid'}).json()['recorded']
        assert len(requests)==5
        text=json.dumps(review)
        assert 'private-reasoning' not in text and 'groq-test-only' not in text
        status=c.get('/api/health').json()['language']
        assert status['provider']=='groq' and status['free_only']
        assert status['account_billing_tier_verified'] is False


@pytest.mark.parametrize('mode',['quota','timeout','bad_facts','length','refusal','bad_json','array','tool','incomplete'])
def test_groq_failures_have_no_retry_or_provider_switch(mode):
    async def check():
        service, requests=mock_groq(mode)
        try:
            # Classification must fail closed for transport/envelope errors.
            if mode not in {'bad_facts','length'}:
                result=await service.classify(FACTS,'We paid this invoice yesterday.')
                assert result['status']=='manual_review'
                assert result['audit']['api_attempted']
                assert len(requests)==1 and service.calls==1
                assert 'private' not in json.dumps(result)
            else:
                from backend.language import validate_draft
                value,_=await service.call('draft_reminder',FACTS)
                with pytest.raises(ValueError): validate_draft(value,FACTS)
                assert len(requests)==1
        finally:
            await service.close()
    asyncio.run(check())


def test_quota_run_is_truthful_template_fallback(store_factory):
    service, requests=mock_groq('quota')
    with TestClient(create_app(store_factory(),language=service)) as c:
        run, events=finish(c)
        assert run['result']['drafting']['counts']['fallback']==4
        assert len(requests)==4 and any(e['status']=='warning' for e in events)
        assert 'HTTP 429' in json.dumps(run)
        assert 'groq-test-only' not in json.dumps(run)


def test_model_change_uses_same_adapter():
    async def check():
        for model in ['openai/gpt-oss-120b','qwen/qwen3.8-27b']:
            service, requests=mock_groq(config=replace(LLMConfig(enabled=True,key='groq-test-only'),model=model))
            try:
                _,audit=await service.call('draft_reminder',FACTS)
                assert requests[0]['model']==model and audit['requested_model']==model
            finally:
                await service.close()
    asyncio.run(check())
