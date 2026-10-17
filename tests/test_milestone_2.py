import copy
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.main import create_app
from backend import pipeline


def decode_events(text):
    import json
    return [json.loads(line[6:]) for line in text.splitlines() if line.startswith("data: ")]


def finish(client):
    start = client.post("/api/runs")
    assert start.status_code == 202, start.text
    rid = start.json()["run_id"]
    stream = client.get(f"/api/runs/{rid}/events")
    assert stream.status_code == 200, stream.text
    run = client.get(f"/api/runs/{rid}").json()
    return run, decode_events(stream.text)


def test_source_totals_events_and_immutable_history(store_factory):
    with TestClient(create_app(store_factory())) as c:
        assert c.get("/api/health").json()["storage"] == "supabase_postgres"
        assert c.get("/").status_code == 200
        assert c.get("/assets/app.js").status_code == 200
        run, events = finish(c)
    assert run["status"] == "completed", run
    assert len(events) == 11
    assert [e["event_id"] for e in events] == list(range(1, 12))
    s = run["result"]["summary"]
    assert s["invoice_count"] == 6
    assert s["open_balance"] == "372200.00"
    assert s["eligible_balance"] == "308000.00"
    assert s["draft_count"] == 4
    assert s["high_urgency_count"] == 1
    assert run["input_snapshot"]["invoices"]
    early = next(e for e in events if e["stage"] == "validate" and e["status"] == "completed")
    assert all(r["score"] is None for r in early["snapshot"]["invoices"])


def test_owner_database_edit_changes_new_run_not_saved_history(store_factory, database):
    with TestClient(create_app(store_factory())) as c:
        first, _ = finish(c)
        database.sql("update ca_invoices set amount=96400 where id='INV-10482'")
        second, _ = finish(c)
        old = c.get(f"/api/runs/{first['run_id']}").json()
    assert second["result"]["summary"]["open_balance"] == "382200.00"
    assert second["result"]["summary"]["eligible_balance"] == "318000.00"
    assert old["result"] == first["result"]
    assert second["result"]["source_sha256"] != first["result"]["source_sha256"]


def test_restart_preserves_history_and_idempotent_approval(store_factory):
    with TestClient(create_app(store_factory())) as c:
        run, _ = finish(c)
        rid = run["run_id"]
        route = f"/api/runs/{rid}/invoices/INV-10287/dry-run"
        assert c.post(route).json()["recorded"] is True
    # New Python application and HTTP client; only the test database is shared.
    with TestClient(create_app(store_factory())) as fresh:
        saved = fresh.get(f"/api/runs/{rid}").json()
        assert len(saved["events"]) == 12
        assert len(saved["interactions"]) == 1
        assert saved["interactions"][0]["email_sent"] is False
        assert fresh.post(route).json()["recorded"] is False
        assert len(fresh.get(f"/api/runs/{rid}").json()["events"]) == 12
        assert fresh.get("/api/runs").json()["runs"][0]["run_id"] == rid


def test_disputes_monitor_and_cross_run_isolation(store_factory):
    with TestClient(create_app(store_factory())) as c:
        a, _ = finish(c)
        b, _ = finish(c)
        rid = a["run_id"]
        assert c.post(f"/api/runs/{rid}/invoices/INV-10317/dry-run").status_code == 409
        assert c.post(f"/api/runs/{rid}/invoices/INV-10405/dry-run").status_code == 409
        assert c.post(f"/api/runs/{rid}/invoices/INV-10287/dry-run").json()["recorded"] is True
        other = c.get(f"/api/runs/{b['run_id']}").json()
        assert not other["interactions"]
        assert not any(r["contacted"] for r in other["result"]["invoices"])


def test_persisted_sse_resume_and_unknown_run(store_factory):
    with TestClient(create_app(store_factory())) as c:
        run, _ = finish(c)
    with TestClient(create_app(store_factory())) as fresh:
        stream = fresh.get(f"/api/runs/{run['run_id']}/events", headers={"Last-Event-ID": "8"})
        assert [e["event_id"] for e in decode_events(stream.text)] == [9, 10, 11]
        assert fresh.get(f"/api/runs/{uuid4()}").status_code == 404
        assert fresh.get(f"/api/runs/{run['run_id']}/events", headers={"Last-Event-ID": "bad"}).status_code == 400


def test_abandoned_work_is_interrupted_after_startup(store_factory, database):
    rid, process = str(uuid4()), str(uuid4())
    result = database.call(command="rpc", name="ca_create_run", params={
        "p_run_id":rid,"p_process_id":process,"p_initial_result":pipeline.result_snapshot(pipeline.Context())})
    assert "error" not in result
    with TestClient(create_app(store_factory())) as c:
        recovered = c.get(f"/api/runs/{rid}").json()
        assert recovered["status"] == "interrupted"
        assert recovered["events"][-1]["status"] == "failed"


def test_database_outage_is_visible_and_no_fallback(store_factory):
    outage = {"enabled":False}
    with TestClient(create_app(store_factory(outage=outage))) as c:
        outage["enabled"] = True
        assert c.get("/api/health").status_code == 503
        assert c.post("/api/runs").status_code == 503


def test_invalid_database_source_fails_validation(store_factory, database):
    raw = database.call(command="rpc",name="ca_source",params={})["data"]
    raw["invoices"][0]["amount"] = "-1.00"
    with TestClient(create_app(store_factory(source_override=raw))) as c:
        run, events = finish(c)
    assert run["status"] == "failed"
    assert events[-1]["stage"] == "validate"
    assert not any(e["stage"] == "run" and e["status"] == "completed" for e in events)


def test_database_constraints_and_reseed(database):
    rejected = database.call(command="sql",sql="update ca_invoices set amount=-1 where id='INV-10482'")
    assert "error" in rejected
    rejected = database.call(command="sql",sql="update ca_invoices set late_payments=99 where id='INV-10482'")
    assert "error" in rejected
    assert database.sql("select count(*) as n from ca_invoices")[0]["n"] == 6


def test_unprivileged_roles_cannot_access_source(database):
    rejected = database.call(command="sql",sql="set role anon")
    assert "error" not in rejected
    try:
        rejected = database.call(command="sql",sql="select ca_source()")
        assert "error" in rejected
    finally:
        database.sql("reset role")
