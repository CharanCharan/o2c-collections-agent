"""Orchestrate actual work; Supabase is the source of saved history (M2).

Use one backend process per demo database. A restart marks abandoned work
interrupted. Saved history survives; background jobs are not automatically resumed.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

from . import pipeline
from .storage import StorageError
from .language import LanguageService


STAGES = ["ingest", "validate", "assess", "predict", "prioritize", "draft"]


def timestamp():
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Run:
    id: str
    process_id: str
    store: object
    status: str = "queued"
    context: pipeline.Context = field(default_factory=pipeline.Context)

    async def emit(self, stage, status, message, run_status=None, saved_result=None, source=None, **details):
        event = {"stage": stage, "status": status, "message": message,
                 "timestamp": timestamp(), **details}
        saved = await self.store.append_event(self.id, self.process_id, str(uuid4()), event,
                                             run_status, saved_result, source)
        if run_status:
            self.status = run_status  # Only after the database commit succeeds.
        return saved


class RunService:
    def __init__(self, store, language=None):
        self.store = store
        self.language = language or LanguageService.from_env()
        self.process_id = str(uuid4())
        self.tasks: set[asyncio.Task] = set()
        self.initialized = False
        self.init_lock = asyncio.Lock()

    async def initialize(self):
        async with self.init_lock:
            if not self.initialized:
                await self.store.health()
                await self.store.rpc("ca_language_health")
                await self.store.recover(self.process_id)
                self.initialized = True

    async def create(self, public_actor=None, prepare_run=None, after_run=None):
        await self.initialize()
        run = Run(str(uuid4()), self.process_id, self.store)
        if public_actor is None:
            await self.store.create_run(run.id, self.process_id, pipeline.result_snapshot(run.context))
        else:
            actor,owner=public_actor
            await self.store.rpc("ca_public_create", {"p_run_id":run.id,"p_process_id":self.process_id,
                "p_initial_result":pipeline.result_snapshot(run.context),"p_session_key":actor,"p_owner":owner})
        if prepare_run:
            try:await prepare_run(run)
            except StorageError:
                await self._fail(run,'case_agent_setup','failed','Could not save case-agent setup. No case actions started.',None)
                raise
        task = asyncio.create_task(self.execute(run,after_run))
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        return run

    async def execute(self, run, after_run=None):
        stage = "ingest"
        try:
            for stage in STAGES:
                await run.emit(stage, "started", f"Starting {stage}.", run_status="running")
                started = perf_counter()
                if stage == "ingest":
                    source = await self.store.source()
                    result = await asyncio.to_thread(pipeline.ingest, run.context, source)
                elif stage == 'draft':
                    async def tool_event(status, message, audit):
                        snapshot = pipeline.result_snapshot(run.context)
                        await run.emit('llm_draft', status, message, saved_result=snapshot,
                                       result=audit, snapshot=snapshot)
                    result = await self.language.draft(run.context, emit=tool_event)
                else:
                    result = await asyncio.to_thread(getattr(pipeline, stage), run.context)
                message = result.pop("message")
                snapshot = pipeline.result_snapshot(run.context)
                await run.emit(stage, "completed", message, saved_result=snapshot,
                               source=run.context.raw if stage == "ingest" else None,
                               duration_ms=round((perf_counter() - started) * 1000, 2),
                               result=result, snapshot=snapshot)
            snapshot = pipeline.result_snapshot(run.context)
            await run.emit("run", "completed", "Collections run completed and saved in Supabase.",
                           run_status="completed", saved_result=snapshot, result=snapshot)
        except asyncio.CancelledError:
            await self._fail(run, stage, "cancelled", "Backend is shutting down. Start a new run.", None)
            raise
        except Exception as exc:
            # StorageError messages are sanitized by the adapter; no credentials
            # or raw provider response bodies are included in events or logs.
            detail = str(exc)[:1200]
            logging.warning("Collections run %s stopped at %s (%s)", run.id, stage, type(exc).__name__)
            await self._fail(run, stage, "failed", f"The {stage} operation failed.",
                             {"type": type(exc).__name__, "detail": detail})

        finally:
            if after_run:await after_run(run)

    async def _fail(self, run, stage, status, message, error):
        try:
            await run.emit(stage, "failed", message, run_status=status, error=error)
        except StorageError:
            # A disconnected DB cannot store a failure. Never fake a successful
            # event or fall back to memory. Restart recovery will mark it interrupted.
            logging.warning("Could not persist failure for run %s; storage unavailable or run inactive", run.id)

    async def close(self):
        for task in list(self.tasks):
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        await self.language.close()
        await self.store.close()
