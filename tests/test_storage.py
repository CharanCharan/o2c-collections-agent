import asyncio

import httpx
import pytest

from backend.storage import StorageError, StoreRequestError, SupabaseStore
from backend.main import create_app
from fastapi.testclient import TestClient


def test_missing_configuration_is_actionable(monkeypatch):
    def missing(root):
        raise StorageError("Configure Supabase in .env")
    monkeypatch.setattr(SupabaseStore,"from_env",missing)
    with TestClient(create_app()) as c:
        assert c.get("/").status_code == 200
        assert c.get("/api/health").status_code == 503
        assert c.post("/api/runs").status_code == 503


def test_secret_header_and_error_sanitization():
    async def check():
        def handler(request):
            assert request.headers["apikey"] == "sb_secret_fake"
            assert "Authorization" not in request.headers
            return httpx.Response(401,json={"message":"Never echo provider details or sb_secret_fake"})
        store = SupabaseStore("https://demo.supabase.co","sb_secret_fake",transport=httpx.MockTransport(handler))
        try:
            with pytest.raises(StorageError) as error:
                await store.health()
            assert "sb_secret_fake" not in str(error.value)
        finally:
            await store.close()
    asyncio.run(check())


def test_invalid_destination_or_publishable_key_rejected():
    with pytest.raises(StorageError):
        SupabaseStore("http://example.com","sb_secret_fake")
    with pytest.raises(StorageError):
        SupabaseStore("https://demo.supabase.co","sb_publishable_fake")


def test_business_404_is_not_schema_missing():
    async def check():
        store = SupabaseStore("https://demo.supabase.co","sb_secret_fake",
            transport=httpx.MockTransport(lambda request:httpx.Response(404,json={"code":"PT404"})))
        try:
            with pytest.raises(StoreRequestError) as error:
                await store.approve("unknown","unknown")
            assert error.value.status == 404
        finally:
            await store.close()
    asyncio.run(check())
