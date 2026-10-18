"""Reproduce legacy FK failure, then verify non-destructive checkpoint repair."""
import asyncio
import json
from pathlib import Path
import httpx
import pytest
from backend.storage import SupabaseStore,StorageError
from backend.workflow.diagnostics import failure
from tests.test_case_agent import client,job
from tests.test_milestone_2 import finish

ROOT=Path(__file__).resolve().parents[1]


def legacy_function(database):
    database.sql('alter table ca_graph_writes add constraint ca_graph_writes_legacy_checkpoint_fkey foreign key(case_id,namespace,checkpoint_id) references ca_graph_checkpoints on delete cascade')
    sql=(ROOT/'sql/009_case_workflow.sql').read_text()
    start=sql.index('create or replace function public.ca_checkpoint(')
    end=sql.index('create or replace function public.ca_workflow_patch(',start)
    assert database.call(command='exec',sql=sql[start:end]).get('data')


def checkpoint(database,case,action,ident,data=None,namespace=''):
    return database.call(command='rpc',name='ca_checkpoint',params={'p_action':action,'p_case_id':case,'p_namespace':namespace,'p_checkpoint_id':ident,'p_data':data})


def test_legacy_late_write_fk_and_repair_preserves_history(store_factory,database):
    with client(store_factory) as c:
        run,_=finish(c);job(c,run['run_id']);case=c.get('/api/cases').json()['cases'][0]['id']
        legacy_function(database)
        for i in range(10):assert 'error' not in checkpoint(database,case,'put',f'repair-{i:02}',{'marker':i})
        payload=[{'task_id':'delayed','idx':0,'channel':'x','value':['json','e30=']}]
        before=checkpoint(database,case,'writes','repair-00',payload)
        assert before['error']['code']=='23503'
        saved=database.sql('select (select count(*) from ca_runs) as runs,(select count(*) from ca_collection_cases) as cases,(select count(*) from ca_invoices) as invoices')
        for _ in range(2):assert database.call(command='exec',sql=(ROOT/'sql/013_checkpoint_repair.sql').read_text())['data']
        assert checkpoint(database,case,'writes','repair-00',payload)['data']=={'retired':True}
        assert database.sql('select (select count(*) from ca_runs) as runs,(select count(*) from ca_collection_cases) as cases,(select count(*) from ca_invoices) as invoices')==saved
        assert checkpoint(database,case,'get',None)['data']['data']=={'marker':9}
        assert database.sql('select count(*) n from ca_graph_checkpoints where case_id=$1',[case])[0]['n']==8
        assert checkpoint(database,case,'writes','unknown-future',payload)['error']['code']=='23503'
        assert checkpoint(database,case,'writes','repair-00',payload,namespace='other')['error']['code']=='23503'


def test_write_idempotency_negative_indices_and_health_privileges(store_factory,database):
    with client(store_factory) as c:
        run,_=finish(c);job(c,run['run_id']);case=c.get('/api/cases').json()['cases'][0]['id']
        ident='zz-new-checkpoint';assert 'error' not in checkpoint(database,case,'put',ident,{'marker':1})
        for value in ['first','second']:
            writes=[{'task_id':'a','idx':i,'channel':'x','value':value} for i in [0,-1]]
            assert 'error' not in checkpoint(database,case,'writes',ident,writes)
        writes=checkpoint(database,case,'get',ident)['data']['writes']
        assert next(w for w in writes if w['idx']==0)['value']=='first'
        assert next(w for w in writes if w['idx']==-1)['value']=='second'
        assert c.get('/api/health').json()['workflow']['checkpoint']['checkpoint_schema']==14
    database.sql('set role anon')
    try:assert 'error' in database.call(command='sql',sql='select public.ca_checkpoint_health()')
    finally:database.sql('reset role')


def test_checkpoint_sqlstate_and_action_exposed_without_raw_details():
    async def check():
        store=SupabaseStore('https://demo.supabase.co','sb_secret_fake',transport=httpx.MockTransport(lambda request:httpx.Response(400,json={'code':'23503','message':'PRIVATE SQL BODY sb_secret_fake'})))
        try:
            with pytest.raises(StorageError) as saved:await store.rpc('ca_checkpoint',{'p_action':'writes'})
            result=failure(saved.value,'INV-10287','process_invoice')
            assert result['sqlstate']=='23503' and result['checkpoint_action']=='writes'
            assert result['code']=='checkpoint_reference_error'
            assert '014_checkpoint_write_order.sql' in result['message'] and 'PRIVATE' not in json.dumps(result)
        finally:await store.close()
    asyncio.run(check())


def test_unrepaired_checkpoint_function_blocks_new_runs(store_factory,database):
    legacy_function(database)
    with client(store_factory) as c:
        response=c.get('/api/health')
        assert response.status_code==200 and response.json()['workflow']['ready'] is False
        response=c.post('/api/runs',json={'mode':'limited'})
        assert response.status_code==503 and '014_checkpoint_write_order.sql' in response.text
        assert c.get('/api/runs').json()['runs']==[]
    assert database.call(command='exec',sql=(ROOT/'sql/013_checkpoint_repair.sql').read_text())['data']
