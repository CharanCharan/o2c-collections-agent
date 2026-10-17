# O2C Collections Agent — Project Plan

Last updated: 2026-10-17
Owner: Charan
Current checkpoint: M0 — UI prototype exported; learner has not yet confirmed running it locally.

## Goal and scope

Build a publicly shareable collections-agent POC. A visitor clicks Start and sees genuine backend actions and results appear in plain language. Charan must be able to explain, run, edit, and deploy the code himself.

Preserve this workflow: ingest AR data → validate and identify exceptions → score payment risk → prioritize accounts → draft reminders → approve/send controlled emails → capture replies → record promises and follow-ups → show audit history.

This is a hands-on learning project. Explain one change at a time, let Charan perform the work, and inspect his result before advancing. Do not substitute a large unexplained code dump for the lesson.

## Current implementation — be precise

- The working website is a browser-only prototype in `dist/index.html`.
- HTML, CSS, JavaScript, and sample data are embedded in that one file.
- There are six actual sample invoice objects, not 128 loaded records.
- Headline totals, 128-invoice messages, draft counts, and forecast figures are illustrative UI content; they are not derived from a real data source.
- Payment-risk values are hard-coded. They are not predictions from a trained model.
- Queue sorting is executed in JavaScript using a simple balance/risk/aging formula.
- The run uses `setTimeout` to display prewritten stage events.
- Reminder wording is a fixed template, not LLM-generated text.
- Email actions and replies are simulations. No email is sent or received.
- State exists only in browser memory and is lost on reload. There is no database or backend.
- The current site is publicly accessible at https://collections-agent-live-demo.blithecomet33.chatgpt.site/ .

Do not present this starting point as a finished agent. Replace each simulated component with real execution and label remaining simulations.

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

### M0 — Own and understand the existing code [CURRENT]

1. Download and extract the source bundle.
2. Open the folder in VS Code.
3. Serve `dist` locally using Python.
4. Run the demo; inspect `baseInvoices`, `run()`, `renderQueue()`, and `addEvent()`.
5. Change a visible heading; reload; explain what changed.
6. Create a repository in Charan's own GitHub account and commit the source.

Acceptance: Charan can start the site locally, edit it, and identify which parts are simulated.

### M1 — Execute a real backend run

Build a small FastAPI service. First serve the existing frontend and a health endpoint. Then add a run endpoint and an event stream. Replace timer-driven claims with backend-produced results calculated from the six sample invoices. Calculate displayed totals and counts from the data.

Proposed API:

- `GET /api/health`: service status.
- `POST /api/runs`: create a run and return a unique run ID.
- `GET /api/runs/{run_id}/events`: SSE event stream for that run.
- `GET /api/runs/{run_id}`: run status and results.

Events should contain `run_id`, `event_id`, `stage`, `status`, `message`, `timestamp`, and structured `result` or `error`. A displayed step is complete only after the operation succeeds. Each visitor's run is isolated. On failure show a clear failed stage rather than continuing as though it succeeded.

Acceptance: Browser Start triggers Python execution. Changing the input changes actual results. No invented load counts or timer-only completion claims.

### M2 — Ingest and persist AR data

Create customers, invoices, payment applications, runs, run_events, interactions, disputes, and promises_to_pay tables. Start with a documented hosted synthetic AR source and CSV import, then one REST connector. Capture source, import timestamp, and validation failures. Store amounts accurately; calculate outstanding balance from invoice amounts, credits, and applied payments. Fix a clear as-of date for aging. Avoid mixing currencies in totals.

Public data may be an ingestion example, but verify business direction, fields, and license. A government paying supplier invoices is AP data and must not be presented as commercial customer AR. Any synthetic records and labels must stay visibly identified.

Acceptance: Records and event history survive refresh/restart; malformed or duplicate input is handled; each run can be replayed from recorded inputs and outputs.

### M3 — Train and evaluate payment risk

Define target and prediction time first. Recommended initial target: probability that an invoice remains unpaid 30 days after its due date, measured at a documented scoring date. Compare a basic baseline with a small interpretable classifier. Build features only from information available at prediction time. Split by time; do not leak future payment dates into features. Evaluate ranking quality and calibration; record model version and dataset provenance.

Separate risk prediction from collection priority. Priority also reflects exposure, aging, disputes, recent contact, and promises to pay. Synthetic-data accuracy demonstrates pipeline behavior, not proven performance on real customer receivables.

Acceptance: Scores come from a saved trained artifact; documented holdout results and limitations; reasons and model version visible in the run history.

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

At the start of a continuation: read this file, inspect current code, and identify the last learner-confirmed checkpoint. State one learning objective. Explain inputs, code change, execution, and expected output. Ask Charan to run that step, inspect his result, then update the progress log. Do not assume he installed tools or completed a prior lesson.

## Progress log

| Date | Checkpoint | Evidence / next action |
|---|---|---|
| 2026-10-17 | UI prototype live | Browser run and dry-run approval checked; no real integrations |
| 2026-10-17 | Portable source and guide prepared | Next: Charan runs `dist` locally and edits the heading |
