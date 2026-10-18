"""One FastAPI server for the website, Supabase-backed runs and SSE."""

import asyncio
from datetime import date, datetime, timedelta, timezone
import json
import time
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import UUID
from typing import Literal

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .runner import RunService, STAGES
from . import risk_model, pipeline
from .language import LanguageService, facts_for
from .mail.service import MailService
from .cases import CaseService
from .workflow.agent import CaseAgent
from .workflow.diagnostics import failure
from .workflow.followups import FollowupService
from .public_demo import PublicConfig, PublicAccess, ACTOR
from pydantic import BaseModel, ConfigDict, Field
from .storage import StorageError, StoreRequestError, SupabaseStore


ROOT = Path(__file__).resolve().parents[1]
TERMINAL = {"completed", "failed", "cancelled", "interrupted"}


def create_app(store=None, language=None, mail_config=None, mail_transport=None, public_config=None):
    config_error = None
    if store is None:
        try:
            store = SupabaseStore.from_env(ROOT)
        except StorageError as exc:
            config_error = str(exc)
    service = RunService(store, language=language) if store is not None else None

    mail = MailService(store,service.language,config=mail_config,transport=mail_transport) if service else None

    cases = CaseService(store,service.language) if service else None

    agent = CaseAgent(store,service.language,mail,cases) if service else None
    if cases:cases.agent=agent
    followups = FollowupService(store,agent) if service else None

    public = PublicAccess(public_config or PublicConfig.from_env(),store)
    if service and public.config.enabled:
        async def reserve_public_language():
            await public.reserve_llm(service.language.config)
        service.language.budget_guard = reserve_public_language

    @asynccontextmanager
    async def lifespan(app):
        if service:
            try:
                await service.initialize()
                await service.store.rpc("ca_graph_recover")
            except StorageError:
                pass  # Still serve the page and an actionable health error.
        yield
        if mail:
            await mail.close()
        if service:
            await service.close()

    app = FastAPI(title="Collections Agent · Milestone 6", lifespan=lifespan)
    app.state.runs = service
    app.state.agent = agent
    app.state.followups = followups

    @app.middleware('http')
    async def demo_boundary(request: Request,call_next):
        try:
            public.config.check()
        except HTTPException as exc:
            return JSONResponse({'detail':exc.detail},status_code=exc.status_code)
        session=None
        if request.url.path not in {'/livez','/api/webhooks/resend'}:
            origin=request.headers.get('origin')
            if public.config.enabled and request.method not in {'GET','HEAD','OPTIONS'} and origin:
                from urllib.parse import urlsplit
                parsed=urlsplit(origin)
                if parsed.scheme!='https' or parsed.netloc!=request.headers.get('host'):
                    return JSONResponse({'detail':'Cross-origin action rejected.'},status_code=403)
            session=public.session(request)
            request.state.demo_session=session
            request.state.demo_owner=public.config.enabled and (session.get('owner_until',0)>time.time() or public.owner(request.headers.get('x-collections-owner')))
            actor=public.actor(request)
        else:
            request.state.demo_owner=False
            actor=('webhook',False)
        context=ACTOR.set(actor)
        try:
            response=await call_next(request)
            if session is not None:public.set_cookie(response,session)
            response.headers['X-Content-Type-Options']='nosniff'
            response.headers['X-Frame-Options']='DENY'
            response.headers['Referrer-Policy']='no-referrer'
            if request.url.path.startswith('/api/'):
                response.headers['Cache-Control']='no-store'
            return response
        finally:ACTOR.reset(context)

    @app.get('/livez')
    async def liveness():
        return {'status':'alive','milestone':'M6'}

    @app.get('/api/webhooks/resend')
    async def webhook_reachability():
        return {'status':'reachable','accepts':'signed POST','milestone':'M6'}

    @app.post('/api/operator/login')
    async def operator_login(request: Request,x_collections_owner: str | None = Header(default=None)):
        if not public.config.enabled:raise HTTPException(404,'Public operator login is disabled locally.')
        if not public.owner(x_collections_owner):raise HTTPException(401,'Invalid owner token.')
        request.state.demo_session['owner_until']=int(time.time())+3600
        return {'owner':True,'expires_in_seconds':3600}

    @app.post('/api/operator/logout')
    async def operator_logout(request: Request):
        if public.config.enabled:request.state.demo_session['owner_until']=0
        return {'owner':False}

    def backend():
        if service is None:
            raise StorageError(config_error or "Configure Supabase in the local .env file and restart Python.")
        return service

    @app.exception_handler(StorageError)
    async def storage_error(request, exc):
        return JSONResponse(status_code=exc.status if isinstance(exc, StoreRequestError) else 503,
                            content={"detail": str(exc)})

    @app.exception_handler(risk_model.ModelError)
    async def model_error(request, exc):
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    @app.get('/api/portfolio')
    async def portfolio_preview():
        source=await backend().store.source()
        def build():
            context=pipeline.Context()
            pipeline.ingest(context,source)
            for stage in ['validate','assess','predict','prioritize']:
                getattr(pipeline,stage)(context)
            return pipeline.result_snapshot(context)
        return {'mode':'read_only_preview','agent_started':False,
                'portfolio':await asyncio.to_thread(build)}

    class OpenCaseRequest(BaseModel):
        model_config = ConfigDict(extra='forbid')
        run_id: UUID
        invoice_id: str = Field(min_length=1,max_length=80)

    class CaseReplyRequest(BaseModel):
        model_config = ConfigDict(extra='forbid',strict=True)
        request_id: UUID = Field(strict=False)
        text: str = Field(min_length=1,max_length=4000)

    class DraftRequest(BaseModel):
        model_config = ConfigDict(extra='forbid', strict=True)
        request_id: UUID = Field(strict=False)
        instructions: str = Field(default='', max_length=600)

    class EditDraftRequest(BaseModel):
        model_config = ConfigDict(extra='forbid', strict=True)
        request_id: UUID = Field(strict=False)
        expected_draft: dict
        subject: str = Field(min_length=1, max_length=200)
        body: str = Field(min_length=1, max_length=4000)

    @app.get('/api/cases')
    async def list_cases(request: Request):
        backend()
        return {'cases':await cases.list(public.actor(request)[0])}

    @app.post('/api/cases')
    async def open_case(body: OpenCaseRequest,request: Request):
        await public.allowed(request,body.run_id)
        backend()
        return await cases.open(public.actor(request)[0],str(body.run_id),body.invoice_id)

    @app.post('/api/cases/{case_id}/replies')
    async def case_reply(case_id: UUID,body: CaseReplyRequest,request: Request):
        backend()
        return await cases.reply(public.actor(request)[0],str(case_id),str(body.request_id),body.text)

    @app.post('/api/cases/{case_id}/send-email')
    async def send_case_email(case_id: UUID,request: Request):
        backend()
        # No recipient/body/mode overrides. This endpoint authorizes one explicit user action.
        if await request.body():
            raise HTTPException(422,'This action takes no message or recipient overrides.')
        actor=public.actor(request)[0]
        case=await agent.case(actor,str(case_id))
        generation=case.get('draft_generation') or {}
        if generation.get('status')=='reserved' and datetime.now(timezone.utc)-datetime.fromisoformat(generation['created_at'])<timedelta(minutes=5):
            raise HTTPException(409,'Wait for draft generation, then review the saved reminder before sending.')
        pending=(case.get('workflow') or {}).get('pending')
        if pending:
            if pending['tool']!='send_email':raise HTTPException(409,'This case is waiting for a different reviewed action.')
            return await agent.approve(actor,str(case_id),pending['event_key'],True)
        if case.get('workflow'):
            if case.get('outbound') and case['outbound']['state']=='accepted':return {'case':case}
            if case['workflow']['status'] in {'delivery_unknown','quota_wait'}:
                return await agent.retry_email(actor,str(case_id))
            raise HTTPException(409,'The graph has not authorized a reminder for this case. Review its pending action or hold.')
        return await mail.send_case(actor,str(case_id))

    @app.post('/api/cases/{case_id}/draft')
    async def redraft_case(case_id: UUID, body: DraftRequest, request: Request):
        backend()
        return await cases.redraft(public.actor(request)[0], str(case_id), str(body.request_id), body.instructions)

    @app.post('/api/cases/{case_id}/draft/edit')
    async def edit_case_draft(case_id: UUID, body: EditDraftRequest, request: Request):
        backend()
        return await cases.edit_draft(public.actor(request)[0], str(case_id), str(body.request_id),
                                      body.expected_draft, body.subject, body.body)

    class AgentRequest(BaseModel):
        model_config=ConfigDict(extra='forbid')
        mode: Literal['limited','autopilot']

    class ApprovalRequest(BaseModel):
        model_config=ConfigDict(extra='forbid',strict=True)
        event_key: str=Field(min_length=1,max_length=100)
        approved: bool

    async def require_checkpoint_storage():
        try:ready=await backend().store.rpc('ca_checkpoint_health')
        except StorageError:raise HTTPException(503,'Apply sql/014_checkpoint_write_order.sql after SQL009–013, then retry.') from None
        if not ready.get('ready') or ready.get('checkpoint_schema',0)<14:raise HTTPException(503,'Apply sql/014_checkpoint_write_order.sql after SQL009–013, then retry.')

    @app.post('/api/runs/{run_id}/agent')
    async def start_case_agent(run_id: UUID,body: AgentRequest,request: Request):
        await public.allowed(request,run_id)
        s=backend();actor=public.actor(request)[0]
        await s.store.rpc('ca_workflow_health')
        await require_checkpoint_storage()
        async with agent.job_locks[str(run_id)]:
            result=await s.store.rpc('ca_agent_job',{'p_action':'create','p_session_key':actor,'p_run_id':str(run_id),'p_mode':body.mode})
            if not result['created'] and result['job']['status']=='completed' and result['job']['progress'].get('failed',0)>0:
                result['job']=await s.store.rpc('ca_agent_job',{'p_action':'update','p_session_key':actor,'p_run_id':str(run_id),
                    'p_progress':result['job']['progress'],'p_status':'running'})
                result['created']=True
            if result['created']:
                task=asyncio.create_task(agent.run_job(actor,str(run_id),body.mode))
                s.tasks.add(task);task.add_done_callback(s.tasks.discard)
            return result

    @app.get('/api/runs/{run_id}/agent')
    async def read_case_agent(run_id: UUID,request: Request):
        await public.allowed(request,run_id);s=backend()
        return await s.store.rpc('ca_agent_job',{'p_action':'get','p_session_key':public.actor(request)[0],'p_run_id':str(run_id)})

    @app.get('/api/runs/{run_id}/agent/events')
    async def agent_events(run_id: UUID,request: Request):
        await public.allowed(request,run_id)
        s=backend();actor=public.actor(request)[0];rid=str(run_id)
        queue=agent.events.subscribe(rid)
        try:
            saved=await s.store.rpc('ca_agent_job',{'p_action':'get','p_session_key':actor,'p_run_id':rid})
            current_cases=await cases.list(actor)
        except BaseException:
            agent.events.unsubscribe(rid,queue)
            raise
        async def stream():
            try:
                yield 'retry: 1500\n\n'
                yield 'event: execution\ndata: '+json.dumps({'job':saved,'cases':current_cases,'restored':True})+'\n\n'
                if saved['status'] not in {'running','waiting_for_portfolio'}:return
                while not await request.is_disconnected():
                    try:payload=await asyncio.wait_for(queue.get(),timeout=5)
                    except asyncio.TimeoutError:
                        # Durable catch-up also handles queued waiting-for-analysis jobs.
                        try:
                            job=await s.store.rpc('ca_agent_job',{'p_action':'get','p_session_key':actor,'p_run_id':rid})
                            payload={'job':job}
                        except StorageError:
                            yield ': reconnect when database is available\n\n';continue
                    yield 'event: execution\ndata: '+json.dumps(payload)+'\n\n'
                    if payload.get('job',{}).get('status') in {'completed','interrupted','analysis_failed'}:return
            finally:agent.events.unsubscribe(rid,queue)
        return StreamingResponse(stream(),media_type='text/event-stream',headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})

    @app.get('/api/cases/{case_id}/events')
    async def case_events(case_id: UUID,request: Request):
        backend();actor=public.actor(request)[0];cid=str(case_id);key='case:'+cid
        queue=agent.events.subscribe(key)
        try:saved=await agent.case(actor,cid)
        except BaseException:
            agent.events.unsubscribe(key,queue)
            raise
        async def stream():
            try:
                yield 'retry: 1500\n\nevent: case-update\ndata: '+json.dumps({'case':saved,'restored':True})+'\n\n'
                while not await request.is_disconnected():
                    try:payload=await asyncio.wait_for(queue.get(),timeout=5)
                    except asyncio.TimeoutError:
                        try:payload={'case':await agent.case(actor,cid),'restored':True}
                        except StorageError:
                            yield ': database temporarily unavailable\n\n';continue
                    yield 'event: case-update\ndata: '+json.dumps(payload)+'\n\n'
            finally:agent.events.unsubscribe(key,queue)
        return StreamingResponse(stream(),media_type='text/event-stream',headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})

    @app.post('/api/cases/{case_id}/approve')
    async def approve_case(case_id: UUID,body: ApprovalRequest,request: Request):
        backend()
        return await agent.approve(public.actor(request)[0],str(case_id),body.event_key,body.approved)

    @app.post('/api/cases/{case_id}/resume')
    async def resume_case(case_id: UUID,request: Request):
        backend()
        return await agent.resume(public.actor(request)[0],str(case_id))

    @app.get('/api/agent-jobs')
    async def latest_case_agent(request: Request):
        return {'job':await backend().store.rpc('ca_agent_latest',{'p_session_key':public.actor(request)[0]})}

    @app.get('/api/scenarios')
    async def scenarios():
        return {'scenarios':await backend().store.rpc('ca_scenarios_list')}

    class ClockRequest(BaseModel):
        model_config=ConfigDict(extra='forbid')
        demo_date: date

    class DueRequest(BaseModel):
        model_config=ConfigDict(extra='forbid')
        request_id: UUID

    @app.get('/api/demo-clock')
    async def read_clock(request: Request):
        backend()
        return await followups.clock(public.actor(request)[0])

    @app.post('/api/demo-clock')
    async def advance_clock(body: ClockRequest,request: Request):
        backend()
        return await followups.clock(public.actor(request)[0],body.demo_date)

    def schedule_due(actor,job):
        if job['created']:
            task=asyncio.create_task(followups.run(actor,job['job']['id']))
            service.tasks.add(task);task.add_done_callback(service.tasks.discard)
        return job

    @app.post('/api/followup-checks')
    async def start_due(body: DueRequest,request: Request):
        backend();actor=public.actor(request)[0]
        return schedule_due(actor,await followups.start(actor,str(body.request_id)))

    @app.get('/api/followup-checks')
    async def latest_due(request: Request):
        backend()
        return {'job':await followups.job(public.actor(request)[0])}

    @app.get('/api/followup-checks/{job_id}')
    async def read_due(job_id: UUID,request: Request):
        backend()
        return await followups.job(public.actor(request)[0],str(job_id))

    @app.post('/api/followup-checks/{job_id}/resume')
    async def resume_due(job_id: UUID,request: Request):
        backend();actor=public.actor(request)[0]
        return schedule_due(actor,await followups.resume(actor,str(job_id)))

    @app.post('/api/cases/{case_id}/followup-email')
    async def send_followup_email(case_id: UUID,request: Request):
        backend()
        if await request.body():raise HTTPException(422,'No recipient or body overrides allowed.')
        actor=public.actor(request)[0];c=await agent.case(actor,str(case_id));w=c.get('workflow') or {};pending=w.get('pending')
        if pending and pending['tool']=='send_followup_email':return await agent.approve(actor,str(case_id),pending['event_key'],True)
        if pending:raise HTTPException(409,'A different action is awaiting review.')
        if (w.get('followup') or {}).get('status')=='accepted':return {'case':c}
        return await agent.retry_followup(actor,str(case_id))

    @app.get("/api/model")
    async def model_info():
        return risk_model.model_card(risk_model.load_model())

    @app.get("/api/model/pre-due")
    async def pre_due_model_info():
        return risk_model.model_card(risk_model.load_model(stage='pre_due'))

    @app.get("/api/health")
    async def health():
        s = backend()
        await s.initialize()
        info = await s.store.health()
        await s.store.rpc("ca_language_health")
        public_info = {}
        if public.config.enabled:
            public_info = await s.store.rpc("ca_public_health")
            if s.language.enabled and (not s.language.config.free_only or s.language.config.error()):
                raise HTTPException(503,"Public demo requires valid free-only Groq configuration.")
        if mail.config.enabled:
            await mail.readiness()
        try:
            await s.store.rpc('ca_workflow_health')
            checkpoint=await s.store.rpc('ca_checkpoint_health')
            workflow={'ready':bool(checkpoint.get('ready') and checkpoint.get('checkpoint_schema',0)>=14),'engine':'langgraph','version':'1.2.16','checkpoint':checkpoint}
        except StorageError:
            workflow={'ready':False,'error':'Apply sql/014_checkpoint_write_order.sql after existing SQL009–013 to repair checkpoint storage.'}
        try:
            await s.store.rpc('ca_followup_health')
            followup_status={'ready':True,'schema':12,'scheduler':'explicit_demo_check'}
        except StorageError:
            followup_status={'ready':False,'error':'Apply sql/012_promise_followups.sql to enable demo-clock follow-ups.'}
        try:
            ai_draft = await s.store.rpc('ca_ai_draft_health')
        except StorageError:
            ai_draft = {'ready':False,'error':'Apply sql/015_ai_draft.sql after SQL014 to enable Draft with AI.'}
        try:
            draft_edit = await s.store.rpc('ca_draft_edit_health')
        except StorageError:
            draft_edit = {'ready':False,'error':'Apply sql/017_manual_draft.sql after SQL015 to enable Edit draft.'}
        model = risk_model.load_model()
        preventive = risk_model.load_model(stage='pre_due')
        return {"status": "ok", "app_version":"v2.23", "ui_version":"workflow-23", "milestone": "M6", "storage": "supabase_postgres",
                "source": "Supabase tables", "invoice_count": info["invoice_count"], "stage_count": len(STAGES),
                "model_version": model["model_version"], "model_training_data": "synthetic",
                "public_demo": {"enabled":public.config.enabled,"daily_run_limit_enabled":public_info.get('daily_run_limit_enabled',True) if public.config.enabled else False,
                                "daily_run_cap":public_info.get('daily_run_cap',20) if public.config.enabled else None,
                                "per_browser_runs":public_info.get('per_browser_runs',3) if public.config.enabled else None,
                                "daily_llm_attempt_cap":public_info.get('daily_llm_attempt_cap',40),"per_browser_llm_attempts":public_info.get('per_browser_llm_attempts',8)},
                "workflow":workflow,"followups":followup_status,"ai_draft":ai_draft,"draft_edit":draft_edit,"email": mail.config.status(), "language": s.language.status(), "model_versions": {"overdue": model["model_version"], "pre_due": preventive["model_version"]}}

    @app.get('/api/reply-examples')
    async def reply_examples():
        return {'examples': [{k: v for k, v in e.items() if k != 'expected_intent'}
                for e in json.loads((ROOT / 'fixtures/replies.json').read_text())]}

    class ExampleRequest(BaseModel):
        model_config = ConfigDict(extra='forbid')
        example_id: str

    @app.post('/api/runs/{run_id}/invoices/{invoice_id}/classify-example')
    async def classify_example(run_id: UUID, invoice_id: str, body: ExampleRequest, request: Request):
        await public.allowed(request,run_id)
        s = backend()
        await s.store.rpc('ca_language_health')
        examples = json.loads((ROOT / 'fixtures/replies.json').read_text())
        example = next((e for e in examples if e['id'] == body.example_id), None)
        if example is None:
            raise HTTPException(404, 'Unknown synthetic example.')
        # Local single-process POC: serialize reviews to avoid concurrent duplicate calls.
        async with s.language.reply_lock:
            run = await s.store.get_run(str(run_id))
            if run is None:
                raise HTTPException(404, 'Run not found.')
            if run['status'] != 'completed':
                raise HTTPException(409, 'Finish a successful run first.')
            row = next((r for r in run['result']['invoices'] if r['id'] == invoice_id), None)
            if row is None:
                raise HTTPException(404, 'Invoice not found in this run.')
            if body.example_id in row.get('reply_reviews', {}):
                return public.sanitize(request,{'recorded': False, 'run': run})
            facts = facts_for(row, run['result'])
            review = await s.language.classify(facts, example['text'])
            review.update({'example_id': body.example_id, 'example_text': example['text']})
            response = await s.store.rpc('ca_record_reply_example', {'p_run_id': str(run_id),
                'p_invoice_id': invoice_id, 'p_example_id': body.example_id, 'p_review': review})
            return public.sanitize(request,response)

    class SendRequest(BaseModel):
        model_config = ConfigDict(extra='forbid',strict=True)
        confirm_reviewed: bool

    class ResolveRequest(BaseModel):
        model_config = ConfigDict(extra='forbid')
        intent: str = Field(max_length=30)
        promise_date: str | None = Field(default=None,max_length=10)
        promise_amount: str | None = Field(default=None,max_length=20)
        evidence_quote: str = Field(default='',max_length=500)

    def email_backend():
        backend()
        return mail

    @app.get('/api/email/owner-config')
    async def email_owner_config(x_collections_owner: str | None = Header(default=None)):
        m=email_backend(); m.authorize(x_collections_owner)
        return {'recipient':m.config.recipient,'sender':m.config.sender}

    @app.get('/api/runs/{run_id}/email')
    async def email_activity(run_id: UUID,request: Request):
        public.require_owner(request)
        return await email_backend().activity(str(run_id))

    @app.post('/api/runs/{run_id}/invoices/{invoice_id}/send-email')
    async def send_email(run_id: UUID,invoice_id: str,body: SendRequest,x_collections_owner: str | None = Header(default=None)):
        if body.confirm_reviewed is not True:raise HTTPException(422,'Confirm that you reviewed the displayed draft.')
        return await email_backend().send(str(run_id),invoice_id,x_collections_owner)

    @app.post('/api/runs/{run_id}/replies/{reply_id}/resolve')
    async def resolve_reply(run_id: UUID,reply_id: UUID,body: ResolveRequest,x_collections_owner: str | None = Header(default=None)):
        return await email_backend().resolve(str(run_id),str(reply_id),body,x_collections_owner)

    @app.post('/api/webhooks/resend')
    async def resend_webhook(request: Request):
        raw=bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw)>65536:raise HTTPException(413,'Webhook exceeds POC size limit.')
        return await email_backend().webhook(bytes(raw),request.headers)

    class RunStartRequest(BaseModel):
        model_config=ConfigDict(extra='forbid')
        mode: Literal['limited','autopilot']

    @app.post("/api/runs", status_code=202)
    async def start_run(request: Request,body: RunStartRequest | None = None):
        s=backend();actor=public.actor(request)[0]
        if body:await require_checkpoint_storage()
        async def plan(run):
            await s.store.rpc('ca_agent_plan',{'p_session_key':actor,'p_run_id':run.id,'p_mode':body.mode})
        async def after(run):
            try:
                if run.status!='completed':
                    await s.store.rpc('ca_agent_job',{'p_action':'update','p_session_key':actor,'p_run_id':run.id,
                        'p_progress':{'error':'Portfolio analysis did not finish. Start a new run.'},'p_status':'analysis_failed'})
                else:
                    job=await s.store.rpc('ca_agent_job',{'p_action':'create','p_session_key':actor,'p_run_id':run.id,'p_mode':body.mode})
                    if job['created']:await agent.run_job(actor,run.id,body.mode)
            except StorageError as exc:
                detail=failure(exc,None,'start_case_job')
                try:
                    saved=await s.store.rpc('ca_agent_job',{'p_action':'get','p_session_key':actor,'p_run_id':run.id})
                    progress={**saved['progress'],'failure':detail,'error':detail['message']}
                    await s.store.rpc('ca_agent_job',{'p_action':'update','p_session_key':actor,'p_run_id':run.id,
                        'p_progress':progress,'p_status':'interrupted'})
                except StorageError:pass  # Never overwrite a report we could not read.

        run = await s.create(public_actor=public.actor(request) if public.config.enabled else None,
            prepare_run=plan if body else None,after_run=after if body else None)
        return {"run_id": run.id, "status": run.status, "events_url": f"/api/runs/{run.id}/events"}

    @app.get("/api/runs")
    async def saved_runs(request: Request):
        if public.config.enabled and not request.state.demo_owner:
            actor,_=public.actor(request)
            return {"runs":await backend().store.rpc("ca_public_recent",{"p_session_key":actor})}
        return {"runs": await backend().store.recent()}

    @app.get("/api/runs/{run_id}")
    async def read_run(run_id: UUID,request: Request):
        await public.allowed(request,run_id)
        run = await backend().store.get_run(str(run_id))
        if run is None:
            raise HTTPException(404, "Run not found in this database.")
        return public.sanitize(request,run)

    @app.get("/api/runs/{run_id}/events")
    async def events(run_id: UUID, request: Request, last_event_id: str | None = Header(default=None)):
        await public.allowed(request,run_id)
        store = backend().store
        try:
            after = max(0, int(last_event_id or 0))
        except ValueError as exc:
            raise HTTPException(400, "Last-Event-ID must be an integer") from exc
        first = await store.feed(str(run_id), after)
        if first is None:
            raise HTTPException(404, "Run not found in this database.")

        async def stream():
            cursor, current, idle = after, first, 0
            yield "retry: 1500\n\n"
            while True:
                for event in current["events"]:
                    cursor = event["event_id"]
                    if not public.event(request,event):continue
                    yield f"id: {cursor}\nevent: update\ndata: {json.dumps(event)}\n\n"
                if current["status"] in TERMINAL or await request.is_disconnected():
                    return
                # Poll persisted events, not simulated work. SSE still pushes each
                # recorded update to the browser. No extra realtime service needed.
                await asyncio.sleep(0.35)
                try:
                    current = await store.feed(str(run_id), cursor)
                    if current is None:
                        raise StorageError("Run was removed from the database.")
                except StorageError as exc:
                    # Transient connection errors are not fabricated saved events.
                    payload = json.dumps({"message": str(exc)})
                    yield f"event: connection-error\ndata: {payload}\n\n"
                    return
                idle = 0 if current["events"] else idle + 1
                if idle >= 28:
                    yield ": heartbeat\n\n"
                    idle = 0

        return StreamingResponse(stream(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    @app.post("/api/runs/{run_id}/invoices/{invoice_id}/dry-run")
    async def dry_run(run_id: UUID, invoice_id: str,request: Request):
        await public.allowed(request,run_id)
        return public.sanitize(request,await backend().store.approve(str(run_id),invoice_id))

    @app.get("/")
    async def index():
        return FileResponse(ROOT / "dist" / "index.html")

    app.mount("/assets", StaticFiles(directory=ROOT / "dist"), name="assets")
    return app


app = create_app()
