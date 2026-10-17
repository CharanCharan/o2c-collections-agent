# V2.6 — Collections language and compact actions

This is a UI update over V2.5. It changes wording, placement and invoice-specific continuation controls while preserving the existing backend, case ownership, approvals, email/model allowances and workflow behavior.

## Apply it

Review/merge the PR, pull main and refresh/restart locally or manually deploy the existing Render service. No new SQL, packages, API keys or environment settings. Existing SQL012 is still required for V2.5 promise functionality; this update does not replace it.

## Header actions

The two full-width portfolio/promise banners have moved into compact panels beside the primary action:

| Action | Purpose |
|---|---|
| Run collections | Start portfolio analysis and permitted collection actions |
| Portfolio overview | Open invoice/outcome counts and, if interrupted, Continue collections run |
| Payment promises | Open Promise-to-pay management: simulation date and Process due promises |
| Collections run history | Open a previously saved run without starting another |

The panels open on click, not hover. Only one opens at a time; outside click or Escape closes it. Portfolio/promise badges show counts or processing/paused state. The invoice table and customer workspace now follow the portfolio metrics directly, without the two large banner rows.

Inside Payment promises, **Set simulation date** and **Advance simulation by7days** only move simulation time. **Process due promises** checks expired promises/payment evidence and can prepare or send a follow-up under each invoice's saved mode. **Continue promise processing** appears only for an interrupted check. Due checking still needs an explicit trigger; no background scheduler was added.

## Modes and business actions

The mode dialog uses **Review & approve** and **Automatic processing**, with short explanations. Their backend values remain limited/autopilot, and saved case modes are not changed by a rename or a later run.

Approval buttons name the actual action, such as **Record payment promise**, **Send reminder** or **Send follow-up**. Declining an approval is labelled **Leave for review**. Recorded payment promises display their next review date; waiting for that date is not an interruption.

The execution column is labelled **Collections activity**, with **Invoice activity** for the selected invoice. Node headings use business descriptions such as Select collection action, Request approval, Complete action and Prepare promise follow-up. These are labels for real recorded nodes, not fabricated activity or private model reasoning.

## Continue a selected invoice

After selecting an invoice with a saved collection case, its customer panel shows a short **Collection case** reference above the customer/email content. The complete UUID is available in its title. This is the existing case/thread identifier, not a new identifier or another workflow.

**Continue invoice processing** appears in that same top area only when saved work is unfinished: the workflow is marked processing or the latest simulated reply still awaits processing, no approval is pending, and the UI is not already processing a run/check/action. The button invokes the existing browser-owned case resume endpoint with that selected case's full ID.

It stays hidden for completed invocations, recorded promises waiting for a date and pending approvals. A pending approval uses its specific action button instead. Completed processing can still leave an invoice unpaid or awaiting review; that alone does not make it resumable.

If a reply or approval request fails, the UI refreshes the saved server state before deciding whether continuation is available. Older pending replies superseded by a newer reply do not keep an irrelevant Continue button visible. After successful continuation, the control disappears when no unfinished processing remains. Changing the selected invoice updates the reference/control for that invoice.

Continuation uses the existing checkpoints and receipt/idempotency protections. It does not reset invoices, start the entire portfolio again, authorize a pending action automatically, or promise that a failed external operation can always complete.

## Find the code

- `dist/index.html`: compact header panels, renamed actions and mode descriptions.
- `dist/styles.css`: responsive action panels and selected-invoice case toolbar; V2.5 bounded panels/horizontal table controls retained.
- `dist/workflow-ui.js`: business node/action names, selected-case continuation eligibility and existing resume binding.
- `dist/followup-ui.js`: promise badge and renamed simulation/promise controls; existing APIs unchanged.
- `dist/app.js`: customer-header placement, refreshed state after request failures and header-panel interactions.

Exercise: open Portfolio overview and Payment promises before running collections. Neither should start a run. Run collections, select an invoice awaiting a send approval and confirm it shows Send reminder rather than Continue. Inspect a recorded promise: its date/next review are visible, with no Continue button merely because payment is pending.

## Verification

22 existing follow-up/email API and SQL regression tests passed with mocked external providers. Local HTTP/SSE/cookie-aware JSDOM checks passed header panel placement, one-open-at-a-time/Escape behavior, no run on opening menus, all eight table fields and existing promise/date/follow-up/delivery/reload flow.

A real graph failure was injected before saving a reconciliation effect: the correct invoice displayed Continue invoice processing above its draft, another selected invoice did not, and resuming completed the saved graph without another model call. The button disappeared afterward. JavaScript syntax passed. No live provider call, cloud mutation or deployment by assistant. Real browser pixel/viewport acceptance remains for the learner; DOM/CSS checks do not claim screenshot verification.

Next milestone remains the guided interviewer walkthrough, then visitor data editing last.
