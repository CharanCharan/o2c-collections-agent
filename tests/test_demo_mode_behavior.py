"""Verify real saved-case/mode behavior; model and mail providers are mocked."""
import pytest
from backend.public_demo import COOKIE
from tests.test_case_agent import client,job,mock_language
from tests.test_milestone_2 import finish
from tests.test_milestone_5 import ResendMock


@pytest.mark.parametrize('mode,expected_sends',[('limited',0),('autopilot',3)])
def test_fresh_llm_run_sends_only_under_saved_automatic_authority(store_factory,mode,expected_sends):
    provider=ResendMock();language,calls=mock_language()
    with client(store_factory,provider,language) as c:
        run,_=finish(c)
        drafted=[row for row in run['result']['invoices'] if row.get('draft')]
        assert len(drafted)==4 and len(calls)==4
        assert all(row['draft']['generation_mode']=='llm_assisted_validated_facts' for row in drafted)
        job(c,run['run_id'],mode)
        cases=c.get('/api/cases').json()['cases']
        assert all(case['workflow']['mode']==mode for case in cases)
        assert len(provider.sent)==expected_sends
        assert sum(bool(case.get('outbound') and case['outbound']['state']=='accepted') for case in cases)==expected_sends
        # Reading/repeating the same job never repeats mail.
        job(c,run['run_id'],mode)
        assert len(provider.sent)==expected_sends


def test_enabling_llm_does_not_rewrite_saved_case_or_change_saved_approval_mode(store_factory):
    provider=ResendMock()
    with client(store_factory,provider) as c:
        run,_=finish(c);job(c,run['run_id'],'limited')
        before={case['invoice_id']:case for case in c.get('/api/cases').json()['cases']}
        cookie=c.cookies.get(COOKIE)
    language,calls=mock_language()
    with client(store_factory,provider,language) as c:
        c.cookies.set(COOKIE,cookie)
        run,_=finish(c);result=job(c,run['run_id'],'autopilot')
        assert len(calls)==4 and not provider.sent
        assert result['progress']['retained']==len(before)
        for case in c.get('/api/cases').json()['cases']:
            old=before[case['invoice_id']]
            assert case['id']==old['id'] and case['snapshot']==old['snapshot']
            assert case['workflow']['mode']=='limited'
