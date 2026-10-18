# V2.17 — Demo inbox screenshot in How it works

User cancelled the proposed Start fresh demo feature and chose the existing Incognito approach. This milestone contains no fresh-demo button, endpoint, cookie/budget identity changes, background-task tracking or database cleanup. The unfinished fresh-demo-workspaces branch is not part of this release and must not be merged without a new request.

The first How it works page now has a small clickable image icon beside “Send real email to the demo inbox” in the Send and respond row. It opens the user's supplied Gmail screenshot in a new tab at its original size. The image is a static example of received demo emails, not a live inbox or a delivery status for the current run. Opening it starts no run, model call or email action.

The unchanged uploaded PNG is served as `dist/demo-email-inbox.png`. `dist/HOW_IT_WORKS.md` contains the marker `[Inbox screenshot](/assets/demo-email-inbox.png)` in the relevant table cell. The existing escaped Markdown renderer recognizes only this exact marker and inserts an accessible image-icon link to that fixed local asset. It does not enable arbitrary Markdown URLs or raw HTML. The icon supports keyboard focus and identifies the new-tab behavior; `noopener noreferrer` is set.

App v2.17 / UI workflow-18. Backend change is version metadata only. No new SQL, packages, environment settings or service integrations. Previous SQL014 remains required; sessions, checkpoints, provider limits, mail receipts and approval/automatic behavior remain unchanged.

After review/merge: pull, deploy latest main, hard-refresh, open How it works → Entire workflow and click the image icon beside the demo inbox text. Verify the full screenshot opens. Existing normal browser cases remain saved; a new Incognito/InPrivate session provides a fresh walkthrough.

Validation:4 preview/saved-mode SQL/API regression tests passed. Actual HTTP/SSE/cookie-aware JSDOM verified icon placement, accessible new-tab link, fixed local asset, image/png response and byte-for-byte original PNG, escaped HTML and no arbitrary URL rendering, absence of the fresh-demo button and the existing full scenario/approval/email/delivery/recovery/payment/promise/follow-up/reload flow with mocked providers. JS syntax/Python compilation passed. No live model/email calls, database changes, merge or deployment by the assistant. Native pixel/browser visual acceptance remains manual.
