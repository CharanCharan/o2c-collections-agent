"""Actual committed graph updates, durable catch-up and owned SSE snapshots."""
import asyncio
import json
from tests.test_case_agent import client,job
from tests.test_milestone_2 import finish


def test_committed_node_events_job_completion_and_readonly_sse(store_factory):
    with client(store_factory) as c:
        run,_=finish(c);rid=run['run_id'];agent=c.app.state.agent
        queue=agent.events.subscribe(rid)
        result=job(c,rid)
        events=[]
        while not queue.empty():events.append(queue.get_nowait())
        agent.events.unsubscribe(rid,queue)
        assert events[-1]['job']['status']=='completed'
        cases=[e['case'] for e in events if 'case' in e]
        assert cases
        nodes=[x['workflow']['activity'][-1]['node'] for x in cases]
        assert 'load' in nodes and 'choose' in nodes and 'approval' in nodes
        stored={x['id']:x for x in c.get('/api/cases').json()['cases']}
        for case in cases:
            latest=case['workflow']['activity'][-1]
            assert any(a['key']==latest['key'] for a in stored[case['id']]['workflow']['activity'])
        snapshot=c.get(f'/api/runs/{rid}/agent/events')
        assert snapshot.status_code==200 and snapshot.headers['content-type'].startswith('text/event-stream')
        data=json.loads(next(line[6:] for line in snapshot.text.splitlines() if line.startswith('data: ')))
        assert data['job']['status']=='completed' and len(data['cases'])==6 and data['restored']
        assert 'session_key' not in snapshot.text
        assert c.get(f'/api/runs/{rid}/agent').json()==result
        assert not agent.events.listeners
    with client(store_factory) as other:
        assert other.get(f'/api/runs/{rid}/agent/events').status_code in {403,404}
        assert not other.app.state.agent.events.listeners


def test_repeated_job_retains_cases_without_new_graph_execution(store_factory):
    with client(store_factory) as c:
        first,_=finish(c);job(c,first['run_id'])
        second,_=finish(c);result=job(c,second['run_id'])
        assert result['progress']['retained']==6


def test_execution_delivery_buffer_bounded_and_unsubscribed():
    from backend.workflow.events import ExecutionEvents
    events=ExecutionEvents();queue=events.subscribe('owned-run')
    for i in range(200):events.publish('owned-run',{'sequence':i})
    assert queue.qsize()==128 and queue.get_nowait()['sequence']==72
    events.unsubscribe('owned-run',queue)
    assert not events.listeners


def test_manual_approval_publishes_committed_invoice_activity(store_factory):
    from tests.test_milestone_5 import ResendMock
    provider=ResendMock()
    with client(store_factory,provider) as c:
        run,_=finish(c);job(c,run['run_id'])
        case=next(x for x in c.get('/api/cases').json()['cases'] if x['workflow'].get('pending'))
        agent=c.app.state.agent;key='case:'+case['id'];queue=agent.events.subscribe(key)
        assert c.post(f"/api/cases/{case['id']}/send-email").status_code==200
        events=[]
        while not queue.empty():events.append(queue.get_nowait())
        agent.events.unsubscribe(key,queue)
        assert len(provider.sent)==1
        activities=[e['case']['workflow']['activity'][-1] for e in events]
        assert any(a['node']=='execute' and a['status']=='started' for a in activities)
        assert any(a['node']=='execute' and a['status']=='completed' for a in activities)
        assert events[-1]['case']['outbound']['state']=='accepted'
