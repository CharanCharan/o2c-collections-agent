"""Contract tests: calculated outputs, honest failures, event replay and isolation."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.main import ROOT, create_app


def sample():
    return json.loads((ROOT / "data" / "invoices.json").read_text())


def source_file(tmp_path, data):
    path = tmp_path / "invoices.json"
    path.write_text(json.dumps(data))
    return path


def decode_events(text):
    return [json.loads(line[6:]) for line in text.splitlines() if line.startswith("data: ")]


def finish(client):
    start = client.post("/api/runs")
    assert start.status_code == 202
    run_id = start.json()["run_id"]
    stream = client.get(f"/api/runs/{run_id}/events")
    assert stream.status_code == 200
    assert stream.headers["content-type"].startswith("text/event-stream")
    return client.get(f"/api/runs/{run_id}").json(), decode_events(stream.text)


def test_sample_totals_queue_and_event_order():
    with TestClient(create_app()) as client:
        assert client.get("/api/health").json()["status"] == "ok"
        assert client.get("/").status_code == 200
        assert client.get("/assets/app.js").status_code == 200
        run, events = finish(client)
    assert run["status"] == "completed"
    summary = run["result"]["summary"]
    assert summary["invoice_count"] == 6
    assert summary["open_balance"] == "372200.00"
    assert summary["past_due_balance"] == "372200.00"
    assert summary["eligible_balance"] == "308000.00"
    assert summary["disputed_count"] == 1
    assert summary["draft_count"] == 4
    assert summary["high_urgency_count"] == 1
    assert run["result"]["invoices"][0]["id"] == "INV-10287"
    assert len(events) == 11  # Five start/success pairs and one terminal event.
    assert [e["event_id"] for e in events] == list(range(1, 12))
    assert all(e["run_id"] == run["run_id"] for e in events)
    assert [e["stage"] for e in events if e["status"] == "completed"] == [
        "ingest", "validate", "assess", "prioritize", "draft", "run"
    ]
    # Early event snapshots must not be mutated by later scoring/drafting.
    validated = next(e for e in events if e["stage"] == "validate" and e["status"] == "completed")
    assert all(row["score"] is None and row["draft"] is None for row in validated["snapshot"]["invoices"])
    assert len(run["result"]["source_sha256"]) == 64


def test_changed_input_recomputes_money_aging_and_eligibility(tmp_path):
    data = sample()
    data["invoices"] = data["invoices"][:2]
    data["invoices"][0]["amount"] = "0.10"
    data["invoices"][1]["amount"] = "0.20"
    data["invoices"][0]["due"] = "2026-10-20"  # Future: excluded from collections.
    with TestClient(create_app(source_file(tmp_path, data))) as client:
        run, _ = finish(client)
    s = run["result"]["summary"]
    assert s["open_balance"] == "0.30"
    assert s["past_due_balance"] == "0.20"
    assert s["eligible_count"] == 1
    assert next(r for r in run["result"]["invoices"] if r["id"] == "INV-10482")["days"] == 0


@pytest.mark.parametrize("fault", ["duplicate", "negative_amount", "bad_date", "currency", "history"])
def test_invalid_source_fails_validation_and_never_claims_success(tmp_path, fault):
    data = sample()
    if fault == "duplicate":
        data["invoices"][1]["id"] = data["invoices"][0]["id"]
    elif fault == "negative_amount":
        data["invoices"][0]["amount"] = "-1.00"
    elif fault == "bad_date":
        data["invoices"][0]["due"] = "not-a-date"
    elif fault == "currency":
        data["currency"] = "EUR"
    else:
        data["invoices"][0]["late_payments"] = 99
    with TestClient(create_app(source_file(tmp_path, data))) as client:
        run, events = finish(client)
    assert run["status"] == "failed"
    assert events[-1]["stage"] == "validate"
    assert events[-1]["status"] == "failed"
    assert not any(e["stage"] == "run" and e["status"] == "completed" for e in events)


def test_missing_source_is_a_failed_ingest(tmp_path):
    with TestClient(create_app(tmp_path / "missing.json")) as client:
        run, events = finish(client)
    assert run["status"] == "failed"
    assert events[-1]["stage"] == "ingest"
    assert events[-1]["error"]["type"] == "FileNotFoundError"


def test_dry_run_is_idempotent_and_isolated_and_dispute_is_blocked():
    with TestClient(create_app()) as client:
        first, _ = finish(client)
        second, _ = finish(client)
        run_id = first["run_id"]
        assert run_id != second["run_id"]
        route = f"/api/runs/{run_id}/invoices/INV-10287/dry-run"
        approved = client.post(route)
        assert approved.json()["recorded"] is True
        duplicate = client.post(route)
        assert duplicate.json()["recorded"] is False
        latest = duplicate.json()["run"]
        assert len(latest["interactions"]) == 1
        assert latest["interactions"][0]["email_sent"] is False
        assert len(latest["events"]) == 12
        unrelated = client.get(f"/api/runs/{second['run_id']}").json()
        assert not unrelated["interactions"]
        assert not any(row["contacted"] for row in unrelated["result"]["invoices"])
        assert client.post(f"/api/runs/{run_id}/invoices/INV-10317/dry-run").status_code == 409
        assert client.post(f"/api/runs/{run_id}/invoices/INV-10405/dry-run").status_code == 409


def test_sse_resume_uses_event_ids_and_unknown_runs_return_404():
    with TestClient(create_app()) as client:
        run, _ = finish(client)
        response = client.get(f"/api/runs/{run['run_id']}/events", headers={"Last-Event-ID": "8"})
        assert [e["event_id"] for e in decode_events(response.text)] == [9, 10, 11]
        assert client.get("/api/runs/not-a-run").status_code == 404
        assert client.get(f"/api/runs/{run['run_id']}/events", headers={"Last-Event-ID": "bad"}).status_code == 400


def test_restart_has_no_persistence():
    with TestClient(create_app()) as client:
        run, _ = finish(client)
    with TestClient(create_app()) as fresh:
        assert fresh.get(f"/api/runs/{run['run_id']}").status_code == 404
