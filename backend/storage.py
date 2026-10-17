"""Small HTTPS adapter for the Supabase SQL functions; no JSON/memory fallback.

Only apikey carries a modern sb_secret_ key. Legacy JWT service-role keys also
need Authorization. Keys and raw provider error bodies are never logged/returned.
"""

import os
import re
from pathlib import Path
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv


class StorageError(Exception):
    pass


class StoreRequestError(StorageError):
    def __init__(self, status: int, message: str):
        self.status = status
        super().__init__(message)


class SupabaseStore:
    def __init__(self, url: str, key: str, transport=None):
        url = url.strip()
        try:
            parsed = urlparse(url)
            port = parsed.port
        except ValueError:
            raise StorageError("SUPABASE_URL is invalid. Copy the project HTTPS URL from Supabase.") from None
        if (parsed.scheme != "https" or not re.fullmatch(r"[a-z0-9]+\.supabase\.co", parsed.hostname or "")
                or parsed.username or parsed.password or parsed.query or parsed.fragment
                or parsed.path not in {"", "/"} or port not in {None, 443}):
            raise StorageError("Set SUPABASE_URL to your project's https://PROJECT_REF.supabase.co URL in .env.")
        key = key.strip()
        if not key or not (key.startswith("sb_secret_") or key.startswith("eyJ")):
            raise StorageError("Set SUPABASE_SECRET_KEY to a server-side secret key in .env; do not use a publishable/anon key.")
        headers = {"apikey": key, "User-Agent": "collections-agent-python/0.2"}
        if key.startswith("eyJ"):
            headers["Authorization"] = f"Bearer {key}"
        self.client = httpx.AsyncClient(base_url=url.rstrip("/") + "/rest/v1/", headers=headers,
                                        timeout=15, follow_redirects=False, transport=transport)

    @classmethod
    def from_env(cls, root: Path):
        load_dotenv(root / ".env", override=False)
        return cls(os.getenv("SUPABASE_URL", ""), os.getenv("SUPABASE_SECRET_KEY", ""))

    async def rpc(self, name: str, body: dict | None = None):
        try:
            response = await self.client.post("rpc/" + name, json=body or {})
        except httpx.HTTPError:
            raise StorageError("Cannot reach Supabase. Check network, project status and whether the Free project is paused.") from None
        if response.status_code in {401, 403}:
            raise StorageError("Supabase rejected access. Check the backend secret key and run sql/001_schema.sql.")
        if response.status_code >= 400:
            try:
                data = response.json()
            except ValueError:
                data = {}
            allowed = {
                "PT404": "Run, invoice or case not found in this session.",
                "PT409": "Action blocked: case needs review, or invoice has no eligible draft in a completed run.",
                "PT429": "Demo limit reached (runs, replies or case storage). Daily limits reset at UTC midnight; case/message storage limits do not.",
            }
            if data.get("code") in allowed:
                raise StoreRequestError(int(data["code"][2:]), allowed[data["code"]])
            if response.status_code == 404:
                raise StorageError("Supabase schema function missing. Run the required schema SQL (001/002 for setup; 004_language_review.sql for M4; 005_email_loop.sql for M5; 006_public_demo.sql for M6; 007_visitor_cases.sql and 008_case_email.sql for V2).")
            raise StorageError("Supabase could not complete the database operation. Check schema setup and project availability.")
        try:
            return response.json()
        except ValueError:
            raise StorageError("Unexpected Supabase response; check your project URL and database setup.") from None

    async def health(self):
        result = await self.rpc("ca_health")
        if not result or result.get("schema_version") != 2 or not result.get("seeded"):
            raise StorageError("Database is not seeded. Run sql/001_schema.sql then sql/002_seed_demo.sql.")
        return result

    async def source(self):
        result = await self.rpc("ca_source")
        if result is None:
            raise StorageError("No demo settings found. Run sql/002_seed_demo.sql.")
        return result

    async def create_run(self, run_id, process_id, initial_result):
        return await self.rpc("ca_create_run", {"p_run_id": run_id, "p_process_id": process_id,
                                               "p_initial_result": initial_result})

    async def append_event(self, run_id, process_id, event_key, event, status=None, result=None, source=None):
        return await self.rpc("ca_append_event", {"p_run_id": run_id, "p_process_id": process_id,
            "p_event_key": event_key, "p_event": event, "p_run_status": status,
            "p_result": result, "p_input": source})

    async def get_run(self, run_id):
        return await self.rpc("ca_get_run", {"p_run_id": run_id})

    async def feed(self, run_id, after=0):
        return await self.rpc("ca_event_feed", {"p_run_id": run_id, "p_after": after})

    async def recent(self):
        return await self.rpc("ca_recent_runs")

    async def approve(self, run_id, invoice_id):
        return await self.rpc("ca_approve_dry_run", {"p_run_id": run_id, "p_invoice_id": invoice_id})

    async def recover(self, process_id):
        return await self.rpc("ca_recover_runs", {"p_process_id": process_id})

    async def close(self):
        await self.client.aclose()
