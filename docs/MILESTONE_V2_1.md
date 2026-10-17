# V2.1 — Visitor conversations and persistent collection cases

This milestone gives each browser its own conversation and proposed collection status. It builds on the already-working current-portfolio preload. No new service, package or paid feature.

## Run it

1. Review/merge this milestone PR in the canonical o2c-collections-agent repository.
2. In VS Code terminal at the project root:

   ```powershell
   git switch main
   git pull origin main
   ```

3. Open [sql/007_visitor_cases.sql](../sql/007_visitor_cases.sql). Copy the entire file into the **existing project's Supabase SQL Editor** and run once. It is additive and may be rerun. Earlier SQL001–006 are prerequisites already used by the live app. Do not rerun seeds to erase your edits.
4. Render → existing service → **Manual Deploy → Deploy latest commit**. Existing cloud secrets stay in Render; none belong in Git or this conversation. No new cloud environment setting or pip install is needed.
5. Reload the website. You should see fresh invoice data immediately and the new Customer conversation panel. Start the agent, let it finish, select an invoice, then **Open collection case**.
6. The panel stores an **unsent reminder copy** when that invoice has a draft. Type a short customer reply, then **Save reply & classify**.
7. Reload without Start. The portfolio loads from current Supabase AR and your saved conversation/status reappears beside its invoice. Use another browser/incognito window: your conversation must not appear there.

For local use, restart your usual Uvicorn command from the repository root after pulling. To keep local case identity across Python restarts, put a private32+character `DEMO_SESSION_SECRET` in ignored `.env` (you can generate one locally with `python -c "import secrets; print(secrets.token_urlsafe(32))"`). Keep `PUBLIC_DEMO=false` for private local learning. Without a stable local secret, database rows persist but a new Python process cannot recognize the prior local browser cookie. Existing Render public deployment already requires a stable session secret; public cookies remain Secure/HttpOnly and expire after seven days.

## What actually happens

| Visitor action | Backend behavior | What it does not claim |
|---|---|---|
| Open page | Load fresh AR preview and this browser's saved cases | No new run/model call/email |
| Open collection case | Save originating completed-run invoice snapshot and optional unsent draft copy | No email sent or delivered |
| Save typed reply | Commit simulated reply, then call existing configured classifier once | No Resend received webhook |
| Classification succeeds | Save a proposed review status with evidence | No payment, committed promise or task |
| LLM off/capped/invalid | Save original text, visibly require manual review | No pretend AI classification |
| Retry same request | Return saved result by request UUID | No repeated model call |
| New run | Fresh AR run; reuse case for that invoice | No contact-history reset |

Real emails still use the existing owner-controlled Resend panel. The agreed next milestone will allow narrowly scoped visitor actions to send **real emails to the fixed project test inbox**, while only that visitor's message/status copy appears on the page. Website replies remain clearly simulated. We have retained Resend for that real transport.

## Read these files in order

1. `dist/app.js`: `refreshCases`, `renderCase`, `saveCase` render the conversation. All customer text is escaped; it never becomes executable HTML.
2. `backend/main.py`: three case API routes derive the browser actor server-side. Clients never choose another session key. Public case opening checks run ownership.
3. `backend/cases.py`: save-before-classify flow; existing language service reused. Reads/page loads never call the LLM.
4. `backend/language.py`: structured reply schema, literal evidence/date/amount validation, free-only provider routing and visible manual fallback.
5. `sql/007_visitor_cases.sql`: private tables, atomic insert/limits/dedup/status transitions. RLS and service-only RPC permissions preserve the backend boundary.

`collection_status` is separate from the invoice balance/lifecycle. A “paid” claim becomes **reconciliation required**, never “paid.” A promise is **proposed for review**, never scheduled automatically. A dispute creates a sticky **demo case hold**. This foundation does not change the owner's separate email permissions/hold state; that connection belongs in the scoped graph workflow.

Cases freeze the originating run snapshot. Editing source AR can change the current portfolio without rewriting the conversation's original financial context. The panel shows the originating date/run. One case per browser/invoice prevents a new run from losing contact history.

## Limits and failure behavior

- 12 cases/browser and500 globally stored cases;12 customer replies/case. These storage limits do not reset daily. There is no visitor delete/reset or automatic cleanup in this milestone.
- 20 replies/browser and120 globally per UTC day, enforced in SQL before classification. Existing model limits also apply: public8 attempts/browser and40 globally/day, including drafts and earlier classification examples; four draft calls can consume half a browser's allowance. Process cap remains20. Templates/manual review remain usable without provider requests.
- Browser identity is a cookie, not a verified person. Clearing it creates a new identity but does not bypass global limits.
- If processing stops after saving, the reply remains pending/manual-review. Same-request retry returns it without repeating a potentially spent model call. Durable automatic graph resume is **not** implemented yet.
- Missing SQL007 shows an actionable error in the conversation panel; the invoice preview and original run features still load.
- Free Render can sleep; this feature has no unattended worker and makes no exact-time scheduling claim.

## Your hands-on exercise

With LLM enabled and quota available, enter `We paid this invoice yesterday.` Verify the status is **Payment claim · reconciliation required**, the evidence says simulated customer reply, and open balance is unchanged. If the model is disabled/capped, expect **Reply needs manual review** instead; that is correct fallback behavior.

Reload, select the same invoice and confirm the text is still there. In VS Code, change the visible `reconciliation_required` label in `caseLabels` inside `dist/app.js`, reload locally and observe the label change while the stored message stays unchanged. This connects UI rendering to persisted backend state.

Next milestone: LangGraph with durable Supabase checkpoints, Review actions/Autopilot demo modes, approvals/resume and narrowly authorized fixed-recipient real Resend sends. Later: documents/dispute evidence/payment reconciliation/promise expiry. No new arbitrary-recipient email or paid IVR in the free default.

Implementation verification:112-test full regression and final15-case targeted suite passed on Python3.12.14. Local HTTP/SSE/frontend checks covered initial preload, case creation/reply/reload/privacy/HTML escaping and the existing owner mock-email loop. Providers were mocked; these checks do not prove live provider delivery. One existing Starlette/httpx deprecation warning remains.
