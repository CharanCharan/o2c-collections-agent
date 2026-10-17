from fastapi.testclient import TestClient
from backend.main import create_app
from tests.test_llm_providers import mock_groq
from tests.test_milestone_6 import PUBLIC


def test_preview_loads_source_without_run_quota_llm_or_email_side_effects(store_factory,database):
    language,requests=mock_groq()
    with TestClient(create_app(store_factory(),language=language,public_config=PUBLIC),base_url='https://demo.test') as c:
        before=c.get('/api/runs').json()
        preview=c.get('/api/portfolio')
        assert preview.status_code==200,preview.text
        data=preview.json()
        assert data['mode']=='read_only_preview' and not data['agent_started']
        assert len(data['portfolio']['invoices'])==6
        assert data['portfolio']['summary']['open_balance']=='372200.00'
        assert data['portfolio']['summary']['draft_count']==0
        assert not requests and c.get('/api/runs').json()==before
        assert database.sql('select count(*) as n from ca_demo_usage')[0]['n']==0
        assert database.sql('select count(*) as n from ca_mail_messages')[0]['n']==0
