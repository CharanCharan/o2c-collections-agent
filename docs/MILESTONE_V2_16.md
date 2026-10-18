# V2.16 — Remove popup coaching banner and clarify saved drafts/modes

The Suggested test banner is removed from every invoice popup. How it works → Try a scenario retains its invoice explanations and saved-state suggestions. Open scenario still opens the exact invoice, focuses the reply composer and shows a short notification. All invoices retain the suggested-reply/category picker; inserting text remains read-only.

A saved case retains its original draft and approval mode. Enabling the LLM does not rewrite old drafts, restart saved cases or authorize a second email. A new run can contain fresh LLM results while its reused case still shows the original template; that is preserved business history rather than a failed inference. The invoice now shows its saved mode beside the case reference, and template drafts show their recorded reason directly under the call evidence. LLM drafts are labelled Facts checked; whether sending needs approval depends on actual saved mode, not that generation badge. Deterministic promise follow-ups remain explicitly templates/no LLM.

New eligible drafts attempt the LLM only within configured application/provider limits. A cap, unavailable model, timeout or invalid response can produce a clearly labelled template fallback, even when LLM is enabled. Draft validation and tool evidence remains the source of call status/reason; no template is relabelled as LLM output.

Current verified modes:

- Review & approve: eligible reminder waits for Send reminder; no mail during the initial collection run.
- Automatic processing: sends eligible newly created cases without a click, up to the existing three-new-reminder allowance per run and global email limits. Accepted means Resend accepted the request, not confirmed delivery.
- Existing cases retain their saved mode, approvals, holds and send receipts. Choosing Automatic for another run does not convert a saved Review & approve case or resend accepted email.
- Disputes, missing contacts, delivery uncertainty and other policy restrictions still prevent blind sending. Automatic is not a promise that every invoice sends an email.

For a clean acceptance run, use one fresh private browser session after the current LLM configuration is ready. Test Review & approve and Automatic in separate browser sessions so their saved case modes do not mix. Do not delete the database, reset budgets or clear mail receipts. Enabling LLM alone is not a clean-case reset; Reset page does not clear cases. No live provider requests or database reset are performed by this milestone.

UI/static/version change only: app v2.16 / UI workflow-17. Existing SQL014 remains required. No new SQL, environment values, dependencies, mode conversion, automatic draft regeneration or changes to provider/email budgets. After review/merge, pull, deploy latest main and hard-refresh. Validation:43 targeted isolated SQL/API/actual LangGraph tests passed, covering fresh LLM limited/automatic runs, retained draft/mode immutability, mail deduplication and follow-ups. Actual HTTP/SSE/cookie-aware JSDOM journey passed no banner, all24 reply pickers, guide navigation, template-reason helpers, saved mode, approval/send/delivery/recovery/payment/promise/follow-up/reload/source preservation with mocked providers. First HTTP journey hit a local fetch failure during send; full rerun passed. JS syntax/Python compile passed. Native pixel/focus-trap acceptance remains manual; live behavior/private session data cannot be verified from this workspace.
