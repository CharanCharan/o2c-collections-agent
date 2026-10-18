# V2.22 — Header alignment and demo LLM allowance

## Header fix

The source link now reads **GitHub**, with a smaller footprint and the same accessible new-tab label. The desktop header uses a grid: title/guide/GitHub on the left and collection controls aligned at the top right. The old <=1400px rule that forced the run controls onto a full-width row below the title is removed. At mobile widths <=760px, the groups stack while the controls remain right-aligned.

Run overview, Payment promises and Collections run history panels use fixed positioning, clamped to the current viewport with bounded internal scrolling. Position is recalculated on open, resize and page/visual-viewport scroll, avoiding the previous offscreen popup. The original native disclosure controls, Escape/outside-click handling and business actions remain.

## Why the quota message appears

“Daily demo LLM quota reached” is an application-side Supabase reservation limit. Before optional SQL016, it is eight attempts per browser and forty shared attempts per UTC day, whichever is reached first. Failed model/output-validation attempts also consume reservations. Render's LLM_MAX_CALLS_PER_RUN and LLM_MAX_CALLS_PER_PROCESS are separate limits and cannot raise this database allowance. Groq's provider/account limits are separate too.

The UTC day resets at 05:30 India time. Incognito creates another browser session but does not reset the shared global counter. Existing saved template drafts retain their historical reason; changing a limit does not regenerate them.

## Optional allowance increase

To allow more testing, run `sql/016_demo_llm_budget.sql` in Supabase after SQL015. It sets **40 attempts per browser / 100 shared per UTC day**. This is optional for the UI fix. The script is additive/repeatable, does not clear counters/history and leaves Start, email limits, free-only routing and provider account settings unchanged.

For a later adjustment, edit the two numbers in `ca_llm_budget()` near the top of that script and re-run it. Both reservation enforcement and public health read the same definition. Keep positive values and browser allowance <= shared allowance. This remains an app-side cap; it does not increase Groq's account limits or verify billing tier. There is no automatic retry or paid fallback.

After deploying this code, `/api/health` reports the actual SQL daily caps when SQL016 is installed; without it, the original 8/40 values remain. App version v2.22 / UI workflow-22. Existing per-process caps remain in place; a process restart does not reset database daily usage.

## Deploy and check

1. Merge and deploy this PR; no SQL is needed just for the header fix.
2. Optionally run SQL016 to increase the application daily allowance. SQL015 remains the prerequisite for Draft with AI itself.
3. Hard-refresh. Confirm collection controls are top-right on desktop and each menu stays within the viewport at your usual zoom and a narrower window.
4. For an eligible unsent case, choose Draft with AI to request a new draft; old fallback drafts are not automatically replaced. Inspect a new failure reason if another cap/provider limit applies.

## Validation

20 tests passed across tests/test_demo_llm_budget.py and tests/test_milestone_6.py. They cover repeatable optional migration, preserved usage, 40/browser and 100/shared enforcement including owner/webhook actors, unlimited Starts, private settings RPC and accurate old/new health values. Providers are mocked and PostgreSQL runs locally in PGlite.

Seven mocked geometry cases passed for desktop/mobile, short viewport, offscreen anchors and visual-viewport offsets. Actual local HTTP/cookie/SSE JSDOM AI-draft journey passed again (three mock LLM calls, one mock email), preserving drafting/review/send/reload behavior. HTML/JS/Python checks passed. A native Chromium download failed because the archive was truncated, so no native screenshot/pixel/focus or real viewport-layout acceptance is claimed; the owner should confirm after deployment.

No actual model/email calls, live Supabase changes, deployment, new runtime packages or environment changes were performed. Saved invoice cases and Incognito behavior remain; Start fresh demo stays cancelled.
