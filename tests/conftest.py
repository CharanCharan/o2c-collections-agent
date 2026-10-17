"""Optional SQL integration uses actual Postgres functions in a local WASM engine.

No live credentials/network. Install Node test dependencies with npm install --prefix tests.
"""
import json
import shutil
import subprocess
import threading
from pathlib import Path

import httpx
import pytest

from backend.storage import SupabaseStore


ROOT = Path(__file__).resolve().parents[1]


class SQLBridge:
    def __init__(self):
        self.lock = threading.Lock()
        self.process = subprocess.Popen(["node", "tests/sql_bridge.cjs"], cwd=ROOT,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        line = self.process.stdout.readline()
        if not line or not json.loads(line).get("ready"):
            raise RuntimeError("SQL test setup failed: " + self.process.stderr.read())

    def call(self, **query):
        with self.lock:
            self.process.stdin.write(json.dumps(query) + "\n")
            self.process.stdin.flush()
            line = self.process.stdout.readline()
            if not line:
                raise RuntimeError("SQL test process stopped")
            return json.loads(line)

    def sql(self, statement, params=None):
        result = self.call(command="sql", sql=statement, params=params or [])
        if "error" in result:
            raise AssertionError(result["error"])
        return result["data"]

    def close(self):
        self.process.stdin.close()
        self.process.wait(timeout=10)


@pytest.fixture(scope="session")
def sql_bridge():
    if not shutil.which("node") or not (ROOT / "tests/node_modules/@electric-sql/pglite").exists():
        pytest.skip("Optional SQL integration: install Node, then npm install --prefix tests")
    bridge = SQLBridge()
    yield bridge
    bridge.close()


@pytest.fixture
def database(sql_bridge):
    assert sql_bridge.call(command="reset").get("data") is True
    return sql_bridge


@pytest.fixture
def store_factory(database):
    def factory(source_override=None, outage=None):
        def request_handler(request):
            if outage is not None and outage["enabled"]:
                raise httpx.ConnectError("Test database unavailable", request=request)
            name = request.url.path.rsplit("/", 1)[-1]
            if name == "ca_source" and source_override is not None:
                return httpx.Response(200, json=source_override)
            response = database.call(command="rpc", name=name, params=json.loads(request.content))
            if "error" in response:
                code = response["error"]["code"]
                status = int(code[2:]) if code.startswith("PT") else 400
                return httpx.Response(status, json=response["error"])
            if response.get("data") is None:
                return httpx.Response(200, content=b"null", headers={"Content-Type":"application/json"})
            return httpx.Response(200, json=response["data"])
        return SupabaseStore("https://testproject.supabase.co", "sb_secret_test_only",
                             transport=httpx.MockTransport(request_handler))
    return factory

@pytest.fixture(autouse=True)
def disable_paid_api_in_tests(monkeypatch):
    """Never inherit a learner's live .env opt-in/API key during pytest."""
    monkeypatch.setenv('COLLECTIONS_LLM_ENABLED', 'false')
    monkeypatch.setenv('OPENAI_API_KEY', '')
    monkeypatch.setenv('GROQ_API_KEY', '')
    monkeypatch.setenv('EMAIL_ENABLED', 'false')
    for name in ['RESEND_API_KEY','RESEND_WEBHOOK_SECRET','EMAIL_OWNER_TOKEN','EMAIL_TEST_RECIPIENT','EMAIL_RECEIVING_DOMAIN']:
        monkeypatch.setenv(name, '')
    for name, value in {'LLM_PROVIDER':'groq', 'LLM_MODEL':'openai/gpt-oss-20b',
            'LLM_FREE_ONLY':'true', 'LLM_MAX_CALLS_PER_RUN':'4',
            'LLM_MAX_CALLS_PER_PROCESS':'20', 'LLM_MAX_OUTPUT_TOKENS':'2048',
            'LLM_TIMEOUT_SECONDS':'30'}.items():
        monkeypatch.setenv(name, value)
