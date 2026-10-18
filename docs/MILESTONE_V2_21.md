# V2.21 — Draft with AI

## What the visitor sees

Open an invoice. Beside Send reminder, choose **Draft with AI** (or **Redraft with AI** when the current reminder is already AI generated). A small inline editor accepts optional tone, brevity and wording preferences, for example “Make it warmer and shorter. Ask for an expected payment date.” Click Generate draft, review the saved result, then send separately. Opening or cancelling the editor makes no model call.

The button is available for eligible, unsent initial overdue reminders. Sent/uncertain send intents, customer replies, disputes, follow-ups, case holds and active processing cannot be rewritten. Disabled controls explain why in their title; the server enforces the same policy. This milestone does not regenerate missed-promise follow-up templates.

## Setup — required SQL

1. Merge/pull this PR.
2. In Supabase SQL Editor, run `sql/015_ai_draft.sql` after the existing migrations through SQL014. It is additive and repeatable; do not reset the database. It preserves invoices, runs, replies, checkpoints and sent mail.
3. Deploy latest main on Render; hard-refresh. `/api/health` should show app_version `v2.21`, ui_version `workflow-21`, and `ai_draft.ready: true` / schema15. If SQL015 is missing, this feature is disabled with an actionable message; the existing portfolio remains available.
4. No new environment variables, packages, keys or quota changes. Existing LLM configuration must be enabled and valid. Every explicit generation uses the same durable browser/global and process budgets; opening the editor does not.

## How it works

`dist/draft-ui.js` manages the inline editor, per-invoice in-memory preferences, busy indicators and request UUID. `POST /api/cases/{id}/draft` accepts only request_id and instructions (plain text, max600 characters). It uses signed browser case ownership.

`CaseService.redraft` reserves the request durably, then `LanguageService.redraft` calls the selected LLM once with validated invoice facts and preferences as untrusted user data. The existing system instructions, strict schema, exact-fact echo and prohibited-prose checks remain. Preferences cannot change the recipient or directly submit an email body. Only validated output updates the saved case draft and draft-preview message; the original portfolio result and source AR remain unchanged. The draft audit records provider/model/usage/input hash and explicit generation trigger; preference text is not retained in database attempt records (only a hash). It is sent to the configured model and retained in browser memory while navigating invoices.

Generation never sends email or grants automatic authority. Existing approval checkpoints remain intact. The later Send reminder action reads the saved case draft, and SQL rejects a stale payload. The graph therefore sends the updated preview after the person chooses Send; it does not reuse an old draft body from a checkpoint.

SQL015 creates private `ca_draft_attempts`, a case `draft_generation` summary, generation RPCs and a send reservation guard. Requests are replay-safe across restarts. A completed/failed/reserved UUID does not make another model call; changed preferences require a new explicit request. An unresolved reservation blocks overlapping generations/sends for five minutes; a new explicit request can then supersede it. Late results cannot overwrite the newer draft. Final commit rechecks eligibility, so an intervening reply/hold/send prevents saving. Case locks serialize graph approvals; SQL locks serialize draft commits and mail intents. No database transaction is held open while waiting for the model.

On a model failure, the existing draft remains and a safe reason is saved. On an unknown network outcome, the browser retains its request UUID and checks it on retry instead of silently repeating the model call. Reload restores saved drafts/status; unsaved preference text is not durable. Ordinary model failures are still possible and remain visible.

## Validation and hands-on exercise

A 100-test backend regression run passed across AI draft, formatting, provider/M4, sending, LangGraph, promise follow-up and mode suites. After adding migration-readiness/stale-payload assertions, the final feature suite passed all12 tests. Tests cover saving/restart/replay, exact updated graph send, old-run immutability, validation/transport/quota failures, ownership/overrides/input limits, durable budgets, reserved/stale requests, generation/send races, changed-case discard, repeatable/private migration and missing-migration behavior. Providers are mocked; PostgreSQL functions run locally in PGlite.

Actual local HTTP/cookie/SSE JSDOM UI checks passed: editor open/cancel no call, optional escaped preferences and per-invoice retention, busy/double-click gates, success preview, invalid-output preservation, empty preferences, simulated lost-response retry without repeat model call, exact reviewed send and reload persistence. That journey used three mock LLM calls and one mock email. Six-script ordering, preserved analytics beacon, two Markdown guide pages and JS/Python syntax checked. Native visual/focus-trap behavior and live LLM acceptance remain owner checks; no actual model/email calls, Supabase migration or deployment were performed by the assistant.

After deployment, use an existing eligible unsent case in Review & approve mode. Choose Draft with AI, enter preferences, Generate, inspect the LLM badge/audit, then Send reminder. If the existing case is already sent/held/replied, use another eligible unsent case or the established Incognito walkthrough within shared quotas. There is no new fresh-demo/reset feature.
