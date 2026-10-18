"""Draft format reliability and safe diagnostics; no live provider calls."""
import asyncio
import copy
import json

import pytest
from fastapi.testclient import TestClient

from backend.language import DRAFT_TEXT_LIMITS, LanguageError, validate_draft
from backend.main import create_app
from tests.test_llm_providers import mock_groq
from tests.test_milestone_2 import finish
from tests.test_milestone_4 import FACTS, draft_value


def test_portable_provider_schema_and_prompt_keep_character_constraints():
    async def check():
        service, requests = mock_groq()
        try:
            value, audit = await service.call('draft_reminder', FACTS)
            assert validate_draft(value, FACTS)
            payload = requests[0]
            prompt = payload['messages'][0]['content']
            properties = payload['response_format']['json_schema']['schema']['properties']
            for name, (low, high) in DRAFT_TEXT_LIMITS.items():
                assert f'{name}: {low}–{high} characters' in prompt
                assert f'{low}–{high} characters' in properties[name]['description']
            assert 'preserving every value as a JSON string' in prompt
            assert 'exactly these keys: facts, opening, request, closing' in prompt
            assert 'Thank you for your assistance.' in prompt
            assert audit['prompt_version'] == 'collections-language-v3'
            assert len(requests) == 1
        finally:
            await service.close()
    asyncio.run(check())


@pytest.mark.parametrize('field', ['opening', 'request', 'closing'])
@pytest.mark.parametrize('boundary', ['below', 'above', 'wrong_type'])
def test_draft_rejects_invalid_field_with_safe_specific_reason(field, boundary):
    value = copy.deepcopy(draft_value(FACTS))
    low, high = DRAFT_TEXT_LIMITS[field]
    value[field] = {'private-generated-output': 'private-value'} if boundary == 'wrong_type' else 'x' * (low - 1 if boundary == 'below' else high + 1)
    with pytest.raises(LanguageError) as caught:
        validate_draft(value, FACTS)
    reason = str(caught.value)
    assert field in reason
    assert ('must be a string' if boundary == 'wrong_type' else f'{low}–{high} characters') in reason
    assert 'private-generated-output' not in reason and 'private-value' not in reason
    assert 'input_value' not in reason


def test_schema_diagnostics_do_not_echo_untrusted_keys_or_fact_values():
    for change, reason in [
        ({'private-model-field': 'private-value'}, 'unexpected field'),
        ({'facts': {**FACTS, 'amount': 123}}, 'facts.amount must be a string'),
        ({'closing': None}, 'closing must be a string'),
    ]:
        with pytest.raises(LanguageError) as caught:
            validate_draft({**draft_value(FACTS), **change}, FACTS)
        assert reason in str(caught.value)
        assert 'private-model-field' not in str(caught.value)
        assert 'private-value' not in str(caught.value)
    value = draft_value(FACTS)
    del value['request']
    with pytest.raises(LanguageError, match='request is missing a required field'):
        validate_draft(value, FACTS)


def test_overlength_provider_response_persists_specific_fallback_without_retry(store_factory):
    service, requests = mock_groq('length')
    with TestClient(create_app(store_factory(), language=service)) as client:
        run, events = finish(client)
        assert run['result']['drafting']['counts']['fallback'] == 4
        assert len(requests) == 4  # One request per draft, no retries or extra quota use.
        for row in run['result']['invoices']:
            if not row['draft']:
                continue
            audit = row['draft_audit']
            assert 'closing must contain 5–100 characters' in audit['reason']
            assert audit['api_attempted'] is True and audit['http_status'] == 200
            assert audit['usage']['total_tokens'] == 400
            assert row['draft']['generation_mode'] == 'template_fallback_no_llm_approval'
            assert row['draft']['review_required'] is True
        saved = json.dumps(run)
        assert 'x' * 101 not in saved and 'private-reasoning' not in saved
        assert 'groq-test-only' not in saved
        assert any('closing must contain' in json.dumps(e) for e in events)
