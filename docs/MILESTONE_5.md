> Current send UX is documented in [V2.2](MILESTONE_V2_2.md): Send email beside the draft, no owner token required. Older token/dry-run UI instructions below are historical. Existing Resend/webhook setup still applies.

# Milestone 5 — Send a controlled email and capture its reply

M5 PR#6 is now merged; M6 cloud deployment supersedes the temporary forwarding instructions below when hosting. See docs/MILESTONE_6.md for the direct cloud callback and Resend Connect troubleshooting.

M4 PR#5 merged as a18edaad. Charan explicitly deferred its LLM drafting/reply learning checks until after M5. Those checks remain pending; M5 works with `COLLECTIONS_LLM_ENABLED=false` and deterministic templates. No need to enable a model to send your first email.

## 1. Get the code and prepare the database

Review/merge the M5 pull request in the canonical repository. Preserve/commit/push local edits, stop Python and run in your existing VS Code project:

```powershell
git status
git switch main
git pull --ff-only origin main
```

In your existing Supabase SQL Editor, run `sql/004_language_review.sql` if not already applied, then **`sql/005_email_loop.sql`**. SQL005 adds four small tables plus backend-only functions; no existing source/history is dropped. Re-running is safe. Keep the prior SQL001/002/003 setup.

Start the existing application, bound locally:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Open http://localhost:8000 . Health reports M5. Start a normal run: original nine-row totals and13template-mode events remain. The email panel is separate from the six collection stages and the older dry-run approval. Nothing sends just by running the pipeline.

## 2. Use a free email account and your own test inbox

Sign up at https://resend.com with an email address you own and keep the account on **Free**. This POC uses `onboarding@resend.dev` to send only to your own Resend signup email, avoiding a purchased sending domain. Do not upgrade or add unrelated recipients for this test. Confirm current account limits in its dashboard; free availability is not unlimited. The app cannot verify account billing tier.

Create a private Resend API key with the permissions needed for sending **and retrieving sent/received messages** (Full access for this small separate demo account). A sending-only key cannot retrieve inbound content. Never paste the key in chat, screenshots, Git or website fields.

In Resend **Emails → Receiving**, open **Receiving address** and copy your account's unique `<id>.resend.app` subdomain. Use only the subdomain in `.env`, without a username or @. The app creates one random `collections-<messageUUID>@<id>.resend.app` Reply-To per approved email. This handles reply correlation without buying a domain.

## 3. Let Resend reach only your callback

A webhook is Resend calling your backend when delivery or a reply occurs. Resend cannot call localhost directly. M5 includes a small forwarding app exposing only the callback path. Keep the main app's8000port private.

Open a **second VS Code terminal** in the same project:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.webhook_gateway:app --host 127.0.0.1 --port 8001
```

In VS Code, open **Ports** (View → Open View → Ports, if hidden). Choose **Forward a Port**, enter **8001**, and sign in if VS Code requests it. Change that forwarded port's **Port Visibility** to **Public** so Resend can call it. Copy its HTTPS forwarded address. Do not forward8000. The helper has no UI, run routes, database initialization or API docs; it forwards only `POST /api/webhooks/resend` to the fixed local main app while preserving raw bytes/signature headers.

In Resend **Webhooks**, add an endpoint:

```text
https://YOUR-FORWARDED-ADDRESS/api/webhooks/resend
```

Subscribe to `email.sent`, `email.delivered`, `email.delivery_delayed`, `email.bounced`, `email.complained`, `email.failed`, `email.suppressed`, and `email.received`. Copy that endpoint's private signing secret (`whsec_...`). Do not use your API key in its place. Keep VS Code and both terminals running during the live demo. Forwarding addresses can change; update Resend when needed. Stop forwarding after testing. This is temporary webhook connectivity, not M6 website hosting.

## 4. Configure privately and restart

Generate an independent owner token in the terminal:

```powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(32))"
```

This token authorizes email approval/review in your own local UI; it is **not** the Resend or Groq API key. Edit the existing ignored `.env`, preserving Supabase/Groq settings:

```dotenv
COLLECTIONS_LLM_ENABLED=false
EMAIL_ENABLED=true
RESEND_API_KEY=YOUR_PRIVATE_RESEND_API_KEY
RESEND_WEBHOOK_SECRET=YOUR_PRIVATE_ENDPOINT_SIGNING_SECRET
EMAIL_OWNER_TOKEN=YOUR_NEW_RANDOM_OWNER_TOKEN
EMAIL_FROM=onboarding@resend.dev
EMAIL_TEST_RECIPIENT=YOUR_OWN_RESEND_SIGNUP_EMAIL
EMAIL_RECEIVING_DOMAIN=YOUR_ACCOUNT_SUBDOMAIN.resend.app
```

Use the actual subdomain; placeholder underscores/uppercase are not valid. The test recipient must be one bare email address, lowercase. Restart the main app, refresh the page and check email readiness in health. Existing terminal variables override `.env`. Keep all API secrets server-side; the browser receives no provider keys. No new runtime Python dependency is needed.

## 5. Send one reviewed draft

Start a new collection run. Open **Controlled email demo · owner access** above the queue, enter only the owner token and click **Unlock test sending**. The page shows the exact fixed test inbox and sender. The token remains in page memory/password field; it is not saved to browser storage. Refreshing the page requires entering it again.

Select an eligible overdue invoice, read its displayed draft and choose **Review & send test email** in the separate email panel. Confirm the dialog. Every message carries an `[O2C DEMO]` subject and a synthetic-data disclaimer. The backend cannot accept a visitor-supplied recipient, body or model.

The backend first saves an owner-approved send intent, exact payload, random Reply-To and unique run/invoice key. It then calls Resend with a stable provider idempotency key. **Accepted** means Resend accepted the request, not that the email reached your inbox. A verified `email.delivered` event confirms delivery to the recipient mail server, not that a human read it. Delivery events appear individually; delayed/out-of-order events do not overwrite a single misleading latest-status badge.

Check your inbox/spam and the Resend dashboard. The website polls email activity every five seconds after the collection run completes, and has **Refresh email activity**. Post-run email actions append actual audit events; six pipeline stages do not replay. Earlier dry-run approval remains available and is explicitly not an email send.

A second click after accepted/restart returns the same saved message without sending again. Timeout/error records **uncertain**, even when rejection seems likely: it cannot claim no email was sent. There is no automatic retry. After inspecting Resend, a manual retry uses the same saved payload/idempotency key. Unknown intents older than20hours are blocked to stay within the provider's24-hour dedup window. Do not create a fresh run to bypass an unresolved send.

There is a **durable limit of10new email reservations per UTC day**, shared by the database and surviving Python restart. Failed/uncertain reservations count too. This is deliberately below normal provider free-plan capacity. Owner token/one recipient are POC controls, not complete public authentication or LLM abuse controls; M6 is still required.

## 6. Reply from your own inbox

Click **Reply** on the received message, keeping its thread and generated Reply-To. Do not compose an unrelated message or forward it. For a first test, write a short new plain-text line:

```text
We paid this invoice yesterday.
```

Use plain text if your mail client offers it. The received-email webhook carries metadata; Python fetches content/headers from Resend's fixed API. It verifies the random Reply-To, expected sender, original RFC Message-ID in `In-Reply-To`/`References`, and provider-computed DMARC pass. A valid webhook signature proves the callback came from the provider, not that the customer's financial claim is true.

Matched plain text up to4000characters can use the existing Groq classifier if enabled. With LLM disabled it is honestly labelled **manual_review**; the real received reply is still stored. Unexpected sender/thread/authentication goes to **quarantined** without an LLM call. HTML-only/long content requires manual review; no HTML, attachments or remote links are executed/downloaded. Missing original RFC ID/API failures trigger callback retry rather than an invented match. Unmatched addresses are ignored, not attached by invoice number in a subject.

In the email panel, choose the reviewed intent and **Confirm review & schedule follow-up task**. For the paid claim choose `payment_claim`; this creates a reconciliation task for tomorrow's UTC date. It never closes the invoice or reduces its balance.

For a promise test, reply with a **future** literal ISO date and amount, e.g. `We will pay 1000.00 on YYYY-MM-DD.` Replace the placeholder with a future date. Enter that date/amount and its exact supporting quote in the review form. Python checks literal evidence, future date and amount within saved balance; the task is due the day after the promised date. Other intents create tomorrow's review task. Unsupported/relative promises remain manual tasks until you obtain supported evidence. Promise checks use current UTC review/receipt date, not the fixed2026-10-17portfolio snapshot.

Reviewed disputes create an investigation task and a durable email hold for that invoice across later runs. They do not rewrite the original AR source or historical snapshot. Resolve the underlying dispute with the AR owner before manually clearing its demo hold. No automatic follow-up email or unattended scheduler is added: the scheduled records are AR work tasks with due dates. Duplicate review/callback creates no second saved task; saved reviews cannot be silently overwritten.

## 7. Understand the code

| File | Responsibility |
|---|---|
| `backend/mail/config.py` | Explicit opt-in, fixed test address, private key/token/signing settings |
| `backend/mail/provider.py` | Resend HTTPS send and sent/received retrieval; no retries |
| `backend/mail/signatures.py` | Raw-body Svix v1 HMAC, timestamp tolerance, constant-time checks |
| `backend/mail/service.py` | Owner approval, stored send intent, thread/sender checks, review/follow-up policy |
| `backend/webhook_gateway.py` | Temporary callback-only forwarding to local8000; no run routes |
| `sql/005_email_loop.sql` | Messages, webhook dedup, real replies, follow-ups, durable daily cap, dispute hold and audit RPCs |
| `backend/main.py` | Email activity, send, signed callback and owner-review HTTP endpoints |
| `dist/app.js` | Owner unlock, approval dialog, five-second activity refresh and review form |
| `tests/test_milestone_5.py` | Mock transport + real isolated SQL tests of side effects and failures |

Routes: `GET /api/email/owner-config` (owner token), `GET /api/runs/{run}/email`, `POST /api/runs/{run}/invoices/{invoice}/send-email` (owner+review confirmation), `POST /api/webhooks/resend` (provider signature), `POST /api/runs/{run}/replies/{reply}/resolve` (owner).

Finance snapshots remain immutable. New messages/replies/tasks live in separate tables; post-run audit events are appended under run locks. SQL functions/table access remain backend-only, no anon/authenticated grants. One main backend process per database remains required. Callback+LLM+DB writes are not a distributed transaction: repeated calls can consume LLM quota if saving fails; no exactly-once provider billing guarantee. Main API/history has no general public authentication yet; keep it local.

## 8. Learner checkpoints and troubleshooting

Verify your first email reaches your inbox, a signed delivery event appears, an actual reply is saved, a human-reviewed paid claim schedules exactly one reconciliation task without changing AR, repeat actions are deduplicated, and reopening history after restart preserves all evidence. Then return to the deferred M4 Groq learning exercises.

- Schema missing: run SQL004 then SQL005 in the project matching your existing Supabase URL.
- Email disabled/not ready: inspect health and restart after `.env`; check terminal overrides,32+character token, actual receiving subdomain and signing secret.
- Resend403: test sender can only send to your Resend signup address; Full access key is needed for reads. No paid upgrade/domain purchase is required for this controlled demo.
- Accepted but no delivery: inspect Resend's real events/spam; do not claim delivery based on acceptance.
- No callback: both local apps and VS Code public forwarding8001must be running. Check endpoint URL, subscriptions and delivery attempts in Resend. Main8000stays private.
- Signature401: use the secret for this exact webhook endpoint; keep system clock synchronized. Do not bypass signature checks for testing.
- Reply quarantine: check From, Reply-To, original thread/DMARC and plain text; human review is expected when those checks fail. Signature alone is insufficient.
- Provider429: wait for rate/quota reset; no automatic retries or tier upgrades.10reservation cap uses UTC day and does not reset on Python restart.
- Unresolved intent20+hours: reconcile using the provider dashboard. Only after verifying its actual matching recipient/subject/body, record the known provider UUID in SQL Editor with `select public.ca_mail_finish('SAVED_MAIL_UUID'::uuid,'VERIFIED_RESEND_EMAIL_UUID',null);`. Do not invent an ID or resend an unknown old intent. This repairs acceptance evidence, not proof of delivery.

**81 tests passed on Python3.12.14**, including17M5tests and the previous64regressions. Real local Uvicorn HTTP/SSE/frontend DOM passed both existing Groq mocked flow and the new template-email flow through owner approval, mocked send, signed inbound callback, reviewed reconciliation task and unchanged AR. Python/JS syntax checks passed; one existing upstream Starlette/httpx deprecation warning remains. Automated checks are mocked integration evidence, not proof of your live Resend/Groq tier, account permission, deliverability, tunneling or Python3.13.5 compatibility. Assistant has not obtained keys, sent mail, registered accounts, exposed ports or deployed the app. Live learner acceptance remains pending.

Next M6: deploy under Charan's account with public access/LLM quotas, private-history/PII treatment and operator controls. Then optional visitor data editing. Temporary callback URL is not the final interviewer demo URL.

Official references checked2026-10-17:

- https://resend.com/pricing
- https://resend.com/docs/dashboard/receiving/introduction
- https://resend.com/docs/api-reference/emails/send-email
- https://resend.com/docs/api-reference/emails/retrieve-received-email
- https://resend.com/docs/api-reference/emails/retrieve-email
- https://resend.com/docs/dashboard/emails/idempotency-keys
- https://resend.com/docs/webhooks/verify-webhooks-requests
- https://docs.svix.com/receiving/verifying-payloads/how-manual
- https://code.visualstudio.com/docs/debugtest/port-forwarding
