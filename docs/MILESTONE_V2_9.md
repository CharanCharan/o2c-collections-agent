# V2.9 — Invoice next step and horizontal processing

Merge/pull, manually redeploy the existing Render service, then hard-refresh. No new SQL, packages, accounts or environment settings. Existing SQL012 remains a prerequisite for previous promise features. No backend policy/model/provider changes.

## What changed

Portfolio processing is a full-width horizontal strip above the invoice queue. The six stages remain actual saved backend events (load, validate, urgency, prediction, prioritization, drafting). Horizontal overflow supports narrow screens. The detailed portfolio event log is collapsed below that strip. The table now uses the full landing workspace width; the redundant right sidebar is removed.

Selected invoice processing belongs inside the invoice popup, under its reply/evidence area. It always names the selected invoice ID, including invoices with no case/graph history. It displays the latest 12 recorded backend activities as horizontally scrollable cards with recorded status/time, not an invented universal graph path. Different replies invoke different branches. Opening another invoice replaces its activity. Popup open performs a read-only case refresh; polling also refreshes while the popup stays open, even without an active portfolio job or pending mail. This does not invoke the graph, send mail, classify text or make the agent always-on.

The old sidebar was outside the modal and its empty-state heading did not identify which invoice was selected. The new placement and explicit identity make the relationship visible and distinguish missing graph history from a stale display. An interrupted portfolio run can leave some invoices without graph steps; those invoices honestly say they have not been processed. Resume the portfolio from Run overview in that situation.

## Next step area

Every selected invoice has a consistent area above its details/email with an explanation and the applicable action:

| Saved state | Action |
|---|---|
| Initial reminder approval | Send reminder |
| Missed-promise follow-up approval | Send follow-up |
| Supported promise approval | Record payment promise / Leave for review |
| Interrupted invoice invocation | Continue invoice processing |
| Explicit email retry allowed | Existing specific retry action |
| Dispute hold | View supporting evidence; no chase/send |
| Waiting for delivery/reply/payment date | Explanation; no generic Run button |
| Unprocessed invoice | Return to queue and use Run collections |

Top send/retry reuses the existing Send button handler and its computed eligibility. Promise approval and resume reuse their existing endpoints/checkpoints. A send remains available beside the draft as a shortcut. Actions disable while busy; disabled/unconfigured email remains clearly explained. No new single-invoice start API or automatic approval path is introduced. Selected case reference is retained. Promise approval moved from the lower reply panel into this consistent top area; supporting evidence stays beside the reply.

## Hands-on checks

1. Before a run, open two invoices. Each popup identifies its own invoice and says no processing history; no graph/email is triggered by opening.
2. Run Review & approve. Open an invoice with a pending email: Next step explains the saved draft and offers Send reminder. Use the top button and confirm provider status updates without a second email.
3. Switch invoices. Confirm Invoice processing names the new invoice and shows that invoice's saved activity.
4. Submit a suggested promise reply. Record payment promise should appear in the top Next step area; approve it there. The waiting explanation should replace the approval.
5. In an interrupted individual invoice, Continue invoice processing remains at the top and resumes the saved checkpoint. It does not rerun the portfolio.
6. For a dispute, View supporting evidence moves focus to the evidence section. It does not resolve a dispute or send a reminder.
7. Resize in your native browser: portfolio stages and invoice history scroll horizontally; table remains bounded and full width; email/reply remain side by side on desktop and stack on mobile.

## Validation and boundaries

10 isolated SQL/API/reporting regression tests passed with mocked providers. Local HTTP/SSE/cookie-aware JSDOM journey passed full-width queue/horizontal flow, invoice-specific history inside dialog, unprocessed identity/empty state, switching invoices, top Send reminder, top promise approval, interrupted-case resume, delivery callback, reply reconciliation, promise/date/follow-up/reload and unchanged source. JavaScript syntax passed. No live provider calls or cloud writes/deployment by assistant. DOM/CSS checks do not establish actual pixel layout or native focus trapping; Charan validates those after deployment.

Next remains guided interviewer walkthrough, then visitor editing. Source AR, frozen run reports, ownership, metered budgets, deterministic financial tools and saved modes are unchanged.
