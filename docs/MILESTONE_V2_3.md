# V2.3 — Readable three-column workspace

This is a UI milestone before the LangGraph/control-mode work. It uses the existing backend and saved state; no SQL, dependency or environment changes.

## What changed

- Wide desktop layout: **AR work queue | Customer, email draft and conversation | Live agent execution**. Execution stages and actual backend events are visible without opening a bottom toggle.
- The workspace uses the available window width with24px outer gutters. Body text is16px; draft/customer text15–22px; metadata has a13px minimum. No browser zoom is needed to increase the original8–11px text.
- **Previous runs** is beside Start agent. Open the menu, choose a saved run, then Open run. It plays saved evidence without starting another run or sending email. The menu closes after opening a run, outside click or Escape.
- **Overdue / Preventive** buttons replace the stage dropdown. Overdue is the default. Each button shows the count in that stage; high-urgency filtering remains separate and is unavailable for prevention.
- The current stage selection survives Start and saved-run playback. Portfolio totals always cover the full source snapshot, not just the visible queue. With all seed scripts, expect6 overdue rows or3 preventive rows, with total open balanceUSD431700.
- The old **Review a synthetic reply example / Classify example** panel is removed. That panel classified a hard-coded fixture, not a received email. Use the customer conversation panel to type a clearly labelled simulated reply instead. Existing legacy example APIs/history remain compatible.

On screens1180px or narrower the layout becomes two columns with execution below; at760px it stacks. Live execution remains expanded at every width. The AR table can scroll inside its panel on narrow screens so its readable text is retained. On wide desktops the execution column is sticky and independently scrollable.

## Apply it

1. Review and merge the PR in the canonical repository.
2. In the local project terminal:

   ```powershell
   git switch main
   git pull origin main
   ```

3. Refresh the local app, or use Render → **Manual Deploy → Deploy latest commit** for the public site. Existing Supabase/email setup from V2.2 is retained. No new SQL or pip installation.
4. Confirm the three columns at normal desktop zoom. Click Preventive, then Start agent: the selected queue should remain preventive while the execution panel shows the actual run. Switch back to Overdue to inspect a sendable draft.
5. Open Previous runs beside Start and reopen a completed run. The saved stages/events should appear without another run or email send.

## Find the code yourself

- `dist/index.html`: order of the three columns, header Previous runs menu and filter buttons.
- `dist/styles.css`: all styling now lives in this readable file instead of several minified inline style blocks. `.grid` controls columns; `.draft-body` controls draft readability; the media queries control smaller screens.
- `dist/app.js`: stage filtering/counts, selected-invoice rendering, saved-run playback and real SSE events. The removed fixture classifier no longer has a UI handler.

Exercise: locally change `.draft-body` font-size from15px to16px in styles.css. Reload and check that only the reminder text grows. This CSS change does not change model, finance or email behavior.

The script/style URLs carry a new UI version so a redeploy fetches the updated assets. Saved runs and cases stay in Supabase.

## Validation and next milestone

23 preview/case/email regression tests passed. Actual local HTTP/SSE with cookie-aware frontend DOM checks passed initial portfolio, stage counts/buttons, filter persistence, visible execution placement, saved-run menu playback, removal of fixture controls, computed typography, send/verified callback status, typed reply and reload restoration. Providers were mocked; no real email or model call was made by the assistant. Responsive CSS rules were reviewed; a real Chromium viewport/screenshot check was unavailable because its browser download failed, so pixel-perfect browser rendering is not claimed.

Next: LangGraph with durable checkpoints, limited/autopilot controls, real send-tool decisions, approval/resume and automatic response handling. Keep this as the dedicated UI PR in the agreed one-milestone-at-a-time delivery workflow; do not label the existing linear run as LangGraph already.
