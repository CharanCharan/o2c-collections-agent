# Milestone 1 — website connected to Python

## Objective and boundaries

Start triggers real invoice processing in Python. Five operations emit start and
success/failure events; the browser displays those results. Six records process
quickly, so the run may finish almost immediately. There are no artificial work
delays. Inspect the retained outputs rather than interpreting animation as proof.

The data is synthetic. Urgency uses rules, drafts use templates, and approvals
are dry runs. ML, LLMs, ERP/API ingestion, email and Postgres remain later milestones.

## 1. Get the reviewed code

After merging the M1 pull request on GitHub, run from your existing project folder:

```powershell
git status
git switch main
git pull --ff-only origin main
git rev-parse --short HEAD
```

If status shows your own edits, preserve and commit them first. If pull reports
a conflict or divergent history, share the output before continuing. Use only
https://github.com/CharanCharan/o2c-collections-agent for this project.

## 2. Start one server

Stop the original `python -m http.server` terminal with Ctrl+C. Also stop any
earlier Uvicorn process. From the folder containing backend, dist and requirements:

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000
```

This environment uses your existing Anaconda Python. Directly calling its Python
avoids PowerShell activation scripts. Pinned dependencies support Python 3.13;
the automated delivery checks ran on Python 3.12.14. Your own run is still required
before the milestone is marked learner-complete.

- http://localhost:8000 — website.
- http://localhost:8000/api/health — confirms the service responds.
- http://localhost:8000/docs — interactive API explorer.

The health endpoint alone does not prove invoice processing; verify the next step.

## 3. Run and inspect

Click Start collections run. The empty page fills from actual Python results.

| Output | Expected |
|---|---|
| As-of date | 2026-10-17 |
| Invoices | 6 |
| Open receivables | USD 372,200.00 |
| Past due | USD 372,200.00 |
| At least 90 days overdue | USD 0.00 |
| Eligible exposure | USD 308,000.00 |
| Eligible invoices | 5 |
| High urgency, eligible | 1 |
| Reminder templates | 4 |
| Monitor without reminder | Atlas Office Systems |
| Paused dispute | Solace Energy Partners |
| First eligible account | Cedar & Finch Retail |
| Events before approval | 11 |

All sample balances happen to be overdue at the fixed snapshot date. This is a
property of these records, not a claim about a real receivables portfolio.

Select Cedar & Finch. Read its score explanation and draft, then approve the dry
run. The backend should record one interaction, bringing the event count to 12.
No email is sent. Repeating the HTTP approval request for that invoice in that run
returns 'already recorded'. The dispute has no draft and cannot be approved.
Atlas is eligible for review but below the reminder threshold, so it is monitored.

## 4. Follow one request through the code

| Step | Code | Responsibility |
|---|---|---|
| Click | `dist/app.js`, `startRun()` | POST /api/runs |
| Create | `backend/main.py`, `start_run()` | New UUID and stream URL |
| Orchestrate | `backend/runner.py`, `execute()` | Five operations in order |
| Calculate | `backend/pipeline.py` | Ingest, validate, assess, prioritize, draft |
| Record | `backend/runner.py`, `emit()` | Event ID, time, stage, output and duration |
| Stream | `backend/main.py`, `events()` | SSE updates to browser |
| Render | `dist/app.js`, `handleEvent()` | Metrics, queue, progress and detail |

SSE is one-way server-to-browser communication. Start and approval use ordinary
POST requests. Browser EventSource receives events. No WebSocket or second server
is required. Each stage completion is recorded after the operation succeeds.

Events remain available when subscription starts after processing. Reconnects can
use Last-Event-ID to resume; the browser deduplicates event IDs. Runs have separate
inputs/results/events, so approving in one run does not affect another run.

Click Inspect output under a stage event to see its structured result. Inspect
run JSON in the footer opens the full record, including the source SHA-256 hash.

## 5. Understand the business rules

Collection urgency is a score out of 100:

- Aging: min(days overdue, 90) / 90 × 40 points.
- Payment history: late payments / previous invoices × 40 points.
- Broken promise: 20 points if any broken promise is recorded.

Round the sum to an integer. High is at least 65; medium is at least 35. Customers
with no history get zero history points, with limited evidence disclosed. These
are illustrative policy weights, not learned coefficients or predicted probabilities.

Eligible accounts are ranked by open balance × urgency / 100. This is a priority
index, not a recoverable-cash forecast. Active disputes, zero balances and invoices
not yet overdue are ineligible. Eligible scores of at least 35 get template drafts.
M3 adds a separately evaluated payment-risk model; M4 adds language generation.

Python Decimal handles monetary calculations. JSON amounts are decimal strings;
JavaScript formats them for display. Only USD is supported in M1 to prevent mixed
currency totals. Aging uses the explicit as-of date in the input file.

## 6. Your hands-on exercise

1. Open data/invoices.json.
2. Change Northstar's amount from 86400.00 to 96400.00, preserving JSON quotes.
3. Save and start another run. A JSON edit is read on the next run without restart.
4. Open receivables should become USD 382,200.00; eligible exposure USD 318,000.00.
5. Northstar's template must show the updated amount.
6. Restore the amount, rerun and confirm original totals return.

Optional failure exercise: make an amount negative and run again. Validation must
fail without a run-completed claim or usable reminders. Restore the valid input
before committing. This demonstrates actual data-dependent processing.

## 7. Checks and learner acceptance

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

Checks cover calculated totals, input changes, invalid-data failure, stage order,
immutable historical results, event replay, duplicate-approval protection, disputes,
run isolation, and loss of in-memory state after restart.

Report your normal run and amount-edit result. We will then mark M1 learner-verified
in PROJECT_PLAN.md. Review git diff, commit and push any edits before the next
milestone, so the assistant and your local app use the same code.

## Troubleshooting and limits

- Restarting the server clears runs and approvals. Python edits with --reload
  restart it. Persistent storage is M2.
- Closing the browser does not cancel the run. Oldest completed runs expire when
  the 100-run in-memory limit is reached; at most five runs may be active at once.
- A stale run ID returns 404. Start a new run after restarting Python.
- Port 8000 busy: stop your old server with Ctrl+C.
- Cannot import backend.main: start from the repository root.
- Backend unavailable: use Uvicorn; python -m http.server cannot execute the API.
- Run IDs and in-process limits are local POC controls, not production authentication
  or durable jobs. Hosting and access/usage hardening remain in M6.
