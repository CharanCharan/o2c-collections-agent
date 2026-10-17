---
document_role: implementation_knowledge_and_session_handoff
repository: CharanCharan/o2c-collections-agent
updated: 2026-10-17
implementation_milestone: M2
implementation_pr: 3
implementation_status: ready_for_review_not_learner_verified
learner_status: M1_normal_run_confirmed_Supabase_project_created
pending_learning_check: M2_cloud_setup_source_edit_restart_persistence
next_milestone: M3_payment_risk_model
---

# Project knowledge — continuation context

## Read first

Use only https://github.com/CharanCharan/o2c-collections-agent . Read this file, PROJECT_PLAN.md, docs/MILESTONE_2.md and current code before changing anything. Delivery is one complete runnable milestone through a branch/PR, then Charan reviews/merges/pulls/runs/edits. Do not merge for him. His edits must be pushed before the next implementation. Repository documents are explicit handoff context, not automatic memory in unrelated sessions.

Purpose: a shareable interview POC whose visitor clicks Start and sees genuine collections operations/evidence. Charan must own, edit and explain the code. Preserve O2C sequence: ingest → validate/exceptions → assess → prioritize → draft → controlled send → capture replies → promises/follow-ups → audit.

## Latest decision and learner checkpoint

- Disposable, low-cost POC. Supabase Free is hosted Postgres: one source/store choice. No paid upgrade, second DB, CSV importer, arbitrary online connector, normalized payment ledgers or extra production infrastructure in M2.
- Runtime invoice JSON has been removed. SQL seeds the same six synthetic records; each new run reads Supabase.
- Visitor data editing comes only after M0–M6. Owner editing in Supabase is allowed now.
- User confirmed Supabase project created and database password copied. Password is not needed by this app; privately configure project URL and backend API secret in ignored `.env`. No credentials received or live project connection tested by assistant.
- Windows VS Code / Anaconda Python 3.13.5; use `python`, not unavailable `py`. Git identity/auth set up. Use `.venv\Scripts\python.exe` to avoid activation-policy problems.
- M0 complete. M1 normal local run and expected results confirmed. M1 JSON amount-edit exercise was unconfirmed and is superseded by M2's database edit exercise.
- M2 code and local tests ready in PR #3; merge, cloud SQL/key setup and learner acceptance remain pending. Do not label M2 learner-complete until Charan confirms source edit and restart exercises.
- Supabase Free may pause after a week of inactivity. Check/resume manually before demos. No automatic keepalive or always-on claim.

## Repository and deployment facts

Only canonical repository above. Duplicate `CharanCharan/collections-agent` is unused; user handles deletion, not independently verified. Baseline 4777bb5; M1 PR #1 merge af9944b; knowledge PR #2 merge 692f03d. M2 branch `milestone-2-supabase`, PR #3. Inspect actual GitHub head/merge status when resuming; these documents do not imply PRs have been merged.

Original public URL https://collections-agent-live-demo.blithecomet33.chatgpt.site/ is the old static presentation prototype. Current Python/Supabase app is local, not deployed there. Public deployment is M6.

## Current implementation and honest capability labels

| Capability | M2 behavior |
|---|---|
| Source | Online Supabase tables, six synthetic invoices seeded through SQL |
| Validation/money | Pydantic consistency checks, Decimal/SQL NUMERIC, USD only |
| Urgency | Explicit policy score out of 100; no trained model |
| Reminder | Factual Python template; no LLM |
| Approval | Persisted dry-run interaction; no email provider or actual send |
| Live display | SSE of stored events, outputs, timestamps and duration |
| Persistence | Postgres runs, input/result snapshots, events and interactions |
| Restart | Saved history remains; abandoned active jobs become interrupted |
| Isolation | Separate run UUID and approval state; no production auth yet |

This is the workflow foundation. Agentic language/tool reasoning arrives in M4; do not inflate current capabilities. Action summaries/evidence can be displayed; private model chain-of-thought must not be displayed.

## Request-to-result path and code map

1. FastAPI serves `/` and `/assets/app.js`; browser checks `/api/health`.
2. Start POSTs `/api/runs`; Python persists a queued run and schedules stage execution.
3. Ingest calls `ca_source` for a consistent settings/invoice snapshot. `pipeline.ingest` hashes it; later stages validate, assess, prioritize and draft.
4. Every started/completed event is saved using `ca_append_event`. Run status/result/input changes commit with the event. Python only reports persisted success after the write succeeds.
5. SSE reads stored events after its cursor every 0.35 seconds and streams them. This poll interval is delivery plumbing, not artificial work delay. Five stage pairs plus terminal success normally give 11 events.
6. Approval invokes one atomic SQL function: verify completed/eligible/draft, create unique interaction, update result and append event. Duplicate retries return recorded false; no second interaction/event. Approval adds event 12.
7. Saved-run UI lists latest 20; opening a terminal run replays stored evidence then applies latest stored result (including approval). Older runs are retained.

| File | Contract |
|---|---|
| backend/main.py | API routes, health, SSE cursor/replay, frontend and lifespan |
| backend/runner.py | RunService initialization/recovery, stage orchestration, persist-before-success |
| backend/storage.py | Supabase HTTPS RPC, dotenv config, sanitized errors; no fallback |
| backend/pipeline.py | Context, ingest/validate/assess/prioritize/draft/result_snapshot |
| backend/models.py | Typed source schema and history constraints |
| dist/index.html / dist/app.js | UI, requests/events, safe text rendering, saved runs |
| sql/001_schema.sql | Five tables, permissions and atomic RPC functions |
| sql/002_seed_demo.sql | Upsert settings and six synthetic invoices |
| tests/test_storage.py | Config, headers, provider errors, business 404 |
| tests/test_milestone_2.py | Actual SQL-backed API/business/persistence checks |
| tests/sql_bridge.cjs / conftest.py | Isolated PGlite SQL engine behind httpx test transport |

## Database, credentials and transaction contracts

Tables: `ca_demo_settings` (one fixed-date/currency row), `ca_invoices` (source), `ca_runs` (status/process/input/result), `ca_run_events` (ordered evidence), `ca_interactions` (approval records).

Functions: `ca_health`, `ca_source`, `ca_create_run`, `ca_append_event`, `ca_get_run`, `ca_event_feed`, `ca_recent_runs`, `ca_recover_runs`, `ca_approve_dry_run`. RLS is enabled; anon/authenticated/public table/function access revoked; service_role has required access. Security-definer functions set a fixed search_path. Browser has no database key. This is a local POC trust boundary, not user authentication.

`SUPABASE_URL` must be the standard project HTTPS URL. `SUPABASE_SECRET_KEY` accepts modern `sb_secret_` via apikey header or legacy service-role JWT via apikey+Authorization. Secret/publishable types differ; password is not API key. No raw provider error body/key is exposed. `.env` ignored; blank `.env.example` checked in. dotenv never overrides existing process environment; restart after changes.

Runs/events are append-oriented: event IDs are monotonic per run, UUID event keys deduplicate retried appends, locks keep status/result/event atomic. Approval uniqueness is `(run_id, invoice_id, action)`, enforced with transaction/row lock. Inputs are saved at ingest and never changed by source edits or approval. Approval updates final result, not historical stage snapshots. SQL seed upserts source only; history remains. Do not truncate live project tables.

## Source schema, finance rules and calculations

Source object: as_of_date, currency, invoices. The pipeline only accepts USD and 1–500
invoice objects. The canonical JSON serialization limit is 1 MB. Supabase is read once per run;
the sorted, compact JSON snapshot is SHA-256 hashed. Later source edits cannot
alter the input snapshot saved with the historical run.

Each invoice contains id, customer, segment, amount, due, previous_invoices,
late_payments, broken_promises and disputed. Unknown fields are rejected. Amount
must be nonnegative with at most two decimal places. Dates must parse; history
counts must be nonnegative; late_payments cannot exceed previous_invoices; IDs
must be unique. The amount represents the outstanding balance already supplied.
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

## Reproducible sample outputs

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

## API and failure contracts

| Route | Behavior |
|---|---|
| GET /api/health | M2, supabase_postgres, actual schema/seed readiness/count; actionable 503 on config/DB problems |
| POST /api/runs | 202, UUID/status/events_url; max five active runs in SQL |
| GET /api/runs | Latest 20 run summaries, not a retention cap |
| GET /api/runs/{UUID} | Saved input/result/events/interactions; 404 if absent |
| GET /api/runs/{UUID}/events | SSE event update with persisted IDs; Last-Event-ID replay |
| POST /api/runs/{UUID}/invoices/{invoice_id}/dry-run | Atomic eligible completed-run approval; deduplicated |

Event fields: run_id, event_id, stage, status, message, timestamp; completed stages also duration_ms/result/snapshot. Money uses decimal strings. Terminal run states: completed/failed/cancelled/interrupted; active: queued/running. Malformed UUIDs are rejected by API validation. SQL business errors map to 404/409/429; connectivity/config/schema failures to sanitized 503.

A database failure never triggers JSON fallback or fabricated persisted success. Failure events are best-effort if DB itself is unavailable. SSE can send a transient `connection-error` (not saved evidence) and the UI shows lost connection. Next startup marks abandoned active jobs interrupted and adds evidence. Startup recovery is once per backend process; **one backend process per database only**, no multi-worker/independent parallel servers. This is not durable job execution or automatic resume. Completed history survives restart; runs may finish while their browser is disconnected.

## Setup, evidence and troubleshooting

Complete Windows steps and exercises: docs/MILESTONE_2.md. Merge/pull PR #3; run schema then seed in Supabase SQL Editor; copy `.env.example` to `.env` once and set URL/server secret privately; install requirements; start `.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000`. No second Python or Node installation is needed for the app.

Assistant evidence on Python 3.12.14: 14 tests passed (4 storage + 10 real SQL-backed API tests in PGlite). Tests cover changed source/new run, immutable old input, SQL constraints, anon denial, duplicate approval, restart persistence, SSE resume, interrupted recovery and DB failure. Actual Uvicorn HTTP/SSE with frontend DOM passed Start → six rows/totals/11 events → approval/12 events → saved-run reopening. Syntax checks passed. No real Supabase gateway, credentials, cloud permissions or user Python 3.13.5 verification yet. Do not present local test transport as cloud end-to-end proof.

Optional full tests need Node and `npm install --prefix tests`, then Python requirements-dev and pytest. SQL tests skip if dependency absent; storage tests remain. PGlite resets/truncates only its isolated in-memory engine, never live Supabase.

| Symptom | Action |
|---|---|
| Health 503 missing schema/seed | Run SQL001 then SQL002 in same project as URL |
| Access rejected | Check server secret/service_role, not anon/publishable/password |
| Network/paused | Check project availability and manually resume Free project |
| New .env ignored | Restart Python; check pre-existing terminal environment variables |
| Changed amount not reflected | Start new run; old saved results must remain unchanged |
| Port busy or old static page | Stop old server; start Uvicorn from repository root |
| Interrupted run after restart | Start new run; history is durable, job execution is not resumed |
| Wrong origin/unpushed edits | Check git status/remote/log; preserve and push learner edits |

## Next milestone TODO — M3, after learner M2 checks

1. Record user's cloud health, expected totals, source-edit and restart/approval results. Do not mark them done from assistant tests.
2. Confirm training target and prediction time (initial candidate: unpaid 30 days after due date at a documented scoring date). Define labels from historical outcomes.
3. Obtain/license a suitable historical dataset or clearly disclosed synthetic training generator. Six demo rows are insufficient for useful model evaluation. Keep online demo source in Supabase; no arbitrary connector expansion.
4. Build timestamp-safe features; exclude future payments/outcomes. Time-based holdout, basic baseline and interpretable classifier; measure ranking and calibration with limitations.
5. Save/version artifact and feature contract; display model version/reasons with persisted run evidence. Keep probability separate from collection priority and policy exceptions.
6. Deliver runnable M3 through PR, explain code, provide exercise. M4 LLM, M5 real controlled email/reply loop, M6 public deployment, then optional isolated visitor editor.
