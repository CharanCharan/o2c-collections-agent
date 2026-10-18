# V2.17 — Start fresh demo

Use **Start fresh demo** beside Run collections, then choose Run collections and a mode. This gives the browser new invoice cases with no prior replies, approvals, promises, reminders or saved case mode. The source AR portfolio still loads before Start. New draft generation uses the current LLM configuration and existing limits; a fresh demo cannot guarantee LLM success or refill its quota.

The action does not start the agent or send email. The next explicit collection run creates fresh cases; Automatic can then send up to three newly eligible reminders to the configured project test inbox under the existing global mail limit. Older emails remain real emails and are not recalled. A new case/run has new send intent; retrying an existing case still retains its original idempotency behavior.

We retain LangGraph checkpoints within a workspace so reply processing and approvals can continue correctly. This is a fresh workspace, not removal of graph persistence or deletion of Supabase data. Old runs/cases/checkpoints/mail receipts remain stored; an ordinary public browser's new workspace cannot access them using old IDs. Original source invoices, shared payment scenario evidence and global counters remain. The new workspace's simulation clock starts at the source base date. Global case capacity remains finite; this does not add infinite history storage or an editor for source AR.

## Backend

POST `/api/demo/fresh` checks database job state, owned case locks, active HTTP actions and tracked background tasks. It rejects reset while work is active. Stored interrupted states without active work may be left behind. On success it rotates the signed browser workspace ID, clears temporary owner login and preserves a separate stable browser budget ID. Old cookies without a budget ID remain compatible. Public LLM budget reservations use the stable budget identity; run/case ownership uses the new workspace identity. No SQL migration or changes to quota values are needed.

Cookie responses are sent only when the session is new or changed, so a late read-only response from the old workspace cannot replace the new cookie. Existing signing/Secure/HttpOnly/SameSite, expiry and origin checks remain. RunService tracks the owner of each analysis/agent/follow-up task so a reset cannot overlook active background work merely because another newer job completed.

The website reloads after success, stops old event streams and loads a populated portfolio with empty current case/run history in normal public mode. Errors preserve the current workspace. The old footer Reset page action is now called Clear view; it still only clears the displayed run and is distinct from Start fresh demo. Private/local operator history may still list its existing database-wide run archive; normal public history is scoped to the new workspace.

## Deploy and check

Merge/pull, deploy latest main, hard-refresh. No new SQL, dependency or environment setting; existing SQL014 remains required. Health app v2.17 / UI workflow-18. Do not truncate tables or rotate the session secret just to restart a demonstration.

1. Finish current processing. Click Start fresh demo; the table should reload populated and prior invoice conversation/run state should disappear.
2. Run with the current LLM setting in Review & approve mode; review and send one reminder explicitly.
3. Start fresh again and choose Automatic for the next run. Old review-mode cases should no longer interfere with new cases. Email/model allowances still apply.
4. Verify that reload within the current demo retains its own replies/approvals. Use Start fresh demo only when you want another independent walkthrough.

Validation:178 full regression tests passed before the final background-task ownership change;25 targeted public/fresh/SSE tests and all4 final fresh-workspace tests passed afterward. The actual HTTP/SSE/cookie-aware JSDOM journey passed the fresh button/API/cookie/reload flow, populated portfolio with empty case/public run history and original demo date, old-case access denial and existing approval/send/delivery/recovery/reply/promise/follow-up/reload checks. Providers were mocked (2 email/6 model calls). JavaScript syntax and Python compilation passed. Automated providers are mocked; no live model/email call, cloud database change, deletion, deployment or merge by the assistant. Native browser visual/layout acceptance remains manual.
