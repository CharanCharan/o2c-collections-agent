# V2.13 — Two-page workflow guide and LLM transparency

Merge/pull, manually deploy latest main and hard-refresh. No new SQL, packages or environment settings. Previous SQL013 remains required for LangGraph; its live application/retry acceptance is still pending unless Charan confirms it. Health app_versionv2.13/ui_versionworkflow-15.

**How it works** beside the title opens a read-only dialog with exactly two pages: Entire workflow and Agentic workflow. Each page maps short business steps to their backend technology. The editable source is `dist/HOW_IT_WORKS.md`, served by the existing static mount. Edit its text/tables and reload; keep exactly one standalone `---` divider between the two pages. No separate build or Markdown package is needed.

The small renderer supports the headings, paragraphs and tables used by this file and escapes all text; it does not execute HTML. Opening it fetches only this static file and makes no run, model or email request. Native dialog, tabs, Previous/Next, keyboard arrows/Home/End, Escape/backdrop close and focus return are supported. A Markdown source link is available in its footer. Mobile tables scroll inside the guide.

The main synthetic-data notice now mentions optional agent LLM calls and shows current server configuration: enabled provider/model, disabled/templates/manual review, missing key or blocked configuration. This is readiness information, not proof that a model call occurred. Drafts and saved reply classifications show separate per-action audit evidence: completed call, attempted call with fallback/review, explicitly no API call, or missing legacy evidence. Deterministic follow-up templates explicitly show no LLM call. Financial tools and trained risk inference are not labelled as LLM calls.

During validation, an existing display race appeared: the case-job stream could report completion before the older preparation stream delivered its last draft event. The strip now treats an active/completed case job as evidence that preparation already completed, preventing an older draft-start event from regressing the display. No business execution or pacing changes.

Validation:8 preview/email isolated SQL/API tests passed with mocked providers. Local HTTP/SSE/cookie-aware JSDOM journey passed guide placement/two pages/technology tables, keyboard navigation, Escape/focus return, read-only opening/no new run, disabled-mode label and HTML escaping, actual draft call evidence, plus prior live-flow/top approval/log/send/delivery/recovery/reply/promise/date/follow-up/reload/source-preservation journey. JavaScript syntax/Python compile passed. No live provider/cloud changes/deployment or native pixel/focus-trap acceptance claimed.

Code: dist/HOW_IT_WORKS.md, guide-ui.js, index.html, app.js and styles.css. backend/main.py changes version metadata only. Existing provider keys, budgets, case ownership and financial policies are unchanged.

Next: confirm checkpoint repair and deployment; guided interviewer walkthrough; visitor editor last.
