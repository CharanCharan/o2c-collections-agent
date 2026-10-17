"""Run isolation, orchestration, and an in-memory event ledger for M1.

Postgres persistence is M2. Restarting this process clears all runs and events.
"""

import asyncio
import copy
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from . import pipeline


STAGES = ["ingest", "validate", "assess", "prioritize", "draft"]


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Run:
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=timestamp)
    status: str = "queued"
    context: pipeline.Context = field(default_factory=pipeline.Context)
    events: list[dict] = field(default_factory=list)
    condition: asyncio.Condition = field(default_factory=asyncio.Condition)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    interactions: list[dict] = field(default_factory=list)

    async def emit(self, stage: str, status: str, message: str, **details) -> dict:
        async with self.condition:
            event = {
                "run_id": self.id, "event_id": len(self.events) + 1,
                "stage": stage, "status": status, "message": message,
                "timestamp": timestamp(), **details,
            }
            # Keep historical event results immutable as later stages change context.
            self.events.append(copy.deepcopy(event))
            self.condition.notify_all()
            return copy.deepcopy(event)

    def view(self) -> dict:
        return copy.deepcopy({
            "run_id": self.id, "created_at": self.created_at, "status": self.status,
            "result": pipeline.result_snapshot(self.context),
            "events": self.events, "interactions": self.interactions,
            "storage": "process_memory_only",
        })


class RunService:
    def __init__(self, data_path: Path):
        self.data_path = data_path
        self.runs: dict[str, Run] = {}
        self.tasks: set[asyncio.Task] = set()

    def create(self) -> Run:
        if sum(run.status in {"queued", "running"} for run in self.runs.values()) >= 5:
            raise RuntimeError("Five runs are already active. Try again after they finish.")
        # Bound memory in the local POC. Oldest completed runs expire after 100 runs.
        while len(self.runs) >= 100:
            old = next((key for key, run in self.runs.items() if run.status not in {"queued", "running"}), None)
            if old is None:
                raise RuntimeError("No run capacity available")
            del self.runs[old]
        run = Run()
        self.runs[run.id] = run
        task = asyncio.create_task(self.execute(run))
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        return run

    async def execute(self, run: Run):
        run.status = "running"
        stage = "ingest"
        try:
            for stage in STAGES:
                await run.emit(stage, "started", f"Starting {stage}.")
                started = perf_counter()
                operation = getattr(pipeline, stage)
                args = (run.context, self.data_path) if stage == "ingest" else (run.context,)
                # Each thread job completes before the success event is emitted.
                async with run.lock:
                    result = await asyncio.to_thread(operation, *args)
                    message = result.pop("message")
                    await run.emit(stage, "completed", message,
                        duration_ms=round((perf_counter() - started) * 1000, 2),
                        result=result, snapshot=pipeline.result_snapshot(run.context))
            run.status = "completed"
            await run.emit("run", "completed", "Collections run completed. Review drafts before recording a dry run.",
                result=pipeline.result_snapshot(run.context))
        except asyncio.CancelledError:
            run.status = "cancelled"
            await run.emit(stage, "failed", "Run cancelled because the server is shutting down.")
            raise
        except Exception as exc:
            logging.exception("Run %s failed at %s", run.id, stage)
            run.status = "failed"
            await run.emit(stage, "failed", f"The {stage} operation failed. Correct the source or configuration and start a new run.",
                error={"type": type(exc).__name__, "detail": str(exc)[:1200]})

    async def close(self):
        for task in list(self.tasks):
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
