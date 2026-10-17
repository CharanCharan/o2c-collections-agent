# V2.7 — Queue-first workspace and invoice dialog

The landing workspace now contains the invoice table and Collections activity. Customer/email/reply details open on demand in an invoice dialog. This gives the queue more horizontal space while keeping collection processing visible.

## Apply it

Review/merge, pull main and refresh locally or manually deploy the existing Render service. No new SQL, Python/Node dependency, environment setting or account. Existing SQL012 still supports promise processing. No backend/API or model/email policy changes.

## Visitor journey

1. Open the site: current AR and saved activity load as before. The invoice dialog stays closed.
2. Read the hint above the queue: select any invoice row to view its reminder and customer reply side by side. Each row also has a visible **Open invoice** button, hover/focus feedback and a keyboard-accessible action.
3. Click anywhere on a row or activate its Open invoice button. A titled invoice workspace opens for that customer/invoice. Opening it is read-only: no run, case creation, model call or email is triggered.
4. The left pane shows invoice details, saved case reference, conditional Continue invoice processing and the reminder/follow-up with its real send status.
5. The right pane puts **Simulate customer reply** and its composer first, followed by case status/actions and expandable Message history. Unsent composer text is retained in browser memory when closing/reopening or switching invoices; a successfully submitted reply clears it. This unsent text is not persisted across page reload.
6. Use the existing Send reminder/Send follow-up, Record payment promise or Send simulated reply actions explicitly. They keep all existing ownership, approval, validation, quota and idempotency behavior.
7. Use **Back to queue**, Escape or the backdrop to close. Focus returns to that invoice's Open invoice button, even if polling has rerendered the table. Opening another row does not discard the queue's scroll position or start a new collections run.

Before running collections, the dialog shows available source details and explains that Run collections prepares reminders/enables replies. No send or reply is fabricated. After a run, saved case data appears inside the same dialog.

## Layout and accessibility

Desktop landing layout is wide AR queue | Collections activity, with bounded internal scrolling and all eight existing table fields. Horizontal controls remain for narrower widths. At smaller widths the activity panel stacks below the table.

The dialog uses native HTML dialog modality, a labelled heading, a visible Back to queue control and keyboard actions. Its desktop body has two independently scrolling panes so the reply composer is directly visible beside the email. On mobile they stack within the dialog. Closing does not stop an already-triggered backend job; reopening reads the saved results.

Row guidance is explicit rather than relying on hover alone: queue instruction, visible Open invoice control, pointer/focus styling and dialog accessibility attributes. The main selected-invoice activity still follows the selected row, while the dialog is opened only by a row action—not automatically on initial load, polling or saved-state restoration.

## Website icon

`dist/favicon.svg` supplies a custom teal invoice/collection-arrow mark. `dist/favicon.ico` provides16/32/48/64pixel raster fallbacks. Both are served locally by the existing /assets mount, referenced in the page head, and the same SVG is used in the header brand. There is no external icon service/font or image dependency. Asset versions are updated; browser favicon caches may need a hard refresh after deployment.

## Code map

| File | Change |
|---|---|
| `dist/index.html` | Two-column landing, native invoice dialog, queue instruction and favicon links |
| `dist/invoice-ui.js` | Explicit opening/closing, selected-invoice title, focus return, scroll lock and in-memory unsent replies |
| `dist/app.js` | Row action, dialog detail rendering and composer-first conversation/history layout |
| `dist/styles.css` | Wider queue, dialog desktop/mobile layout, click hints and brand icon |
| `dist/favicon.svg`, `dist/favicon.ico` | Locally served vector icon and raster fallback |

The new invoice-ui.js loads before the existing followup-ui.js/workflow-ui.js/app.js classic scripts. Existing DOM IDs and server endpoints are preserved; customer panels have moved into the dialog instead of being duplicated. Header Portfolio overview/Payment promises/run history remain available from the queue.

## Verification

8 preview/email API/SQL regression tests passed with mocked providers. Local HTTP/SSE/cookie-aware JSDOM checks covered two landing columns, dialog initially closed, row-open cue, correct selected title/case, Escape/focus return, no run on opening an invoice, in-memory unsent draft retention, all eight fields, interrupted-case continuation, promise/date/follow-up/send/signed-delivery/reload flow and SVG/ICO asset responses. JavaScript syntax passed. No live provider call or deployment by assistant. These are DOM/CSS checks; actual browser pixel/viewport and native focus-trap acceptance remain learner checks.

Exercise after deployment: open an invoice before Run collections and confirm it makes no action claims. After a run, type a reply without sending, close and reopen the same invoice, then submit it. Confirm the correct invoice/case updates and Back to queue returns focus/position to the queue.

The next feature milestone remains a guided interviewer walkthrough, then visitor data editing last.
