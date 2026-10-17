# V2.8 — Run results and compact collections queue

## Apply

Merge the milestone PR, pull main and manually deploy the existing Render service. No new SQL, packages, keys or environment settings. Existing SQL009–012 prerequisites remain. Hard-refresh to load workflow-10 assets. Old completed runs do not gain invented outcome reports; start a new run to see saved per-invoice results.

## Visitor experience

Run overview replaces Portfolio overview. Its header identifies the selected run, original mode, creation time and completion/interruption. An interrupted run explicitly shows partial results. A completed run means processing finished, not all invoices paid.

- Results during this run: invoices reviewed, invoices with newly accepted initial reminders/follow-ups, newly recorded promises, disputed invoices on hold and new dispute holds. Dispute source exposure is shown separately from collected cash.
- Needs your action now: initial/follow-up drafts to send, promises to record and invoices needing attention. These reflect live cases, including work from earlier runs or after this run ended.
- Waiting on customers or delivery now: replies awaited, recorded promises and pending delivery confirmation.
- Expand Current invoice statuses for the complete reason breakdown. Generic Monitoring is replaced by the actual reason. Awaiting approval specifies the pending action.

Click a nonzero count to filter invoices across stages. Clear result filter restores the selected stage; Overdue/Preventive also exits the result filter. Filters do not start any action. Normal row opening/email/reply/Continue behavior remains.

Queue header uses one wrapping flex row with title/count, stage and urgency filters, short row-open hint. Preventive totals appear only in Preventive view. It adapts to width rather than forcing tiny text or horizontal header overflow. Remove the custom arrows/range slider; bounded native table scrolling remains available. Preserve all eight dedicated fields. Final columns are Current status, Last completed action, Next step: where it stands, what happened, what should happen next.

## How reporting works

`backend/workflow/reporting.py` captures small, public case snapshots: accepted email IDs, recorded promise and status. `CaseAgent.run_job` saves each invoice's baseline into existing ca_agent_jobs.progress JSON **before** invoking its graph, then saves its resulting snapshot/count evidence after processing. Completed invoice entries are skipped on job resume; incomplete entries reuse the same baseline. Stable email IDs prevent earlier accepted emails from being counted again. Original case.run_id is never used to infer this run's sends.

This is a bounded before/after processing report, not a new global event ledger. Actions occurring later (manual approval, simulated reply, promise check) update current case sections, not frozen run achievements. An action submitted concurrently from another tab during the processing interval can appear in its baseline delta; this report measures changes during processing and does not assert autonomous-agent causation. Use one active browser flow for the interview walkthrough. A causal actor/event ledger would be a separate future enhancement if multi-operator attribution becomes necessary.

Delivery confirmations remain live for the exact accepted email IDs saved in this run. Accepted means provider submission, not delivery/payment. Delivery issues take precedence over delivered in the summary. Missing reports on older runs are explicitly unavailable, never reconstructed from current case state. An older interrupted job resumed after this release is labelled partial if it already processed invoices before tracking existed. Run history loads the matching job report instead of showing the latest unrelated job. Refresh restores the latest job report without opening the invoice dialog.

Current statuses show the displayed portfolio's invoices and this browser's saved cases; they are not a historical reconstruction. New runs preserve existing cases/authority and do not resend. Model/mail caps, ownership, source AR and deterministic tool policies are unchanged. No live model/email calls or cloud deployment by assistant.

## Hands-on exercise

1. Run Review & approve. Open Run overview: all invoices reviewed, zero emails submitted during processing, reminders ready to send.
2. Click that approval count, open an invoice, send its reminder. Current approval count falls; the completed run's sent count remains zero because you sent it later.
3. Start another run. It must not claim that earlier email or resend it. Inspect the two saved run reports from history.
4. In a genuinely fresh set of eligible cases, Automatic processing submits at most three initial reminders. Run overview counts distinct invoices and awaits signed delivery separately.
5. Check disputes, synthetic replies and payment promises. Current invoice status explains their exact waiting/review reason. Source balance never changes.
6. Resize the page and check the compact header and native table scrollbar in your actual browser. DOM tests do not establish pixel layout or native focus-trap behavior.

## Verification

34 actual SQL/LangGraph/reporting tests and 8 preview/email regressions passed with isolated PGlite and mocked providers. Reporting checks cover frozen results after manual approval, repeated-run non-attribution, persistence across restart and recovering a crash after email acceptance without duplicate sends. Local HTTP/SSE/cookie-aware JSDOM checks passed new labels/order, result filtering/clearing, slider removal, 24-row preload, dialog/focus/draft retention, graph interruption/resume, email acceptance/signed delivery, simulated reply reconciliation, promise/date/follow-up/reload, and unchanged source. JavaScript syntax passed. Actual deployment and visual acceptance remain Charan's checks.

Next: guided interviewer walkthrough. Visitor data editor remains last; no scheduler or paid voice integration added.
