"""HTTP endpoints and static frontend. Run from the repository root with Uvicorn."""

import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .runner import Run, RunService, timestamp


ROOT = Path(__file__).resolve().parents[1]


def create_app(data_path: Path | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app):
        yield
        await app.state.runs.close()

    app = FastAPI(title="Collections Agent · Milestone 1", lifespan=lifespan)
    app.state.runs = RunService(data_path or ROOT / "data" / "invoices.json")

    def get_run(run_id: str) -> Run:
        run = app.state.runs.runs.get(run_id)
        if run is None:
            raise HTTPException(404, "Run not found. The server may have restarted or the run expired. Start a new run.")
        return run

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "milestone": "M1", "storage": "process_memory_only",
                "message": "Charan's collections backend is running", "stage_count": 5}

    @app.post("/api/runs", status_code=202)
    async def start_run():
        try:
            run = app.state.runs.create()
        except RuntimeError as exc:
            raise HTTPException(429, str(exc)) from exc
        return {"run_id": run.id, "status": run.status, "events_url": f"/api/runs/{run.id}/events"}

    @app.get("/api/runs/{run_id}")
    async def read_run(run_id: str):
        run = get_run(run_id)
        async with run.lock:
            return run.view()

    @app.get("/api/runs/{run_id}/events")
    async def events(run_id: str, request: Request, last_event_id: str | None = Header(default=None)):
        run = get_run(run_id)
        try:
            after = max(0, int(last_event_id or 0))
        except ValueError as exc:
            raise HTTPException(400, "Last-Event-ID must be an integer") from exc

        async def stream():
            cursor = after
            yield "retry: 1500\n\n"
            while True:
                # Hold the condition while inspecting/waiting to avoid missed notifications.
                async with run.condition:
                    batch = [e for e in run.events if e["event_id"] > cursor]
                    terminal = run.status in {"completed", "failed", "cancelled"}
                    if not batch and not terminal:
                        try:
                            await asyncio.wait_for(run.condition.wait(), timeout=10)
                        except asyncio.TimeoutError:
                            pass
                        batch = [e for e in run.events if e["event_id"] > cursor]
                        terminal = run.status in {"completed", "failed", "cancelled"}
                if await request.is_disconnected():
                    return
                for event in batch:
                    cursor = event["event_id"]
                    yield f"id: {cursor}\nevent: update\ndata: {json.dumps(event)}\n\n"
                if terminal:
                    return
                if not batch:
                    yield ": heartbeat\n\n"

        return StreamingResponse(stream(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    @app.post("/api/runs/{run_id}/invoices/{invoice_id}/dry-run")
    async def dry_run(run_id: str, invoice_id: str):
        run = get_run(run_id)
        async with run.lock:
            if run.status != "completed":
                raise HTTPException(409, "Finish a successful collections run first")
            row = next((r for r in run.context.invoices if r["id"] == invoice_id), None)
            if row is None:
                raise HTTPException(404, "Invoice not found in this run")
            if not row["eligible"] or not row["draft"]:
                raise HTTPException(409, "This invoice has no eligible reminder draft")
            if row["contacted"]:
                return {"recorded": False, "message": "Already recorded; no duplicate created", "run": run.view()}
            row["contacted"] = True
            row["action"] = "Dry run recorded"
            run.interactions.append({"invoice_id": invoice_id, "type": "approved_dry_run",
                                     "timestamp": timestamp(), "draft": row["draft"].copy(), "email_sent": False})
            await run.emit("approval", "completed", f"Approved dry-run reminder for {row['customer']} ({invoice_id}). No email was sent.",
                           result={"invoice_id": invoice_id, "email_sent": False})
            return {"recorded": True, "run": run.view()}

    @app.get("/")
    async def index():
        return FileResponse(ROOT / "dist" / "index.html")

    app.mount("/assets", StaticFiles(directory=ROOT / "dist"), name="assets")
    return app


app = create_app()
