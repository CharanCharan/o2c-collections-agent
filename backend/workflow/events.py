"""Bounded live delivery only; SQL checkpoints/case history remain authoritative."""
import asyncio
from collections import defaultdict
from contextvars import ContextVar

active_run=ContextVar('collection_execution_run',default=None)

class ExecutionEvents:
    def __init__(self):self.listeners=defaultdict(set)
    def subscribe(self,run_id):
        queue=asyncio.Queue(maxsize=128);self.listeners[run_id].add(queue);return queue
    def unsubscribe(self,run_id,queue):
        self.listeners[run_id].discard(queue)
        if not self.listeners[run_id]:self.listeners.pop(run_id,None)
    def publish(self,run_id,payload):
        for queue in tuple(self.listeners.get(run_id,())):
            if queue.full():queue.get_nowait()  # Latest snapshot catches up; not business storage.
            queue.put_nowait(payload)
