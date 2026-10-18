"""Exercise real LangGraph save ordering against actual SQL with network latency."""
import asyncio
from pathlib import Path
from typing import TypedDict
import pytest
from langgraph.graph import StateGraph,START,END
from backend.workflow.checkpoints import SupabaseSaver
from backend.storage import StorageError
from tests.test_case_agent import client,job,seed
from tests.test_milestone_2 import finish

ROOT=Path(__file__).resolve().parents[1]

class State(TypedDict):
    value:int

@pytest.mark.parametrize('repair',[False,True])
def test_network_delayed_parent_put(store_factory,database,repair):
    with client(store_factory) as c:
        run,_=finish(c);job(c,run['run_id']);case=c.get('/api/cases').json()['cases'][0]['id']
    assert database.call(command='exec',sql=(ROOT/'sql/013_checkpoint_repair.sql').read_text())['data']
    if repair:
        assert database.call(command='exec',sql=(ROOT/'sql/014_checkpoint_write_order.sql').read_text())['data']
    async def check():
        store=store_factory();rpc=store.rpc;seen=[]
        async def delayed(name,params=None):
            if name=='ca_checkpoint':
                action=params['p_action']
                if action=='put':await asyncio.sleep(.03)
                seen.append(action)
            return await rpc(name,params)
        store.rpc=delayed
        builder=StateGraph(State);builder.add_node('increment',lambda state:{'value':state['value']+1})
        builder.add_edge(START,'increment');builder.add_edge('increment',END)
        graph=builder.compile(checkpointer=SupabaseSaver(store))
        config={'configurable':{'thread_id':case,'checkpoint_ns':''}}
        # Use fresh case checkpoint namespace via fresh case's saved graph state reset in isolated DB.
        database.sql('delete from ca_graph_checkpoints where case_id=$1',[case])
        try:
            if repair:
                assert (await graph.ainvoke({'value':1},config,durability='sync'))['value']==2
                assert (await graph.aget_state(config)).values['value']==2
                assert not (await graph.aget_state(config)).next
            else:
                with pytest.raises(StorageError) as error:await graph.ainvoke({'value':1},config,durability='sync')
                assert error.value.sqlstate=='23503'
            assert seen.index('writes')<seen.index('put'),seen
        finally:await store.close()
    try:asyncio.run(check())
    finally:database.call(command='exec',sql=(ROOT/'sql/014_checkpoint_write_order.sql').read_text())


def test_early_writes_durable_bounded_idempotent_and_case_owned(store_factory,database):
    from tests.test_checkpoint_repair import checkpoint
    from uuid import uuid4
    with client(store_factory) as c:
        run,_=finish(c);job(c,run['run_id']);case=c.get('/api/cases').json()['cases'][0]['id']
        saved=database.sql('select (select count(*) from ca_runs) runs,(select count(*) from ca_collection_cases) cases,(select count(*) from ca_case_mail) mails')
        for _ in range(2):assert database.call(command='exec',sql=(ROOT/'sql/014_checkpoint_write_order.sql').read_text())['data']
        assert database.sql('select (select count(*) from ca_runs) runs,(select count(*) from ca_collection_cases) cases,(select count(*) from ca_case_mail) mails')==saved
        for i in range(12):
            ident=f'zz-early-{i:02}'
            payload=[{'task_id':'t','idx':0,'channel':'x','value':i}]
            assert 'error' not in checkpoint(database,case,'writes',ident,payload,namespace='pending')
        assert checkpoint(database,case,'get',None,namespace='pending')['data'] is None
        assert database.sql("select count(distinct checkpoint_id) n from ca_graph_writes where case_id=$1 and namespace='pending'",[case])[0]['n']==8
        ident='zz-early-11'
        assert 'error' not in checkpoint(database,case,'put',ident,{'marker':True},namespace='pending')
        assert checkpoint(database,case,'get',ident,namespace='pending')['data']['writes'][0]['value']==11
        assert checkpoint(database,str(uuid4()),'writes',ident,payload)['error']['code']=='23503'
        # Unpaired and paired writes both cascade on deletion of their owning case.
        database.sql('delete from ca_collection_cases where id=$1',[case])
        assert database.sql('select count(*) n from ca_graph_writes where case_id=$1',[case])[0]['n']==0


def test_full_portfolio_with_delayed_saves_and_approval_resume(store_factory,database):
    seed(database)
    stores=[]
    def delayed_factory():
        store=store_factory();rpc=store.rpc
        async def delayed(name,params=None):
            if name=='ca_checkpoint':
                await asyncio.sleep(.015 if params['p_action']=='put' else .001)
            return await rpc(name,params)
        store.rpc=delayed;stores.append(store);return store
    with client(delayed_factory) as c:
        run,_=finish(c);rid=run['run_id'];result=job(c,rid)
        assert result['progress']['failed']==0,result
        cases=c.get('/api/cases').json()['cases']
        assert len(cases)==24
        pending=next(case for case in cases if (case.get('workflow') or {}).get('pending'))
        response=c.post(f"/api/cases/{pending['id']}/approve",json={'event_key':pending['workflow']['pending']['event_key'],'approved':True})
        assert response.status_code==200,response.text
        # Repeating the portfolio job retains cases; it cannot repeat accepted sends.
        again=job(c,rid)
        assert again['progress']['failed']==0


def test_v13_ready_marker_is_insufficient_for_new_app(store_factory,database):
    assert database.call(command='exec',sql=(ROOT/'sql/013_checkpoint_repair.sql').read_text())['data']
    with client(store_factory) as c:
        assert c.get('/api/health').json()['workflow']['ready'] is False
        response=c.post('/api/runs',json={'mode':'limited'})
        assert response.status_code==503 and '014_checkpoint_write_order.sql' in response.text
    assert database.call(command='exec',sql=(ROOT/'sql/014_checkpoint_write_order.sql').read_text())['data']


def test_retention_keeps_linked_writes_and_rejects_public_access(store_factory,database):
    from tests.test_checkpoint_repair import checkpoint
    with client(store_factory) as c:
        run,_=finish(c);job(c,run['run_id']);case=c.get('/api/cases').json()['cases'][0]['id']
        for i in range(12):
            ident=f'retention-{i:02}'
            payload=[{'task_id':'t','idx':0,'channel':'x','value':i}]
            assert 'error' not in checkpoint(database,case,'writes',ident,payload,namespace='retention')
            assert 'error' not in checkpoint(database,case,'put',ident,{'marker':i},namespace='retention')
        assert database.sql("select count(*) n from ca_graph_checkpoints where case_id=$1 and namespace='retention'",[case])[0]['n']==8
        assert database.sql("select count(*) n from ca_graph_writes where case_id=$1 and namespace='retention'",[case])[0]['n']==8
        assert checkpoint(database,case,'writes','retention-00',payload,namespace='retention')['data']=={'retired':True}
        assert checkpoint(database,case,'get','retention-11',namespace='other')['data'] is None
        assert checkpoint(database,case,'get','retention-11',namespace='retention')['data']['writes'][0]['value']==11
    database.sql('set role anon')
    try:
        assert 'error' in database.call(command='sql',sql='select * from ca_graph_writes')
        assert 'error' in database.call(command='sql',sql='select public.ca_checkpoint_health()')
    finally:database.sql('reset role')
