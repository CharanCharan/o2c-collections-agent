> Latest V2.20: [LLM draft formatting](docs/MILESTONE_V2_20.md). Explicit field limits/types and concise examples improve draft reliability; rejected output shows safe field-specific reasons. Financial checks and budgets remain. Deploy latest main; saved drafts retain earlier outcomes. No new SQL/packages/settings.

> Latest V2.19: [GitHub source link and credential review](docs/MILESTONE_V2_19.md). Adds View source on GitHub beside How it works. Repository visibility stays private; invite interviewers or choose public access for everyone. The documented source/history scan found no apparent live credentials within its stated scope; prior chat-key rotation remains your service-side check. No SQL/packages/settings changes.

> Latest V2.18: [Cloudflare Web Analytics](docs/MILESTONE_V2_18.md). Adds the supplied website analytics beacon. Merge/deploy, visit the website and check Cloudflare Web Analytics; owner visits are included. No new SQL/packages/settings or DNS changes.

> Latest V2.17: [demo inbox screenshot](docs/MILESTONE_V2_17.md). How it works has a small clickable image icon beside the real-email step, opening the supplied inbox screenshot. Existing Incognito behavior stays; no fresh-demo feature or database cleanup. Deploy and hard-refresh; no new SQL/packages/settings.

> Latest V2.16: [saved draft/mode clarity](docs/MILESTONE_V2_16.md). Removes the invoice popup Suggested test banner while retaining the scenario guide and reply suggestions. Shows template generation reasons and saved case mode; verifies fresh limited vs automatic sending. Deploy latest main and hard-refresh; no new SQL/packages/settings.

> Latest V2.15: [guided invoice scenarios](docs/MILESTONE_V2_15.md). How it works → Try a scenario opens an invoice with a suggested test. Every invoice has suggested-reply categories, including an unsent preview before a run. Opening and filling text are read-only; sending remains explicit. Deploy latest main and hard-refresh; no new SQL/packages/settings (SQL014 remains required).

> Latest V2.14: [checkpoint save-order repair](docs/MILESTONE_V2_14.md). SQL013 did not cover writes arriving before their checkpoint. Apply `sql/014_checkpoint_write_order.sql` after SQL013, deploy latest main, verify app v2.14/checkpoint revision14 ready, then retry failed invoices. Preserves existing rows and email receipts; no reset, dependencies or environment changes.

> Latest V2.13: [workflow guide and LLM labels](docs/MILESTONE_V2_13.md). How it works beside the title opens two short pages backed by editable dist/HOW_IT_WORKS.md. LLM configuration and actual per-action call evidence are labelled separately. Merge/pull and deploy; no new SQL/packages (prior SQL013 still required).

> Latest V2.12: [checkpoint storage repair](docs/MILESTONE_V2_12.md). Apply SQL013 in Supabase after pulling, restart, then retry failed invoices. Fixes a reproduced delayed-checkpoint-write foreign-key failure while preserving runs, cases, invoices and mail receipts. Health v2.12/workflow-14 must show checkpoint revision13 ready. No new packages.

> Latest V2.11: [compact live execution and invoice logs](docs/MILESTONE_V2_11.md). Small top stage strip includes actual invoice processing; owned event streams update invoice actions live. Row Log buttons open invoice history, and ready approvals work while other invoices process. Deploy latest main and verify v2.11/workflow-13; no new SQL/packages.

> Latest V2.10: [reliable portfolio results](docs/MILESTONE_V2_10.md). One invoice error no longer abandons the portfolio; reports retain explicit exceptions and retry failed invoices. Processing details are collapsed below the table. Deploy latest main and verify `/api/health` reports app_version v2.10 and ui_version workflow-12; no new SQL or packages.

> Latest V2.9: [invoice Next step and horizontal processing](docs/MILESTONE_V2_9.md). Portfolio stages run horizontally above the full-width queue; selected invoice history appears in its popup beside reply/evidence, with specific next-action controls at the top. Merge/pull and redeploy; no new SQL or packages.

> Latest V2.8: [run results and compact queue](docs/MILESTONE_V2_8.md). Run overview separates saved processing results from current approvals and customer waiting states. Compact queue header, native scrolling and clearer status/action columns. Merge/pull and manually deploy; no new SQL or packages.

> Latest V2.7: [queue-first invoice workspace](docs/MILESTONE_V2_7.md). Landing page shows a wider invoice table and collections activity. Open an invoice for side-by-side email and simulated reply, with a custom website icon. Merge/pull and deploy only; no new SQL or packages.

> Latest V2.6: [collections controls and invoice continuation](docs/MILESTONE_V2_6.md). Compact Portfolio overview and Payment promises beside Run collections; business-friendly labels and a conditional Continue invoice processing control above the selected email. Merge/pull and manual deploy only; no new SQL or packages.

> Latest V2.5: [promise follow-ups and scrolling lesson](docs/MILESTONE_V2_5.md). After merge/pull, apply SQL012 then manually deploy. Adds an explicit demo clock, resumable due checks, separate authorized follow-up emails and consistent bounded three-panel scrolling with horizontal table controls. No new packages or environment settings.

> Latest correction: daily Start quotas removed. After merge, run `sql/011_unlimited_demo_starts.sql` in Supabase and redeploy. Repeated visitor runs preserve cases/history; email/model allowances remain. Keep PUBLIC_DEMO=true. [Setup](docs/MILESTONE_V2_4.md#remove-the-daily-start-limits-sql011).

> Latest V2.4: [setup and hands-on lesson](docs/MILESTONE_V2_4.md). After merge/pull, apply SQL009 then010 in Supabase, install updated requirements and manually deploy the existing Render service. Adds15 synthetic scenarios (24total with original9), durable graph checkpoints and limited/autopilot modes. No new paid service or API key. Existing cases/history are preserved.

# Charan's O2C Collections Agent

Canonical repository: https://github.com/CharanCharan/o2c-collections-agent

Milestone 6 prepares this repository for a public interview demo on one RenderFree Python service. Visitors click Start and see real Supabase ingestion, risk scoring and draft results, with their own browser's saved history. Visitors can send a saved reminder to the server-configured project test inbox; private inbound/operator activity remains restricted. SQL-backed daily quotas bound public work. Existing controlled email/reply/follow-up tools and configurable Groq model remain.

The deployment is not live until you configure your own account/secrets and verify its actual URL. Email/LLM default off. Only synthetic AR data belongs in the public demo; claims of payment never reduce invoice balances.

The current workspace preloads source AR and saved browser cases before Start. Its landing workspace shows invoices and live execution; opening an invoice reveals email and customer replies in a side-by-side dialog. Collection status, next action and latest activity are separate. A real LangGraph case workflow supports limited approvals, bounded autopilot and automatic processing of clearly simulated website replies. Synthetic document/payment tools demonstrate disputes and reconciliation without changing source balances.

## Start here

For cloud hosting, follow [M6 deployment and webhook repair](docs/MILESTONE_6.md). Merge M6, apply SQL006, stop your local main server sharing the database, then create the one Free service. [Deploy to Render](https://render.com/deploy?repo=https://github.com/CharanCharan/o2c-collections-agent) uses render.yaml after it is merged into main. Verify Free plan and private environment values before confirming. Manual Web Service setup is also documented; do not create both.

For a fresh setup, follow [Milestone 2 database setup](docs/MILESTONE_2.md): run the two SQL scripts in your own Supabase project, create a private local `.env`, install dependencies, then start Python. The database password is not used by this app. The backend uses a project URL and server API secret.

If M4 is merged, follow [Milestone 5 setup and lesson](docs/MILESTONE_5.md): merge/pull M5, run SQL005 (SQL004 first if needed), configure Resend Free privately and use callback-only forwarding for real replies. Keep existing `.env` values. No new runtime dependency or domain purchase. You can leave the LLM disabled for this milestone.

[M4 lesson](docs/MILESTONE_4.md) covers Groq setup; its live/learning checks are deferred at Charan's request until after M5.
For the nine-invoice demo, `sql/003_seed_pre_due.sql` adds three future examples after SQL001/002. No schema change or new database key is needed for those examples. [M3 lesson](docs/MILESTONE_3.md) covers the two models and retraining.

After database and environment setup, from the repository root in Windows / Anaconda:

```powershell
# Only create the environment if it does not already exist:
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000
```

Open http://localhost:8000 . Health: http://localhost:8000/api/health . API explorer: http://localhost:8000/docs . Direct environment Python avoids PowerShell activation-policy issues; no extra Python installation is needed. On macOS/Linux use `.venv/bin/python` instead.

Historical nine-invoice baseline before SQL010: nine invoices, USD 431,700 open AR, USD 372,200 past due, USD 308,000 eligible recovery exposure, three not-yet-due invoices (two at the scoring checkpoint), four overdue templates. Six stages / 13 events; separate prevention/recovery risk labels. Fixed snapshot date: 2026-10-17.

## Code and learning map

| File | Responsibility |
|---|---|
| `dist/index.html`, `dist/app.js` | Website, requests, SSE and saved-run controls |
| `backend/main.py` | FastAPI routes and frontend hosting |
| `backend/runner.py` | Run orchestration; persist events before displaying success |
| `backend/storage.py` | Server-only Supabase HTTPS RPC adapter |
| `backend/pipeline.py`, `backend/models.py` | Validation, Decimal calculations, rules and templates |
| `sql/001_schema.sql` | Tables, permissions and transactional functions |
| `sql/002_seed_demo.sql` | Repeatable synthetic source data |
| `backend/risk_model.py` | Shared features, JSON logistic inference and explanations |
| `ml/generate.py`, `ml/train.py` | Optional offline synthetic history, chronological training and holdout evaluation |
| `artifacts/payment_risk.json`, `pre_due_risk.json` | Separate trained recovery/prevention parameters and measured metrics |
| `sql/003_seed_pre_due.sql` | Three additional online source examples, no schema change |
| `backend/language.py` | Structured O2C tools, guards, rendering, caps and fallback |
| `backend/llm/` | Modular Groq/OpenAI adapters, environment settings and separate keys |
| `sql/004_language_review.sql` | Atomic backend-only sample-reply review persistence |
| `fixtures/replies.json` | Disclosed synthetic reply cases, not received email |
| `backend/mail/`, `sql/005_email_loop.sql` | Owner-approved send intents, signed callbacks, reply review, durable cap and follow-up tasks |
| `backend/webhook_gateway.py` | Optional local callback-only forwarding helper; main app stays private |
| `backend/public_demo.py`, `sql/006_public_demo.sql` | Signed sessions, run ownership, private email filtering and durable quotas |
| `render.yaml`, `scripts/check_deployment.py` | Free cloud configuration and read-only live verification |
| `backend/workflow/`, `sql/009_case_workflow.sql` | Durable LangGraph cases, approvals, tools, checkpoints and jobs |
| `sql/010_seed_scenarios.sql` | Fifteen additive synthetic invoice/document/payment scenarios |
| `dist/workflow-ui.js` | Modes, case states, action trace, outcomes and polling |
| `tests/` | Storage, API, PostgreSQL, ML export/label/policy checks |

- [Project knowledge](PROJECT_KNOWLEDGE.md): implementation contracts and continuation context.
- [Project plan](PROJECT_PLAN.md): scope, learner progress and future milestones.
- [M6 lesson](docs/MILESTONE_6.md): publish under your account, repair webhook URL and verify visitor/owner flows.
- [M5 lesson](docs/MILESTONE_5.md): controlled live email/replies, owner setup and follow-up tasks.
- [M4 lesson](docs/MILESTONE_4.md): Groq Free setup, modular providers, invoice checks, draft labels and synthetic reply review.
- [M3 lesson](docs/MILESTONE_3.md): run, understand predictions, edit inputs and optionally retrain.
- [Model card](ml/MODEL_CARD.md): data provenance, target, measured results and limitations.
- [M2 checklist](docs/MILESTONE_2_PLAN.md): prior milestone, learner-complete.
- [M1 guide](docs/MILESTONE_1.md): historical first-backend lesson.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

The SQL integration tests use optional Node.js and an isolated PostgreSQL/WASM engine. To run them too, install Node.js then run `npm install --prefix tests` before pytest. Without that dependency SQL tests skip explicitly. The two training/export parity tests also require optional `requirements-ml.txt`; otherwise they skip. Node is not needed to run the application. Tests do not access your live Supabase, email or model accounts; paid API settings are overridden off and provider responses are mocked.

## Optional offline training

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-ml.txt
.\.venv\Scripts\python.exe -m ml.generate_pre_due
.\.venv\Scripts\python.exe -m ml.train --stage pre_due
.\.venv\Scripts\python.exe -m ml.generate
.\.venv\Scripts\python.exe -m ml.train
```

This generates two independent sets of 4,000 synthetic records each, fits on past data and evaluates later dates. Dataset/manifest are ignored and reproducible; artifact is versioned. Stop/restart Python around artifact replacement. Full instructions and measured metrics are in the M3 lesson. No new paid service is involved.

## Boundaries and shared workflow

Run one backend process per database, with no multiple Uvicorn workers. Restart marks abandoned active runs interrupted; completed history stays saved. This is persistence, not a durable job queue. Saved-run controls list the latest 20; older runs remain in the database.

This POC has browser-session isolation and owner tools in public mode; it does not provide enterprise authentication. Use only synthetic data. Visitor data editing is deferred until the current case workflow is accepted. Supabase Free can pause after inactivity; check/resume before demos. No paid upgrade is required by this milestone.

Use only this repository. Push your edits before the next milestone. Review/merge milestone PRs, then pull `main` locally. Keep `.env` private and ignored; never paste secrets into chat, browser code or Git.

## API configuration and cost boundary

Default provider/model: Groq / `openai/gpt-oss-20b`. Enable only with your own Groq **Free** account and private `GROQ_API_KEY`. `.env.example` exposes provider, model, free-only guard, timeout and call/output limits; restart after edits. No automatic provider fallback or key sharing. `LLM_FREE_ONLY=true` blocks OpenAI and unreviewed models, but cannot verify the Groq account's billing tier. Confirm Free in its console; do not upgrade for this POC.

Defaults: four draft attempts/run, twenty total attempts/process, 2048 max completion tokens, thirty-second timeout, no retry. Quota/errors produce labelled templates/manual review. Local caps reset on restart; public daily/visitor controls are provided by M6 SQL006. [M4 lesson](docs/MILESTONE_4.md) explains configuration, adapter extension and explicit optional paid compatibility. No live provider/account verification by assistant.

## Controlled email boundary

EMAIL_ENABLED defaults false. Resend key/signing secret stay private. The website Send email action (or bounded autopilot authorization) sends the saved draft only to EMAIL_TEST_RECIPIENT, your own Resend signup inbox. EMAIL_OWNER_TOKEN is optional for legacy private administration; it is not required by the website. SQL persists exact payload, stable idempotency and ten new send reservations per UTC day; errors remain uncertain and require manual reconciliation/retry. Accepted differs from delivered. Real inbound replies need signed callback plus expected sender/thread checks and private human review. Clearly labelled website replies are simulated and automatically processed by the case graph. Tasks/payment claims do not mutate invoice balances. Use only synthetic demo content.

[M5 guide](docs/MILESTONE_5.md) preserves the local callback-forwarding lesson. For hosting, use [M6](docs/MILESTONE_6.md): the main cloud app handles callbacks directly, protects private email/history and enforces durable LLM quotas. Keep unrestricted local mode private.

## Public deployment boundary

PUBLIC_DEMO requires a32+character DEMO_SESSION_SECRET. An optional legacy EMAIL_OWNER_TOKEN, if configured, must be distinct and32+characters. Render refuses unrestricted local mode. Secure signed browser cookies isolate run history; owner login unlocks private email/history. After SQL011, Starts have no daily browser/global quota. Model SQL caps remain40global/8pervisitor attempts per UTC day. Cookie clearing is not person-level authentication; global caps still apply. All email shares10new reservations/day. No paid-provider fallback. Free Render sleeps, so manually wake/check before interviews; a stable URL is not always-on hosting. Supabase remains durable storage. Monitor hosting billing/allowances and provider Free status.

GET `/api/webhooks/resend` reports reachability; actual callback requires a signature. Update Resend to the real cloud URL, use its endpoint signing secret, then Replay failed events instead of resending the email. See M6 for precise diagnosis/acceptance and provider limitations.
