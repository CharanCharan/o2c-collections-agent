# V2.2 — Send email beside the draft

The website now has one direct **Send email** action beside the reminder. It sends through Resend to the configured project test inbox. There is no owner-token entry, owner-unlock panel, extra approval modal or dry-run button.

## What the old dry run did

**Approve & record dry run** recorded a synthetic approval and event in Supabase, marked that saved run's invoice as contacted, and refreshed its suggested action. It never called Resend or sent anything. That was useful while learning persistence in M2, but is confusing in the working email product. The button is removed. Existing saved history and the legacy API remain readable/compatible; they are not converted into email-delivery claims.

## Install and try

1. Review/merge this PR, then pull the canonical repository:

   ```powershell
   git switch main
   git pull origin main
   ```

2. Run the complete [sql/008_case_email.sql](../sql/008_case_email.sql) once in your existing Supabase SQL Editor. SQL007 from PR#9 must already be installed. This script is additive and can be rerun; it preserves AR, conversations, runs and prior email records.
3. Render → existing service → **Manual Deploy → Deploy latest commit**. No new packages or services.
4. Existing email settings remain: `EMAIL_ENABLED=true`, `RESEND_API_KEY`, `RESEND_WEBHOOK_SECRET`, `EMAIL_FROM`, `EMAIL_TEST_RECIPIENT`, `EMAIL_RECEIVING_DOMAIN`. **EMAIL_OWNER_TOKEN is no longer required for the website or email readiness**; you can remove it from Render/local `.env`. Keep the existing `DEMO_SESSION_SECRET` because it restores this browser's saved cases. A configured old owner token is optional for legacy operator API calls; no token is sent by the website.
5. Reload → Start agent → select an eligible overdue invoice → inspect the draft → **Send email**. Clicking automatically opens/uses its collection case. You do not need to click Open collection case first.
6. Look beside the draft: **Accepted by Resend** means the provider accepted it; **Delivered** requires the actual signed Resend webhook. A failure/unknown outcome is shown truthfully. The button becomes **Email sent** after acceptance and cannot send a duplicate.
7. Check the project test inbox. Reload the website: the stored draft and send/delivery status should return without starting another run. Type a simulated customer reply in the conversation if desired.

The displayed case draft is the one sent, with a synthetic-demo prefix. If a case already exists, its originating run/date is shown; a newer portfolio run does not replace that draft or contact history. If a concurrent tab created a case with a different snapshot, the first click restores its draft for review before another Send click.

## How it works

| Component | Responsibility |
|---|---|
| `dist/app.js` `sendDraft` | Single user click; creates case if needed, calls the send endpoint, displays outcome |
| `POST /api/cases/{case_id}/send-email` | Browser-owned case, no body/recipient overrides or owner token |
| `backend/mail/service.py` `send_case` | Shared send tool: stored draft, server-configured project recipient, Resend adapter |
| SQL008 `ca_case_mail_prepare` | Atomic case/hold check, durable send reservation and case-message link |
| Existing mail idempotency/cap | Same stable payload/key on retry, ten new reservations globally per UTC day |
| SQL008 `ca_case_get` | Return only this case's outbound draft/send/delivery status; not the owner's private inbox |
| Existing signed webhook | Record provider delivery status; page polls saved status without extra model calls |

No model call is made by Send, reload or status polling. Sending uses the existing reviewed draft. If the outcome is unknown, no automatic retry occurs; the explicit Retry same email action uses the same stored intent/key within its valid window. Old uncertain intents require Resend reconciliation after20hours. Delivery issues are shown and never silently trigger a fresh send.

A successful acceptance moves an untouched case to **Awaiting customer response**. Any customer reply requiring review or a dispute holds further collection reminders. Repeated calls on an already accepted intent return its saved state without another provider call. No financial amount/payment state changes.

## Manual and automatic modes

This PR delivers the actual send tool and direct manual button. It does **not** pretend the LangGraph automatic mode is implemented.

The next milestone's graph will call this same Python send tool for an allowed automatic action. In limited mode it will pause for the user's Send click. A disputed invoice should pause collection chasing; a reviewed document/dispute response is a separate future action, not a resend of the overdue reminder. Approvals will authorize an actual action, never a second no-send dry run.

## Hands-on exercise

Send one reminder. Observe acceptance and webhook delivery, reload, and confirm you cannot send it a second time. Explain which table links the collection case to the send intent, and why “accepted” differs from “delivered.” Change only the visible button label locally to locate the UI code; the send action itself remains in Python.

Validation is recorded in PROJECT_KNOWLEDGE.md. Provider calls in assistant tests are mocked; user must verify actual delivery in the live project inbox after deployment.
