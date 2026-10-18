# V2.11 — Compact live execution and invoice logs

## Apply

Merge/pull, manually deploy latest main in the existing Render service and hard-refresh. Health must report app_version v2.11 and ui_version workflow-13. No new SQL, dependencies, keys, accounts or environment settings. Existing SQL009–012 remain prerequisites. No live provider calls or deployment by assistant.

## What visitors see

Portfolio processing is back above the queue as a compact horizontal strip of stage names and state icons. Descriptions are removed. The small status line shows the actual invoice/action being recorded and successful processing counts. Detailed portfolio events remain collapsed below the table.

The first six stages are portfolio preparation: load, validate, urgency rules, model prediction, prioritization and drafting. A seventh stage, Process invoice actions, stays active until the backend case job ends. Preparing drafts is not presented as completing LangGraph invoice processing. Waiting approvals are valid processed outcomes; unhandled invoice errors remain explicitly reported by the previous milestone.

Every row gains a small Log button at the end, alongside the original eight fields. It opens that invoice popup and focuses its event history. History shows up to 40 retained saved events, with identity, timestamps and status. Opening a row or log remains read-only. Normal email/reply row opening remains unchanged.

## Actual execution, not presentation timers

Portfolio stage events already come from persisted backend operations. New owned SSE endpoints stream saved graph/case changes immediately:

- GET /api/runs/{id}/agent/events: initial owned job/case snapshot, then committed job progress and case activity during that run.
- GET /api/cases/{id}/events: initial owned case snapshot, then committed invoice activity for manual approvals, replies and due checks while its popup is open.

CaseAgent publishes only after the existing SQL patch/effect/job operation returns successfully. The live fan-out uses a bounded in-process delivery queue, with run context in ContextVar so concurrently running jobs do not share event routing. This is a transport buffer, not an alternative business database/checkpointer. On reconnect, SQL snapshots and retained case activity restore current truth. Buffer overflow retains recent messages; the next snapshot/history catches up within existing retention. The source remains Supabase SQL and LangGraph checkpoints. No new hosted realtime service or tracing.

The server cleans up subscriptions on disconnect. A run stream finishes when its job is terminal; the selected case stream closes on popup dismissal or switching. Five-second snapshot catch-up and the existing bounded polling path cover reconnects and provider status updates. Events contain only existing public case projection; real private inbound/owner inbox remains excluded. Both endpoints enforce signed browser ownership.

The UI avoids older polling responses overwriting newer streamed state. It preserves database timestamp ordering, including sub-millisecond precision. Starting a run clears the old job/stream first; previous-run completed icons do not flash as if they describe the new run. No sleeps, timer-driven fake progress or slowed providers were introduced. The existing ML inference/templates can complete quickly; repeated runs retain saved cases and the strip explicitly reports the retained count. Already completed work is not rerun to make the demonstration longer.

## Next step button correction

Previously the top button's busy condition included the entire portfolio job, even when the selected invoice had a ready pending approval and its own Send button was enabled. It now uses selected-case processing, active user action and load-error state. A pending valid invoice approval is available while other invoices continue. Actual eligible action checks, draft identity, fixed recipient, case holds, mail readiness/quota and provider idempotency remain unchanged. Waiting/disputed/settled invoices do not gain fake actions.

The current invoice log updates from its SSE during later manual actions. Its Current step line follows recorded node activity while processing, rather than waiting for the full HTTP action to return before showing any change. Unsent reply text and independent selected-invoice state are retained.

## Code map

| File | Responsibility |
|---|---|
| backend/workflow/events.py | Bounded live fan-out and run task context |
| backend/workflow/agent.py | Publish committed case/effect/job updates; count retained cases |
| backend/main.py | Owned SSE routes and build version |
| dist/workflow-ui.js | Run/case stream lifecycle, timestamp ordering, case-specific action eligibility |
| dist/app.js | Compact seven-stage rendering, reset old state, row log button |
| dist/invoice-ui.js | Direct event-log focus and selected stream cleanup |
| dist/index.html/styles.css | Top compact strip, hidden descriptions, ninth log column |

## Hands-on exercise

1. Start Review & approve: watch six preparation stages followed by Process invoice actions. A fast step may move immediately; all changes represent backend state.
2. Open an invoice whose reminder is ready while other invoices are still processing. Its top Send reminder should be enabled if email is configured and the case is eligible.
3. Click a row's Log button. Verify the invoice ID matches and its recorded events appear. Switch invoices; their histories must stay separate.
4. Send a reminder or simulated reply. Watch this invoice's current step/history update during processing; approvals remain explicit.
5. Repeat a run: retained cases explain quick completion and must not send duplicates. Reload: saved progress/history return without pretending an execution just happened.
6. Resize in a native browser: stage names scroll horizontally if needed; all nine table fields remain available. DOM tests do not establish pixel appearance.

## Validation

48 unique isolated SQL/API/LangGraph/reporting/follow-up/live-delivery checks passed with mocked providers. New tests verify published graph activity exists in committed SQL, terminal owned SSE snapshot is read-only/private, cross-browser access blocked, delivery queue bounded/cleaned up, repeated runs report retained cases and manual approval publishes execute-started/completed events with one accepted email.

Local HTTP/SSE/cookie-aware JSDOM journey passed real run/invoice streams, compact top flow with no descriptions, nine columns and row-log focus, selected identity, fresh-state reset, seven-stage completion, top approval enabled while a different invoice was deliberately held in progress, send/delivery, interruption recovery, simulated reply reconciliation, promise/date/follow-up/reload and unchanged source. That artificial gate exists only in the test harness; production has no pacing delay. JavaScript syntax/Python compilation passed. Deployment/native visual acceptance remains Charan's work.

Next: guided interviewer walkthrough. Visitor data editing remains last.
