"""One FastAPI server for the website, Supabase-backed runs and SSE."""

import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import UUID

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .runner import RunService, STAGES
from . import risk_model
from .language import LanguageService, facts_for
from pydantic import BaseModel, ConfigDict
from .storage import StorageError, StoreRequestError, SupabaseStore


ROOT = Path(__file__).resolve().parents[1]
TERMINAL = {"completed", "failed", "cancelled", "interrupted"}


def create_app(store=None, language=None):
    config_error = None
    if store is None:
        try:
            store = SupabaseStore.from_env(ROOT)
        except StorageError as exc:
            config_error = str(exc)
    service = RunService(store, language=language) if store is not None else None

    @asynccontextmanager
    async def lifespan(app):
        if service:
            try:
                await service.initialize()
            except StorageError:
                pass  # Still serve the page and an actionable health error.
        yield
        if service:
            await service.close()

    app = FastAPI(title="Collections Agent · Milestone 4", lifespan=lifespan)
    app.state.runs = service

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
        model = risk_model.load_model()
        preventive = risk_model.load_model(stage='pre_due')
        return {"status": "ok", "milestone": "M4", "storage": "supabase_postgres",
                "source": "Supabase tables", "invoice_count": info["invoice_count"], "stage_count": len(STAGES),
                "model_version": model["model_version"], "model_training_data": "synthetic",
                "language": s.language.status(), "model_versions": {"overdue": model["model_version"], "pre_due": preventive["model_version"]}}

    @app.get('/api/reply-examples')
    async def reply_examples():
        return {'examples': [{k: v for k, v in e.items() if k != 'expected_intent'}
                for e in json.loads((ROOT / 'fixtures/replies.json').read_text())]}

    class ExampleRequest(BaseModel):
        model_config = ConfigDict(extra='forbid')
        example_id: str

    @app.post('/api/runs/{run_id}/invoices/{invoice_id}/classify-example')
    async def classify_example(run_id: UUID, invoice_id: str, body: ExampleRequest):
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
                return {'recorded': False, 'run': run}
            facts = facts_for(row, run['result'])
            review = await s.language.classify(facts, example['text'])
            review.update({'example_id': body.example_id, 'example_text': example['text']})
            return await s.store.rpc('ca_record_reply_example', {'p_run_id': str(run_id),
                'p_invoice_id': invoice_id, 'p_example_id': body.example_id, 'p_review': review})

    @app.post("/api/runs", status_code=202)
    async def start_run():
        run = await backend().create()
        return {"run_id": run.id, "status": run.status, "events_url": f"/api/runs/{run.id}/events"}

    @app.get("/api/runs")
    async def saved_runs():
        return {"runs": await backend().store.recent()}

    @app.get("/api/runs/{run_id}")
    async def read_run(run_id: UUID):
        run = await backend().store.get_run(str(run_id))
        if run is None:
            raise HTTPException(404, "Run not found in this database.")
        return run

    @app.get("/api/runs/{run_id}/events")
    async def events(run_id: UUID, request: Request, last_event_id: str | None = Header(default=None)):
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
    async def dry_run(run_id: UUID, invoice_id: str):
        return await backend().store.approve(str(run_id), invoice_id)

    @app.get("/")
    async def index():
        return FileResponse(ROOT / "dist" / "index.html")

    app.mount("/assets", StaticFiles(directory=ROOT / "dist"), name="assets")
    return app


app = create_app()
