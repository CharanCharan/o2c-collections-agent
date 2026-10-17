"""One FastAPI server for the website, Supabase-backed runs and SSE."""

import asyncio
import json
import time
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import UUID

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .runner import RunService, STAGES
from . import risk_model
from .language import LanguageService, facts_for
from .mail.service import MailService
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
            except StorageError:
                pass  # Still serve the page and an actionable health error.
        yield
        if mail:
            await mail.close()
        if service:
            await service.close()

    app = FastAPI(title="Collections Agent · Milestone 6", lifespan=lifespan)
    app.state.runs = service

    @app.middleware('http')
    async def demo_boundary(request: Request,call_next):
        try:
            public.config.check()
        except HTTPException as exc:
            return JSONResponse({'detail':exc.detail},status_code=exc.status_code)
        session=None
        if public.config.enabled and request.url.path not in {'/livez','/api/webhooks/resend'}:
            origin=request.headers.get('origin')
            if request.method not in {'GET','HEAD','OPTIONS'} and origin:
                from urllib.parse import urlsplit
                parsed=urlsplit(origin)
                if parsed.scheme!='https' or parsed.netloc!=request.headers.get('host'):
                    return JSONResponse({'detail':'Cross-origin action rejected.'},status_code=403)
            session=public.session(request)
            request.state.demo_session=session
            request.state.demo_owner=(session.get('owner_until',0)>time.time() or public.owner(request.headers.get('x-collections-owner')))
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
        if public.config.enabled:
            await s.store.rpc("ca_public_health")
            if s.language.enabled and (not s.language.config.free_only or s.language.config.error()):
                raise HTTPException(503,"Public demo requires valid free-only Groq configuration.")
        if mail.config.enabled:
            await mail.readiness()
        model = risk_model.load_model()
        preventive = risk_model.load_model(stage='pre_due')
        return {"status": "ok", "milestone": "M6", "storage": "supabase_postgres",
                "source": "Supabase tables", "invoice_count": info["invoice_count"], "stage_count": len(STAGES),
                "model_version": model["model_version"], "model_training_data": "synthetic",
                "public_demo": {"enabled":public.config.enabled,"daily_run_cap":20,"daily_llm_attempt_cap":40,"per_browser_runs":3,"per_browser_llm_attempts":8},
                "email": mail.config.status(), "language": s.language.status(), "model_versions": {"overdue": model["model_version"], "pre_due": preventive["model_version"]}}

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

    @app.post("/api/runs", status_code=202)
    async def start_run(request: Request):
        run = await backend().create(public_actor=public.actor(request) if public.config.enabled else None)
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
