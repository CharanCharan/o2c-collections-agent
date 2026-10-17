# Milestone 6 — Publish the live demo and repair webhook connectivity

M5 PR#6 merged as0114b768. User reports Resend events sent/delivered/received are attempting with `client error (Connect)`, and authorizes cloud deployment. Exact existing endpoint URL/logs have not been supplied: a specific root cause is not verified. The error points to endpoint reachability; signature failures normally produce an HTTP response instead.

M6 prepares one Render Free Python web service for the website/API/webhook, reusing existing Supabase/Groq/Resend accounts. This is the deployment lesson; M4 deferred learning and M5 successful live delivery/reply checks remain pending. Assistant prepares/tests code; Charan connects/deploys in his own Render account and keeps keys private.

## 1. Merge the M6 PR and apply SQL006

Review/merge the M6 PR in https://github.com/CharanCharan/o2c-collections-agent . Preserve/commit/push local edits, then:

```powershell
git status
git switch main
git pull --ff-only origin main
```

In your existing Supabase SQL Editor, run `sql/006_public_demo.sql`. SQL004 and SQL005 must already be applied for language/email features. SQL006 adds run ownership and durable usage tables/functions without dropping history. Existing old runs have no visitor owner mapping and remain accessible only to the owner in public mode.

**Stop your local main Uvicorn server before cloud startup.** One active backend process per database remains required; a second startup can mark the other process's active jobs interrupted. Stop8001forwarding/gateway when the cloud callback is in use. The cloud directly serves the callback; do not deploy the gateway.

## 2. Create the free Render service

Open https://dashboard.render.com and sign in/connect GitHub. Choose **New → Web Service**, authorize only the canonical repository and select it. Use the **main** branch after merging. Keep the root directory blank.

| Setting | Value |
|---|---|
| Name | `o2c-collections-agent` or an available name |
| Runtime | Python3 |
| Region | Prefer the region closest to your Supabase project; Singapore is a reasonable India-demo choice |
| Branch | main |
| Build command | `pip install -r requirements.txt` |
| Start command | `uvicorn backend.main:app --host 0.0.0.0 --port $PORT --workers 1 --proxy-headers --forwarded-allow-ips '*'` |
| Instance plan | **Free**, verify before creating |
| Health check path | `/livez` |
| Auto-deploy | Off/manual while learning |

`render.yaml` encodes these settings for Render's alternative **New → Blueprint** flow. Use either Web Service or Blueprint, not both; this project needs one service. [Deploy to Render](https://render.com/deploy?repo=https://github.com/CharanCharan/o2c-collections-agent) opens that Blueprint flow after M6 is merged into main. The Blueprint generates the session secret and prompts for Supabase/owner values. Do not create Render Postgres: Supabase is already your persistent database. No Node build, Docker, persistent disk, background worker or second frontend service is needed.

The cloud runtime is pinned to Python3.12.14, the tested version; your Windows installation3.13.5 does not need changing. Render's unpinned default can differ, so set the version explicitly.

## 3. Add environment variables privately

Generate two **different** random values locally. Each command invocation generates one value:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

In Render **Environment**, enter these, without quotes around dashboard values. Do not paste secrets into chat/Git or the website. The `.env` file is ignored and is not uploaded; Render needs its own settings.

| Variable | Value |
|---|---|
| `PYTHON_VERSION` | `3.12.14` |
| `PUBLIC_DEMO` | `true` |
| `DEMO_SESSION_SECRET` | First random value; keep stable across deploys |
| `EMAIL_OWNER_TOKEN` | Second random value; reuse your existing strong M5 token if preferred |
| `SUPABASE_URL` | Your existing project HTTPS URL |
| `SUPABASE_SECRET_KEY` | Existing backend secret/API key, not database password |
| `COLLECTIONS_LLM_ENABLED` | `false` for first deployment |
| `LLM_PROVIDER` | `groq` |
| `LLM_MODEL` | `openai/gpt-oss-20b` |
| `LLM_FREE_ONLY` | `true` |
| `EMAIL_ENABLED` | `false` until configuring the cloud webhook below |

Two random secrets must differ and each be32+characters. `EMAIL_OWNER_TOKEN` is also the M6 owner-login token, even while sending is disabled. Public cloud requests fail closed if public mode/secrets are invalid. Render's `RENDER=true` environment prevents silently publishing unrestricted local mode.

Save/create the service and deploy. Render should build the pinned requirements and start Uvicorn. Wait for **Live**, then copy your actual `https://NAME.onrender.com` URL. Do not assume the example name is available.

Open these URLs:

```text
https://YOUR-ACTUAL-APP.onrender.com/livez
https://YOUR-ACTUAL-APP.onrender.com/api/health
https://YOUR-ACTUAL-APP.onrender.com/api/webhooks/resend
```

Expect alive/M6, statusok with public_demo.enabledtrue, and `{"status":"reachable",...}` respectively. `/livez` checks the process; `/api/health` checks DB/schema/models/config. If only liveness works, fix health before sharing. SQL006 missing/Supabase paused/wrong secrets can cause503 with a setup message. Never bypass public mode to resolve it.

Optional read-only check from your local project:

```powershell
.\.venv\Scripts\python.exe -m scripts.check_deployment https://YOUR-ACTUAL-APP.onrender.com
```

This checks public health, reachable webhook, a fresh visitor's empty history and private email denial; it does not create a run or spend model/email quota. The assistant cannot execute a live check until your actual cloud URL exists.

## 4. Point Resend at the cloud and replay failed callbacks

Edit your existing Resend webhook endpoint URL to:

```text
https://YOUR-ACTUAL-APP.onrender.com/api/webhooks/resend
```

Keep subscribed to the M5 events. Use this exact endpoint's signing secret; if creating a new endpoint, copy its new secret instead. Editing the existing endpoint preserves the old message list for troubleshooting/replay. Check it is enabled—Resend can disable repeatedly failing endpoints.

In Render Environment, now add the existing private settings:

```dotenv
EMAIL_ENABLED=true
RESEND_API_KEY=YOUR_PRIVATE_RESEND_KEY
RESEND_WEBHOOK_SECRET=SIGNING_SECRET_FOR_THIS_ENDPOINT
EMAIL_FROM=onboarding@resend.dev
EMAIL_TEST_RECIPIENT=YOUR_OWN_RESEND_SIGNUP_EMAIL
EMAIL_RECEIVING_DOMAIN=YOUR_ACTUAL_ACCOUNT_SUBDOMAIN.resend.app
```

Keep Resend on Free. Save/redeploy, wait for Live, then verify `/api/health` shows email.readytrue. The main cloud app handles the webhook directly; no local port, gateway or laptop uptime is involved now.

First open the webhook URL in a private browser and confirm reachable JSON. Then go to Resend **Webhooks → endpoint → failed message → Replay**, starting with one sent/delivered event. A successful200 callback should add verified delivery evidence. Replay a received event next. Do **not** resend the original collection email just to retry its webhook; callback replay and email resend are separate operations. Repeated replay is deduplicated.

How to read failures:

| Result | Meaning / next check |
|---|---|
| `client error (Connect)` / no HTTP status | Wrong/inaccessible URL, stopped tunnel/host or connection/TLS/network failure; confirm public HTTPS URL first |
|401| App reached; signing secret/raw bytes/timestamp mismatch |
|403| A private tunnel/authentication gate or origin policy may be in front; callbacks use public cloud path |
|404| Wrong path, old deployment or unrelated host |
|409 email disabled| App reached; enable email and finish server settings |
|503| Check cloud logs, Supabase/schema/config, provider reads or unmatched unresolved original send; replay after repair |
|200| Request accepted/recorded, duplicate or intentionally ignored; inspect response and saved evidence |

GET reachable JSON confirms routing, not signature validation, delivery or correct correlation. Actual signed POST and saved email evidence establish those later steps. A POST without signature must fail; never remove verification to make the dashboard green.

## 5. Verify visitor and owner flows

In an **Incognito/InPrivate** browser, open the root URL and click **Start**. Expect real backend/SSE stages and synthetic invoice results. With default LLM off, four eligible templates are clearly labelled; no invented model/email event. Visitor history lists only that browser's runs. Another private session must not open the first session's saved run by copying its UUID. Old local/owner runs must not appear to a fresh visitor.

In your owner browser, open **Controlled email demo · owner access**, enter `EMAIL_OWNER_TOKEN` and select **Unlock owner tools**. Owner login enables old history and private mail activity; explicit send/review actions still require the token and confirmation. Owner role cookie lasts one hour; page refresh does not immediately end that role, but sending needs the token field again. **Close owner access** clears the role/token/display. Never give interviewers this token. Share only the website URL.

Test one real approved email and reply as in M5. Owner sees private inbox content; visitors see collection progress/drafts and public audit only. Private email/reply/followup events are excluded from visitor run JSON, synthetic-review/dry-run responses and SSE. Visitor-visible flow must never claim a real email was sent when owner-only actions were not run. M5 follow-ups are dated work tasks, not automatically executed email jobs.

After template deployment works, enable Groq privately by adding `GROQ_API_KEY` and changing `COLLECTIONS_LLM_ENABLED=true`. Confirm the Groq account is Free. Keep free-only true; public mode blocks paid-provider routing even if someone calls Start without first opening health. Verify one actual successful model draft/audit; a labelled fallback is not live-model proof.

## 6. Public limits and privacy behavior

SQL006 atomically creates the run and its browser ownership; no transient unowned public run. Sessions are signed7-day Secure/HttpOnly/SameSiteLax cookies, no provider key. Owners authenticate with a random token, not a subscription/account API key. Browser sessions are not verified people: clearing cookies starts a new session; global limits still hold.

Daily limits use UTC and persist through server restart/deploy:

| Action | Per visitor browser | Global demo |
|---|---:|---:|
| New runs |3|20|
| Model attempts, including reply classification |8|40|
| Owner email reservations | Owner-only |10(existing M5 cap)|

Owner/webhook model attempts also consume the40global budget. Owner runs consume20global capacity. Per-run4/process20language caps remain, so a local process cap may trigger earlier. Quotas are reserved before provider calls; errors/validation failures consume attempts. DB budget failure makes no provider request. Quota-limited language falls back visibly; run quota returns429. No endpoint upgrades plans or falls back to paid providers. This does not verify an account is actually Free, bound billing on a paid account, prevent denial of service or provide enterprise authentication.

Only synthetic AR data may be used in the visitor demo. Actual replies/addresses are owner-only; public run access and event filtering protect their routes. Do not share owner cookies/tokens. The browser that started a run needs its session cookie to reopen it; clearing cookies/rotating session secret loses visitor access. Owner can still inspect history. Keep owner secrets stable/private. After exposure, rotate both owner and session secrets to invalidate existing owner-role cookies.

Monitor Supabase storage/provider usage. No automatic deletion was added because prior history must be preserved. Free quotas are not indefinite storage guarantees; export/review your own old demo history before deliberate cleanup. Visitor data editing remains deferred.

## 7. Free-host limitations and interview preparation

Render Free sleeps after15idle minutes and takes about a minute to wake. A webhook arriving during wake-up can fail or wait and require retry. A stable URL removes laptop/tunnel dependency; it is **not always-on free hosting**. Before an interview, open the site manually, wait for healthok and confirm Supabase is resumed. No automated keepalive is added. Resend retries failed callbacks with backoff and permits manual replay; inspect disabled endpoints too.

Render also has monthly compute/bandwidth/build allowances. A payment method can permit charges for supplementary usage; verify billing/spend controls and keep the service plan Free. Without a payment method, allowance exhaustion can suspend service/builds instead. ChatGPT's linked card does not configure Render billing. No paid upgrade is required for these steps, but the app cannot guarantee every account setting is free.

Supabase Free can pause; keep it as the database rather than Render's expiring Free Postgres. Resend uses HTTPS, avoiding Render's Free SMTP-port restriction. Git-tracked model artifacts ship with the app; no training or local database at runtime. Render disk is ephemeral; Supabase retains history.

Deploy manual changes when no run is active. Keep one Uvicorn worker and one main backend per database; do not concurrently run your local app against the cloud demo DB. Restart recovers abandoned work as interrupted, not resumed. No always-on worker/job queue claim is made.

## 8. Code and remaining acceptance

| File | What changed |
|---|---|
| `render.yaml` | One Free Python service, pinned runtime, build/start/health/secrets/manual deploy |
| `backend/public_demo.py` | Signed sessions/owner role, ownership checks, private-event filtering, context and budget guard |
| `sql/006_public_demo.sql` | Backend-only access links and atomic daily quotas |
| `backend/main.py` | Public boundaries, owner login/logout, liveness and webhook reachability probe |
| `backend/runner.py` | Atomic public run creation before starting actual work |
| `backend/language.py` | Provider-independent durable pre-call budget hook |
| `dist/app.js` | Public-mode explanation, owner access/logout and private-mail UI gate |
| `scripts/check_deployment.py` | Owner-run read-only live smoke check |
| `tests/test_milestone_6.py` | HTTPS session isolation/privacy/quota/restart/CSRF/cloud-fail-closed/probe tests |

**97 tests passed on Python3.12.14**, including16M6cases and81regressions. HTTPS session/privacy/quota/fail-closed tests and local HTTP/SSE/frontend DOM checks passed, covering public Start/history, owner login, mocked email/signed reply/review/task and logout. Existing mocked Groq UI flow also passed. Python/JS syntax and local YAML parsing passed; one existing Starlette/httpx deprecation warning remains. Render settings were checked against official docs, not validated by a live Render account. Details are recorded in PROJECT_KNOWLEDGE.md. They use mock providers/isolated SQL; no Render account, service, secrets, actual callbacks or provider bills were created by assistant. Actual URL, deployment health, Resend replay/real reply and deferred Groq live checks must still be verified before declaring all milestones complete. After that, record learner completion and prepare the short interviewer walkthrough; visitor editing is optional later work.

Official references checked2026-10-17:

- https://render.com/docs/deploy-fastapi
- https://render.com/docs/free
- https://render.com/docs/python-version
- https://render.com/docs/blueprint-spec
- https://resend.com/docs/webhooks/retries-and-replays
- https://resend.com/docs/webhooks/verify-webhooks-requests
