# O2C Collections Agent — Project Plan

Last updated: 2026-10-17
Owner: Charan
Current checkpoint: M0 complete; M1 local execution confirmed; M2 learner-complete on 2026-10-17 (Supabase source edit, immutable results and restart/approval persistence confirmed). M3 implementation prepared on milestone-3-payment-risk; learner run/exercises pending.

## Goal and scope

Build a publicly shareable collections-agent POC. A visitor clicks Start and sees genuine backend actions and results appear in plain language. Charan must be able to explain, run, edit, and deploy the code himself.

Preserve this workflow: ingest AR data → validate and identify exceptions → score payment risk → prioritize accounts → draft reminders → approve/send controlled emails → capture replies → record promises and follow-ups → show audit history.

This is a hands-on learning project delivered one complete runnable milestone at a time, as agreed on 2026-10-17. Provide tested code through a GitHub pull request, explain its components, then let Charan run, inspect and modify it. Verify his results before marking a milestone learner-complete.

## Canonical source and delivery workflow

- Use only https://github.com/CharanCharan/o2c-collections-agent .
- Charan's uploaded baseline: 4777bb5a1d6fa5d7d4fc71507ddf980bd6f87db1.
- The duplicate CharanCharan/collections-agent is unused; Charan handles its deletion.
- Read PROJECT_KNOWLEDGE.md, this plan and current code before each milestone. Deliver a branch and pull request. Charan reviews/merges, then pulls main locally. His edits must be committed and pushed before subsequent work.
- The original hosted Sites demo is a presentation prototype; this GitHub repository and the local Python application are the working source for the real POC.

## Current implementation — M3 prepared for review

Supabase remains source/history store. Six Python stages include two saved logistic models: at due-7 predict becoming overdue; after due predict remaining unpaid another30days. Each is trained/evaluated on separate synthetic history. Persist target-specific inputs/explanations/model identity and evidence. Prevention and recovery rank separately; disputes/policy gates remain. Pre-due reviews do not yet create reminder approvals. Existing overdue rule urgency and threshold35 draft policy remain. No LLM or actual email.

M2 PR #3 merged ea7a5fb and learner-confirmed. M3 PR #4 remains the review branch; user requested adding prevention before moving to M4. SQL003 adds three pre-due source examples without schema change/history deletion. No new credentials or runtime ML packages. With full seeds:9invoices/open431700/pastdue372200/eligible recovery308000. M3 learner verification pending. docs/MILESTONE_3.md and ml/MODEL_CARD.md are current.

Local checks:29tests, actual SQL/HTTP/SSE/DOM. Prevention holdout511 AUC.738/Brier.195 versus .5/.225 baseline; recovery500 .808/.180 versus .5/.249. Synthetic tests do not prove real-world accuracy. Prior single-model22-test evidence remains historical.

## Recommended stack

| Responsibility | Choice | Reason |
|---|---|---|
| Frontend | Existing HTML, CSS, JavaScript | Preserve UI; understand browser behavior first |
| API and orchestrator | Python + FastAPI | Fits Charan's Python background; explicit tool functions and run state |
| Live progress | Server-Sent Events (SSE) | Server pushes run events to browser; ordinary POST requests handle actions |
| Durable storage | PostgreSQL on Supabase | SQL tables for invoices, runs, interactions, and promises |
| ML | scikit-learn baseline, trained offline | Separate measurable payment-risk model from language generation |
| Language tasks | LLM API, provider selected in M4 | Reminder drafts and structured reply classification |
| Email | Resend HTTPS API and verified inbound webhook | Outbound email plus reply capture |
| Source control | Charan-owned GitHub repository | Edits, history, rollback, and hosting integration under his account |
| Hosting | One Render Python web service serving UI and API | One public URL; frontend need not be hosted separately |

Keep secrets in local environment variables and host-managed secrets. Never put API keys in HTML or Git. Hosted API usage is separate from a ChatGPT subscription.

## Milestones and acceptance checks

### M0 — Own and understand the existing code [LEARNER COMPLETE]

1. Download and extract the source bundle.
2. Open the folder in VS Code.
3. Serve `dist` locally using Python.
4. Run the demo; inspect `baseInvoices`, `run()`, `renderQueue()`, and `addEvent()`.
5. Change a visible heading; reload; explain what changed.
6. Create a repository in Charan's own GitHub account and commit the source.

Acceptance: Charan can start the site locally, edit it, and identify which parts are simulated.

### M1 — Execute a real backend run [LOCAL RUN VERIFIED; INPUT EXERCISE SUPERSEDED BY M2]

Build a small FastAPI service. First serve the existing frontend and a health endpoint. Then add a run endpoint and an event stream. Replace timer-driven claims with backend-produced results calculated from the six sample invoices. Calculate displayed totals and counts from the data.

Proposed API:

- `GET /api/health`: service status.
- `POST /api/runs`: create a run and return a unique run ID.
- `GET /api/runs/{run_id}/events`: SSE event stream for that run.
- `GET /api/runs/{run_id}`: run status and results.

Events should contain `run_id`, `event_id`, `stage`, `status`, `message`, `timestamp`, and structured `result` or `error`. A displayed step is complete only after the operation succeeds. Each visitor's run is isolated. On failure show a clear failed stage rather than continuing as though it succeeded.

Acceptance: Browser Start triggers Python execution. Changing the input changes actual results. No invented load counts or timer-only completion claims.

### M2 — Supabase data source and persistence [LEARNER COMPLETE]

Use Supabase Free, a hosted Postgres database, as both the invoice data source and durable store. Replace runtime invoice JSON reads with Supabase reads; seed the same synthetic rows once using SQL. Keep a simple five-table design for settings, invoices, runs, events and interactions. M1's amount remains the outstanding balance; normalized payment/credit ledgers are deferred unless a later feature needs them.

The revised checklist is docs/MILESTONE_2_PLAN.md. CSV import and a second hosted-source connector are removed from this milestone. PR #3 merged; Charan confirmed Supabase setup, expected outputs, source edits/immutable history and restart/approval persistence. docs/MILESTONE_2.md preserves the original setup lesson.

Acceptance: the Supabase rows produce the expected portfolio; owner data edits affect the next run; records/events/approvals survive Python restart; duplicate actions stay idempotent; failures are visible without JSON fallback. Historical run snapshots remain immutable.

### M3 — Train and evaluate payment risk [CODE PREPARED; LEARNER CHECKS PENDING]

Two stage-specific targets: (1) at exactly seven days before due, not fully paid by end of due date; (2) positive overdue balance remains at snapshot+30days. The second replaces the original due+30 candidate for recovery; the first adds Charan's requested prevention use case. A date outside the pre-due checkpoint is explicitly not scored, rather than backdating features. No current-invoice aging/future outcomes in pre-due features.

Separate generated histories with mature labels, chronological gaps, train-only scaling, validation C choice and untouched later-date tests. Save/version numeric artifacts, model card, parameters and evidence. Website labels targets, shows separate queues and calibration/holdout evidence; never combines probabilities or calls one independent proof of the other. Disputes/zero balances/policy gates stay enforced. M3 preventive risk is review-only; actual reminder policy/sending is later work.

Acceptance pending from learner: merge updated PR#4, pull main, run SQL003, see nine invoices/two target labels, change Harbor history and observe new risk while saved history stays unchanged. Explain timing windows, probability vs urgency, separate queue ranking and synthetic evaluation limits. Optional generator/trainer exercise for both models. Detailed steps docs/MILESTONE_3.md.

### M4 — Add language reasoning and policy

Use an LLM for reminder drafts and structured reply classification. Use SQL/Python for finance calculations and policy checks. Validate LLM output against invoice facts. Implement explicit tools and state transitions; no multi-agent expansion unless a demonstrated need arises.

Acceptance: Drafts use validated amounts and dates; disputed accounts pause; invalid output routes to review; tool inputs, outputs, versions, duration, and errors are recorded. Display action summaries and evidence, not private chain-of-thought.

### M5 — Close the email loop

Connect outbound email, record provider IDs, and verify delivery events. Capture real replies through a signed webhook; match by message/thread ID. Extract intent, promised date/amount, or dispute reason. Schedule a follow-up with an audit record. A customer saying 'paid' must not itself mark an invoice paid: require a payment source/reconciliation.

Use controlled test recipients, server-enforced recipient allowlists, approval, deduplication/idempotency, and rate limits. Public visitors must not be able to use the POC as an arbitrary email relay. Never send to contacts found in public invoice datasets.

Acceptance: Controlled reminder arrives in a real inbox; reply produces a verified event; retries do not duplicate emails or follow-ups.

### M6 — Deploy and demonstrate

Deploy the repository under Charan's own account. Keep one service for UI/API. Use an external persistent database; do not depend on an ephemeral web-server disk. Configure API secrets, per-run isolation, usage caps, and resettable demo data before public access to live actions.

Make the demo understandable without narration: purpose, Start, stage explanation, input/output evidence, updated queue, action history, and final summary. Clearly distinguish synthetic data, predictions, generated text, and actual delivery/reply events.

Acceptance: An independent visitor opens one URL, starts an isolated run, sees real events, and can inspect the final result. A failed integration shows a truthful error. Charan can redeploy a visible change from his own GitHub repository.

## Optional enhancement after M0–M6

Offer visitors a data-edit/testing playground only after the core milestones are achieved. Use an isolated/resettable portfolio per session so edits do not change shared seed data or another visitor's run. Do not add these UI controls during M2; Charan can edit the source tables through Supabase for learning.

## Cost notes — checked 2026-10-17, verify before purchasing

- Render offers free static sites and free Python web services. Free web services sleep after 15 idle minutes and can take about a minute to wake. They have ephemeral local storage. Free Render Postgres expires after 30 days, so it is not the proposed durable demo database.
- Render's entry paid web-service compute was listed at USD 7/month for 512 MB. This is a base service price, not an all-inclusive project bill.
- Supabase Free lists 500 MB database space and pauses free projects after one inactive week. A paused database can interrupt a portfolio demo even if the web server is paid.
- Resend Free lists 3,000 transactional emails/month and 100/day; received emails count toward the quota. Sender verification and domain configuration still apply.
- LLM API calls and an optional domain can cost extra. Provider subdomains remove the need to buy a website domain. A custom email sending domain may be a separate decision.
- Initial local learning can cost zero. Infrastructure can stay zero for small demos within free limits, but reliable always-on availability is a separate decision.

Official references:

- https://render.com/docs/free
- https://render.com/pricing
- https://render.com/docs/deploy-fastapi
- https://supabase.com/pricing
- https://resend.com/pricing

## Session protocol

At continuation, read PROJECT_KNOWLEDGE.md, this plan and canonical repository code; identify the last learner-confirmed checkpoint. Deliver a runnable milestone through a PR with explanation, test evidence, setup and an exercise. Verify Charan’s execution before updating learner acceptance. Implementation tests alone do not establish learner completion.

## Progress log

| Date | Checkpoint | Evidence / next action |
|---|---|---|
| 2026-10-17 | UI prototype live | Browser run and dry-run approval checked; no real integrations |
| 2026-10-17 | Portable source prepared | Source and initial learning guides exported |
| 2026-10-17 | M0 learner complete | Local run, heading edit and commit 4777bb5 confirmed |
| 2026-10-17 | Delivery workflow agreed | Runnable milestone PRs in o2c-collections-agent; Charan merges/pulls and learns locally |
| 2026-10-17 | M1 implementation merged | PR #1; implementation 05fa17b, merge af9944b; API, HTTP/SSE and DOM checks passed |
| 2026-10-17 | M1 normal local run verified | Charan reported expected results; amount-edit exercise/understanding check pending |
| 2026-10-17 | Knowledge and M2 checklist prepared | PROJECT_KNOWLEDGE.md and docs/MILESTONE_2_PLAN.md; no M2 implementation yet |
| 2026-10-17 | M2 scope simplified by user | Supabase Free source/store; runtime JSON replaced in M2; minimal schema; visitor edits deferred until after M6 |
| 2026-10-17 | M2 implementation ready in PR #3 | Supabase source/history, SQL scripts, saved-run UI; 14 local tests + HTTP/SSE/DOM passed; cloud setup and learner exercises pending |
| 2026-10-17 | M2 learner complete | User confirmed all working and both source-change/persistence checks; PR #3 merge ea7a5fb |
| 2026-10-17 | M3 implementation prepared | Synthetic-trained logistic model, saved evidence, risk ranking and lesson; 22 local tests + HTTP/SSE/DOM; learner verification pending |
| 2026-10-17 | M3 extended at user request | PR#4 now includes due-7 prevention plus overdue recovery, SQL003 examples and separate queues; 29 local checks; learner confirmation pending |
