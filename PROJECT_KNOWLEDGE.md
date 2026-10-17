---
document_role: implementation_knowledge_and_session_handoff
repository: CharanCharan/o2c-collections-agent
updated: 2026-10-17
implementation_milestone: M1
implementation_commit: af9944bf5a56ec7055372cc2f8a93ece580b3e0a
implementation_pr: 1
learner_status: normal_local_run_and_expected_outputs_confirmed
pending_learning_check: invoice_amount_edit_and_rerun
next_milestone: M2_ingestion_and_persistence
---

# Project knowledge — read this when continuing the work

## Latest scope decision — 2026-10-17

Charan specified a disposable POC with a free database and visitor data editing only at the very end. Use Supabase Free (hosted Postgres) as the runtime invoice source and persistent store in M2. Replace invoice JSON reads with database reads; seed synthetic rows through SQL. Keep one simple Supabase storage/API module. The earlier CSV importer, second hosted dataset connector and normalized finance schema are no longer M2 requirements. Current M1 behavior is unchanged until M2 is implemented. Visitors editing data is a post-M6 enhancement; owner edits in Supabase remain available for learning.

Free projects can pause after one inactive week; this does not provide a guaranteed always-on database. Check/resume before demos rather than assuming a paid plan. See docs/MILESTONE_2_PLAN.md for the revised minimal five-table design and acceptance checks.

## 1. Purpose and document hierarchy

Charan is building a publicly shareable O2C Collections Agent POC for interviews.
A visitor should start a run and understand its genuine actions, evidence, data
changes and results. Charan needs to own the source, edit it, deploy it and explain
its business and technical choices. His strengths include Python, SQL and finance
analytics; web/backend setup is being learned through this project.

Use these documents together:

| Document | Role |
|---|---|
| PROJECT_KNOWLEDGE.md | Current implementation, explanations, decisions and resume context |
| PROJECT_PLAN.md | Agreed scope, milestone acceptance and progress |
| docs/MILESTONE_1.md | Runnable M1 lesson and exercise |
| docs/MILESTONE_2_PLAN.md | Next milestone checklist; not implemented yet |
| AGENTS.md | Working rules for assistants |

Read current repository code before changing it. Code and observed execution are
the authority for behavior; update stale documents when they disagree. Preserve
the user's latest decisions. Do not infer completed work from a TODO or sample.

## 2. Shared source and working agreement

- Only working repository: https://github.com/CharanCharan/o2c-collections-agent .
- Default branch: main. Repository is private; the eventual demo can be public.
- The duplicate CharanCharan/collections-agent is unused. Charan said he would
  delete it; deletion has not been independently verified.
- Baseline initial commit: 4777bb5a1d6fa5d7d4fc71507ddf980bd6f87db1.
- M1 implementation: 05fa17ba2103e6bd82d9915b6f98e7be19d2381f.
- M1 merged via PR #1 into af9944bf5a56ec7055372cc2f8a93ece580b3e0a.
- Delivery is one complete runnable milestone per branch/PR, followed by an
  explanation and learner exercise. Charan reviews/merges and pulls locally.
- Commit/push Charan's changes before the next implementation. An assistant can
  read pushed code, not unsaved or unpushed changes on his laptop.
- Check the current main commit and local status before assuming synchronization.
  Do not overwrite user changes or use a second repository.

The earlier public Sites URL is still the original static presentation prototype:
https://collections-agent-live-demo.blithecomet33.chatgpt.site/ . M1 currently runs
locally from GitHub source. It has not been deployed to that URL. Public hosting
of the actual backend remains M6.

## 3. Learner and environment checkpoint

Confirmed by Charan:

- Windows with VS Code and Anaconda Python 3.13.5.
- Python notebooks previously worked through Jupyter.
- `py` was not available. Use `python` from the Anaconda-enabled terminal.
- Launching VS Code from Anaconda Prompt was the chosen setup approach.
- Git installed, commit identity configured, GitHub authentication completed.
- Original frontend ran locally; Charan changed the heading successfully.
- PR #1 merged. On 2026-10-17, Charan reported that M1 ran and showed the expected
  results. This confirms the normal local flow, not every optional test.

Still unconfirmed: Charan's amount-edit exercise, manual duplicate-approval or
failure exercises, and his ability to explain every backend component. Do not
claim these learning checks are complete merely because automated tests pass.

## 4. What M1 actually added

The old page contained six invoice objects, hard-coded headline totals, template
text, and setTimeout-driven messages. It had no Python application API.

M1 added a FastAPI application and moved the business work into Python. Start now
creates a real run. Python reads a JSON file, validates it, calculates urgency,
sorts eligible accounts and prepares factual template drafts. Events are emitted
after operations finish. The page renders backend outputs and calculated totals.
JavaScript timers are used only for UI notifications, not simulated work stages.

| Capability | M1 reality |
|---|---|
| Input | Six synthetic invoices from a local JSON file |
| Validation | Pydantic schemas and business consistency checks |
| Monetary arithmetic | Decimal in Python |
| Aging | Explicit fixed as-of date in the source snapshot |
| Urgency | Documented policy rules out of 100 |
| Prioritization | Eligible-first, then exposure-weighted urgency |
| Reminder | Python string template using validated invoice facts |
| Approval | Backend dry-run interaction; no email provider |
| Progress | Server-Sent Events with stage outputs and timestamps |
| Storage | Python process memory; clears on restart |
| Isolation | Separate UUID, context, events and interactions per run |
| ML / LLM / email / database | Not connected yet |

M1 is a deterministic collections workflow foundation. Agentic language/tool
reasoning will be introduced in M4. Do not describe current rules as a trained
model or current templates as LLM-generated content.

## 5. The request-to-result path

1. The browser loads `/` and `/assets/app.js` from FastAPI. app.js checks health.
2. Clicking Start calls startRun() in dist/app.js and POSTs `/api/runs`.
3. backend/main.py calls RunService.create(), returning a UUID and stream URL.
4. RunService schedules execute() independently of the browser connection.
5. execute() runs ingest, validate, assess, prioritize and draft in that order.
6. Each operation gets a started event, then a completed event with outputs and
   elapsed time. A failed operation emits failed and stops subsequent stages.
7. Browser EventSource subscribes to `/api/runs/{run_id}/events`.
8. SSE sends retained and new events. handleEvent() updates the metrics, rows,
   selected invoice, stage indicators and inspectable event timeline.
9. A final run-completed event contains the final result snapshot.
10. Approving a dry run makes a separate POST. The backend checks eligibility,
    records one interaction and adds an approval event. No email is sent.

No artificial delay is added. Six invoices process fast; the visible evidence is
the event sequence and operation output, not how long a spinner lasts.

## 6. Code map

| File / main symbols | Responsibility |
|---|---|
| backend/main.py — create_app, health, start_run, read_run, events, dry_run | HTTP routes, frontend assets, app lifecycle |
| backend/runner.py — Run, RunService, execute, emit, view | Isolated state, orchestration, locks and immutable event copies |
| backend/pipeline.py — Context, ingest, validate, assess, prioritize, draft, result_snapshot | Business operations and summary calculations |
| backend/models.py — Invoice, ReceivablesSnapshot | Input types, ranges, unique invoice IDs, consistent history |
| dist/index.html | Layout/styles, controls, metric placeholders; preserves Charan's heading |
| dist/app.js — startRun, handleEvent, applySnapshot, renderQueue, renderDetail | Requests/SSE, safe text rendering and UI state |
| data/invoices.json | Synthetic source snapshot, changed/read per new run |
| tests/test_milestone_1.py | Meaningful API/business checks |
| requirements.txt / requirements-dev.txt | Runtime and optional test dependencies |

## 7. Source schema, finance rules and calculations

Source object: as_of_date, currency, invoices. M1 only accepts USD and 1–500
invoice objects. The ingest file limit is 1 MB. It reads once per run and records
a SHA-256 hash. Later source edits cannot alter a run's input snapshot in memory.

Each invoice contains id, customer, segment, amount, due, previous_invoices,
late_payments, broken_promises and disputed. Unknown fields are rejected. Amount
must be nonnegative with at most two decimal places. Dates must parse; history
counts must be nonnegative; late_payments cannot exceed previous_invoices; IDs
must be unique. M1 amount represents the outstanding balance already supplied.
The simplified M2 keeps this outstanding-balance definition. Deriving it from invoice value, credits and applied payments is deferred until a feature requires it.

Days overdue = max(0, as_of_date minus due date). Invoices due today or later,
zero balances and disputes are ineligible for reminders.

Urgency points:

- Aging = min(days_overdue, 90) / 90 × 40.
- Prior lateness = late_payments / previous_invoices × 40.
- Broken promise = 20 if broken_promises is positive; otherwise zero.
- With no history, use zero history points and disclose limited evidence.
- Round the total using Decimal ROUND_HALF_UP to an integer.
- High: at least 65; medium: at least 35; low: below 35.

Priority index = open balance × urgency / 100. Eligible invoices sort first;
within that group, index descends, then days overdue descend, then ID breaks ties.
This index is not forecast cash recovery. A score of 81 is not an 81% probability.
Eligible invoices with scores at least 35 get template drafts; lower scores are
monitored. Disputes stay paused regardless of their score.

Policy version: collections-policy-v1. Template version: reminder-template-v1.
Draft generation mode: template_no_llm.

## 8. Reproducible sample outputs

Snapshot date: 2026-10-17. All amounts below are USD.

| Customer | Balance | Days overdue | Urgency | Priority index | Action |
|---|---:|---:|---:|---:|---|
| Cedar & Finch Retail | 115,200.00 | 56 | 81 | 93,312.00 | Review draft |
| Northstar Medical Group | 86,400.00 | 29 | 57 | 49,248.00 | Review draft |
| Meridian Components | 52,750.00 | 22 | 46 | 24,265.00 | Review draft |
| BluePeak Logistics | 38,900.00 | 15 | 39 | 15,171.00 | Review draft |
| Atlas Office Systems | 14,750.00 | 12 | 9 | 1,327.50 | Monitor |
| Solace Energy Partners | 64,200.00 | 43 | 67 | 43,014.00 | Pause — dispute |

Open AR = 372,200.00; past due = 372,200.00; 90+ = 0.00; eligible exposure =
308,000.00; five eligible invoices; one high-urgency eligible invoice; four drafts.
Solace has a large index but is sorted after eligible accounts because of dispute.

Learning exercise: Northstar 86,400.00 → 96,400.00 should produce open AR 382,200.00
and eligible exposure 318,000.00 on the next run. Restore input after checking.

## 9. API, event and state contracts

| Route | Result |
|---|---|
| GET /api/health | Status, milestone M1, storage mode, stage count |
| POST /api/runs | HTTP 202; run_id, status and events_url |
| GET /api/runs/{run_id} | Status, result, event history, interactions and storage label |
| GET /api/runs/{run_id}/events | text/event-stream; event name update |
| POST /api/runs/{run_id}/invoices/{invoice_id}/dry-run | Eligible draft approval, or no duplicate |
| GET / | Frontend |
| GET /assets/app.js | Browser logic |
| GET /docs | Interactive API explorer |

Event common fields: run_id, event_id, stage, status, message, timestamp. Completed
stage events also include duration_ms, result and a snapshot. Errors include type
and detail. The final event stage is run, status completed, with the final result.
There are normally 11 events: five started/completed pairs and one terminal event.
An approved dry run adds event 12. Financial JSON amounts are decimal strings.

SSE frames include id, event: update and JSON data. Last-Event-ID supports resume.
The browser deduplicates event IDs. Event snapshots are deep copies so later
operations do not rewrite history. SSE is one-way; user actions use POST requests.

Run states include queued, running, completed, failed and cancelled. Stage states
include started, completed and failed. Approvals are allowed only on successful
runs and eligible drafts. A run lock and contacted flag prevent duplicate approvals
within the process; M2 needs database constraints/transactions for durability.

Up to five runs can be active. At 100 retained runs the oldest terminal run is
evicted to bound memory. These controls and UUIDs do not provide production auth.
The run continues if its browser disconnects. Restart clears all history; M1 does
not have a durable job queue or automatic crash recovery.

## 10. Execution and verification evidence

Windows commands from repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000
```

Then open http://localhost:8000 . Only one application server is needed. Directly
calling the environment Python avoids PowerShell activation-policy issues.

Assistant checks: 11 automated API/business tests passed on Python 3.12.14; real
Uvicorn HTTP/SSE processing passed; frontend DOM integration using jsdom against
that server passed Start, streaming, metrics, rows and approval. JavaScript syntax
passed. These are not a claim of exhaustive visual browser QA.

Charan confirmed normal local execution and expected outputs on Python 3.13.5 on
2026-10-17. Full learner exercise/understanding remains to be checked.

## 11. Troubleshooting and continuation rules

| Symptom | Check / recovery |
|---|---|
| py is not recognized | Use Anaconda Python through python |
| git is not recognized | Git installation/PATH; reopen terminals after installation |
| Git requests name/email | Configure commit identity locally; no password belongs in source |
| GitHub push appears stuck | Complete GitHub authentication; inspect status, remote and log |
| Wrong repository | origin must be CharanCharan/o2c-collections-agent for fetch and push |
| Port 8000 busy | Stop the previous server with Ctrl+C |
| Cannot import backend.main | Run from the repository root |
| Backend unavailable | Use Uvicorn; the old static HTTP server cannot run the API |
| Validation fails | Inspect failed event output, correct JSON, start a new run |
| Run not found after code edit | --reload restarted Python; M1 state is temporary |
| Data edit does not affect current run | Start a new run; each run uses its own snapshot |

Before continuing, fetch current main and inspect the plan, knowledge document and
code. Confirm the user's last checkpoint; preserve local edits. Keep credentials
out of chat, files committed to Git and frontend code. Do not silently add paid
services or send emails. Detailed M2 tasks are in docs/MILESTONE_2_PLAN.md.
