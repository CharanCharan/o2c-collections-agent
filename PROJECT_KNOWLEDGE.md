---
document_role: implementation_knowledge_and_session_handoff
repository: CharanCharan/o2c-collections-agent
updated: 2026-10-17
implementation_milestone: M3
implementation_branch: milestone-3-payment-risk
implementation_status: ready_for_review_not_learner_verified
learner_status: M2_complete_cloud_source_edit_restart_confirmed
pending_learning_check: M3_run_prediction_input_edit_and_understanding
next_milestone: M4_LLM_drafting_and_policy
---

# Project knowledge — continuation context

## Read first and preserve the agreement

Canonical repository: https://github.com/CharanCharan/o2c-collections-agent . Read this file, PROJECT_PLAN.md, docs/MILESTONE_3.md and actual code before changes. Delivery: one complete runnable milestone per branch/PR; explain the code and give an exercise. Charan reviews/merges/pulls/runs/edits; do not merge for him. Preserve/push local edits before next work. Documents are handoff context, not automatic memory in other sessions. Inspect GitHub head/merge status; this document alone does not prove a PR merged.

Goal: a shareable interview O2C POC showing genuine backend actions/evidence. User must own, edit and explain it. Preserve ingest → validate/exceptions → assess/predict → prioritize → draft → controlled send → replies/promises/follow-ups → audit. No detours to extra agents, source connectors or production infrastructure without a demonstrated need/user scope change.

## Learner and environment checkpoint

- Windows, VS Code from Anaconda Prompt, Python 3.13.5. Use `python`, not unavailable `py`. Direct `.venv\Scripts\python.exe` avoids PowerShell activation issues. Git installed/configured/authenticated.
- M0 complete; M1 normal local run confirmed; M1 JSON edit exercise superseded by M2 DB edit.
- M2 PR #3 merged ea7a5fb7c3d1d2747c35182c97d4280f63f70d2f. User confirmed everything working, then confirmed source-change/immutable history and restart/approval persistence exercises on 2026-10-17. Mark M2 learner-complete based on that report; assistant has not independently accessed his Supabase.
- M3 code prepared on milestone-3-payment-risk; local tests passed, learner M3 run/input edit/understanding checks pending. Do not infer learner mastery or live-cloud M3 success from assistant tests.
- Only this repository. Unused duplicate CharanCharan/collections-agent deletion handled by user, not verified. M1 merge af9944b; knowledge PR #2 merge 692f03d. Check current refs before next work.
- Old URL https://collections-agent-live-demo.blithecomet33.chatgpt.site/ is a static presentation prototype; current Python/Supabase/ML app is local until M6. Do not silently publish via Sites.

## Decisions and limits

Throwaway low-cost POC. Supabase Free = hosted Postgres, sole online invoice source/history store. Runtime invoice JSON removed; six synthetic source records seeded by SQL. No CSV invoice importer, arbitrary source connector, normalized payment/credit ledgers, second DB or paid plan. Offline generated training CSV is separate from runtime invoice ingestion. Owner source edits in Supabase allowed; visitor editing comes only after M0–M6.

Free database can pause after inactivity; manually check/resume before demos, no paid upgrade/keepalive assumed. Secrets stay server-side in ignored .env; no secrets received in chat/code. Backend uses project URL and server API secret, not database password. One backend process per database; history is durable, jobs do not automatically resume. UUIDs do not provide production auth; public access/usage controls remain M6.

## What M3 actually does

| Capability | Current reality |
|---|---|
| Source | Fresh Supabase snapshot; synthetic source invoices |
| Validation/money | Pydantic, USD, Decimal/SQL NUMERIC |
| Urgency | Existing explicit policy score, not probability |
| ML risk | Saved scikit-learn-trained logistic model; standard-library inference |
| Target | Overdue positive balance remains at snapshot+30 days |
| Training/evaluation | Independent synthetic historical snapshots; no real customer validation |
| Prioritization | Eligible-first, balance × predicted risk |
| Explanation | Feature values, additive log-odds contributions, versions/hashes, holdout report |
| Reminders/approvals | Templates and persisted dry-run only; no LLM or actual email |
| Storage | Supabase input/results/events/interactions including prediction evidence |

Training happens offline; never per visitor Start. No LLM/tool reasoning implementation until M4. Do not describe rule scores as ML, synthetic metrics as real finance performance, or dry-run records as sent email. Show action summaries/evidence, not private model chain-of-thought.

## M3 target, feature and training contracts

The earlier candidate was unpaid at due+30. Some queue invoices are already beyond that date, so the implemented forward-looking target is unpaid at snapshot+30 for already-overdue positive balances. Snapshot date t is fixed source as_of_date, not current laptop date. Label1: full settlement not observed by t+30 after adequate observation; label0: fully settled by horizon. Synthetic generator assumes full settlement, no partial/payment/write-off ledger. A real dataset needs reconciled historical balances/outcomes.

Features v1: min(days_overdue,180); late/previous or0; min(broken_promises,4); log1p(min(balance,250000)); no-history flag. Counts assumed known at t; simplified source schema cannot independently prove historic availability. Outcome/settlement dates, future labels, customer/invoice IDs, rule score and dispute are excluded from feature vector. No-history disclosed. Ranges outside generated support flagged; caps fixed before fitting. Zero/not-overdue balances not scored; disputes may receive a prediction but are still ineligible.

`ml/generate.py` seed42 creates4,000 unique customer/invoice snapshots from Jan2024–Aug2026 with invented noisy non-settlement mechanism. No six demo-row copies or real data. CSV+hash manifest generated into ignored ml/data; script regenerates it deterministically. Source SHA256 02a0ffbc8d61a77e804bc8a16175fa30a042b56eedc4a4723e56d9f3b0f6ef36. Outcome observation maxSep30 2026.

`ml/train.py`: mature labels; fixed chronological splits: train2,887 throughNov30 2025, validation390 Jan–Mar2026, test500 May–Aug2026, embargo223 Dec2025/Apr2026. Unique customers/invoices and month gaps prevent overlaps/immature label leakage. StandardScaler and LogisticRegression fitted on training only; C(.1,1,10) selected by validation Brier, selected .1. No refit on validation/test. Baseline constant train prevalence. Test never used for selection. Generator itself encodes the signal; favorable metrics do not prove usefulness on real ERP data.

Artifact: artifacts/payment_risk.json; model ar-logreg-30d-v1-4e1935af6cbd. Trained Python3.12.14/scikit-learn1.9.1/NumPy2.5.4. Hash/version bind learned parameters and report. ModelError on missing/incompatible or stale-hash artifact; no rule-as-probability fallback. Serving uses standard-library sigmoid with exported means/scales/coefficients/intercept. No sklearn/pickle/hosted model needed at runtime. Optional requirements-ml enables generator/trainer tests. Environment/path metadata and float differences may change identity across environments; no universal bitwise-retraining guarantee.

Test metrics: ROC AUC .807976 vs .5; AP .798793 vs .466; Brier .180169 vs .249267; top20% precision .84 vs prevalence .466. Top20% rate is not overall accuracy. Brier combines probability/discrimination effects, so show calibration bins separately; e.g. middle bin .489 mean predicted vs .610 observed (n123), calibration imperfect. No real calibration or business uplift established. Export/sklearn maxprobability difference 2.22e-16 on generated splits. Full report/limitations in artifact, docs/MILESTONE_3.md and ml/MODEL_CARD.md.

Per invoice prediction saves rounded6decimal probability, scored_as_of/horizon_date, transformed features, intercept/contributions, modelversion/artifacthash, warnings. Explanation: coefficients×standardized inputs; contributions sum with intercept to logit. Relative to training means, not causal or percentage-point effects. Run model metadata additionally saves parameters/training environment/report, so later artifact changes do not rewrite historical evidence. `/api/model` describes current artifact, not necessarily an older run.

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

Priority index (M3) = open balance × probability_unpaid_30d (six-decimal probability). Money index is formatted with Decimal, eligible-first, then descending index/days, then ID. The old M2 balance×urgency index remains only in historical M2 results. Neither index is a cash forecast. Rule score is not probability. Policy urgency threshold35 still controls template eligibility/cadence independently of the model. Disputes always pause.

Policy version collections-policy-v1; template reminder-template-v1; generation_mode template_no_llm. Workflow version M3 distinguishes current snapshots from older saved runs.

## Seeded reference outputs

Snapshot2026-10-17 → horizon2026-11-16. Open/past-due372,200; eligible308,000; six invoices/fiveeligible; four drafts; onehighurgencyeligible; one dispute; zero90+.

| Customer | Rule urgency | ML risk | Risk-weighted index | Action |
|---|---:|---:|---:|---|
| Cedar & Finch | 81 | .711312 | 81,943.14 | Review draft |
| Northstar | 57 | .356656 | 30,815.08 | Review draft |
| Meridian | 46 | .258685 | 13,645.63 | Review draft |
| BluePeak | 39 | .245919 | 9,566.25 | Review draft |
| Atlas | 9 | .090755 | 1,338.64 | Monitor |
| Solace | 67 | .448718 | 28,807.70 | Dispute paused, sorted after eligible |

M2 exercises: amount Northstar86400→96400 changes total382200/eligible318000; restoring source does not rewrite saved history. M3 exercise: Cedar late_payments9→0, broken_promises2→0 lowers prediction/urgency, preserves balances, drafts4→3; restore9/2. Old result unchanged. Optional generate/train lesson; do not select a flattering seed by test performance.

## Code map and actual event sequence

| File | Contract |
|---|---|
| backend/main.py | Routes, health/model info, SSE, frontend, lifecycle |
| backend/runner.py | initialize/recover, six stages, persist-before-success |
| backend/storage.py | Server-only HTTPS RPC, config and sanitized errors; no fallback |
| backend/pipeline.py / models.py | Context, snapshot validation, finance/policy, predict and rank |
| backend/risk_model.py | Shared features, validated artifact, portable inference/explanations |
| ml/generate.py / train.py | Optional offline synthetic data, labels/splits/fit/export/evaluation |
| artifacts/payment_risk.json | Learned model and measured provenance/report |
| dist/index.html / app.js | UI, SSE, model evidence, historical-run compatibility |
| sql/001_schema.sql / 002_seed_demo.sql | Existing M2 schema/functions/seed, no M3 migration |
| tests/ | Storage, actual SQL/API regression, ML label/export/failure/policy checks |

Start POST persists queued run, then Python executes ingest→validate→assess→predict→prioritize→draft. Ingest captures consistent Supabase settings+invoices; canonical snapshot hash saved. Each stage started/completed and state/result are committed through SQL; only committed success is displayed. Six pairs plus terminal =13events, approval adds14. Prediction loads artifact once for the whole run. Stored model/parameters accompany result; historical stage snapshots are not recalculated later.

SSE polls persisted events after cursor every.35sec and pushes them; no artificial work delays. Saved dropdown lists latest20, older records retained. Opening M2 result preserves original events/ranking; UI detects absent workflow_version M3, shows five-stage flow/no ML and does not rescore. Opening M3 uses its stored model evidence, not `/api/model` current values.

## Database/API/failure contracts

Existing tables ca_demo_settings, ca_invoices, ca_runs, ca_run_events, ca_interactions. Existing RPCs ca_health/source/create_run/append_event/get_run/event_feed/recent_runs/recover_runs/approve_dry_run. RLS on, table/function access revoked for anon/authenticated/PUBLIC, service_role authorized, security-definer fixed search_path. Modern sb_secret in apikey only; legacy service-role JWT also Authorization. `.env` ignored; dotenv process environment takes precedence. Restart after .env changes.

Event IDs monotonic per run; event-key UUID dedupes retries; append status/result/input transaction is atomic. Approval locks run, requires completed/eligible/draft/non-dispute, unique run/invoice/action; duplicate recordedfalse with no extra event. Approval updates final result but not historical stage/model evidence. Seed upserts source and preserves history. Do not truncate live tables.

| Route | Contract |
|---|---|
| GET /api/health | M3, Supabase readiness/count,6stages,current model version; actionable503 on model/config/storage failure |
| GET /api/model | Current artifact card incl parameters, source/identity/metrics/limitations |
| POST /api/runs | 202 UUID/status/events_url; max5active in SQL |
| GET /api/runs | Latest20 summaries, no history deletion |
| GET /api/runs/{UUID} | Saved input/result/model/events/interactions |
| GET /api/runs/{UUID}/events | update SSE with IDs; Last-Event-ID replay |
| POST /api/runs/{UUID}/invoices/{id}/dry-run | Atomic eligible approval, no email |

Financial amounts/index Decimal strings. Prediction numericfloat rounded6decimal; ranking converts it to Decimal. Terminal states completed/failed/cancelled/interrupted; queued/running active. BadUUID rejected; absent404; SQLbusiness409/429; config/connectivity/schema/model503. Mid-run model failure records predict failed and does not continue ranking/drafting. A DB outage may prevent its own failure persistence; never fabricated success. SSE connection-error is transient, not invented saved evidence. Next startup marks prior-process active work interrupted; singlebackend/process perDB, no multiserver or job auto-resume. Completed history survives restart and browser disconnect.

## Execution and verification evidence

Current hands-on commands/explanation: docs/MILESTONE_3.md. After merge/pull, reuse.env, pip install requirements, start `.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000`. No M3 SQL or new key. Fresh Supabase setup: docs/MILESTONE_2.md. Optional training: install requirements-ml; python -m ml.generate; python -m ml.train; stop/restart Python around replacement. Source CSV ignored/reproducible; artifact tracked. Do not request passwords or expose API secrets in source/chat/browser.

Local M3 evidence Python3.12.14:22tests passed including 14 prior storage/SQL checks, new label chronology/maturity/reproducibility, sklearn export parity, predictions/source sensitivity, separate risk ranking/policy, and truthful missing-model failures. Actual Uvicorn HTTP/SSE + DOM passed Start/sixrows/model/evidence/13events, approval14, reopen saved history. Optional Node/PGlite for SQL tests and sklearn for one training parity test; absent dependencies skip explicitly. No Node/ML package needed to serve. One upstream Starlette/httpx deprecation warning. User M3 cloud/Python3.13.5 check remains pending; M2 cloud success is user-reported. Isolated PGlite is not a live Supabase gateway test.

Troubleshooting:503model→restore committed artifact or retrain; don't edit coefficients without valid identity. 503schema/key→sameproject URL+secret and SQL001/002. Paused→manualresume. New.env ignored→restart and inspect existing terminalvars. Old run unchanged→expected snapshots. Portbusy/staticpage→stop prior server and run Uvicorn atroot. Interruptedrun→newrun, not auto-resume. Wrongrepo/unpushededits→gitstatus/remote/log, preserve edits.

## Next TODO — M4 after learner M3 checkpoint

1. Record user's M3 run and input-change results; explain risk vs urgency vs ranking, synthetic evaluation limits, optional training. Do not mark learner complete from tests.
2. Inspect current pushed code/plan before changes; preserve user edits. Select a low-cost LLM provider/model and explain actual API billing separately from ChatGPT subscription before requiring a key.
3. Add server-side explicit drafting tool using only validated invoice facts. Structured output/schema; deterministic checks for amount/currency/invoiceID/due/asof; disputes gate before generation. No sending in M4.
4. Record provider/model/prompt/tool versions, latency, validated output and errors in persisted events. Distinguish LLM output from template fallback; malformed/inconsistent/provider-failed outputs route to visible review/fallback policy, never fake successful generation.
5. Add structured reply-classification contract with labelled fixtures; actual inbound webhook/email loop remains M5. Keep instructions from customer text untrusted.
6. Give runnable milestone PR, code walkthrough and exercise. M5 outbound allowlist/idempotency + signed inbound replies + promise/followup audit (a claim of payment is not reconciliation). M6 own-account hosting/access/caps; visitor isolated editing only afterM6.
