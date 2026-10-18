# V2.23 — Edit drafts and revise them with added context

## What was missing

The previous redraft request sent invoice facts and tone/wording preferences, but omitted the existing draft. Its output schema also had no place for added factual context. It could therefore return familiar generic prose rather than revising the displayed reminder. That limitation is corrected here; no live model response was captured to diagnose the exact previous attempt.

## Revised AI flow

Redraft with AI now sends the current saved subject/body plus your revision request to a separate `revise_reminder` task. The prompt asks it to preserve useful content, apply requested changes and incorporate relevant added context. It does not use the initial-draft canned examples. The subject remains unchanged; use manual editing to change it.

The structured result has the normal validated opening/request/closing plus additional_context, context_quotes and change_summary. Additional context may contain information such as contact names, previous conversations, dates or a PO reference. Literal excerpts from the new request or existing body must support it; new numeric/date tokens must occur in that evidence. Existing financial/policy checks still reject unsupported payment, route, discount or legal claims. Python inserts the exact protected invoice-facts sentence. Names/meaning are not mathematically verified: added context is labelled **AI revised · Review context**, with a visible summary, and requires review.

If the returned body is identical, the app explicitly says the model returned the same draft and saves no update. It does not report a successful revision. Unsupported/invalid output also leaves the existing saved draft untouched. One explicit call, no automatic retries/failover and the existing durable model budgets remain. Prompt and validator versions are v3; model obedience is not guaranteed.

## Manual editing

**Edit draft** opens subject and body fields with **Save changes** and **Cancel**. The read-only preview remains the normal view. Sending and AI revision are disabled while manual editing is open. Cancel restores the preview without a write or model call; Save atomically replaces the owned case draft and draft-preview message. The badge becomes **Human edited · Review**, and the edit audit says no model call was made. Manual prose is human-authored and is not presented as fully AI-validated.

Keep the invoice-facts sentence unchanged and present exactly once, and retain this invoice ID in the subject. Subject/body are plain text with maximum lengths 200/4000. Sender and recipient stay server-controlled. These checks do not validate every human-authored claim in the rest of the message; review it before sending. The source AR and original portfolio run are unchanged.

Save compares the exact original draft the editor opened. A newer AI/manual revision, send intent, reply or hold prevents a stale overwrite. A repeated request UUID/payload returns its saved result rather than saving twice, even after restart. An active AI reservation blocks manual saving; stale reservations are retired so late results cannot overwrite a human edit. The existing graph approval remains intact, and the later Send reminder sends the saved subject/body.

Only unsent eligible initial reminders can be edited/revised. Sent or uncertain intents, follow-ups, replies, disputes and active processing remain read-only. Unsaved manual text is held in browser memory when navigating invoices; a reload restores the saved draft, not unsaved edits.

## Required setup

1. Apply `sql/017_manual_draft.sql` in Supabase after SQL015. SQL016 remains optional for the increased daily allowance; SQL017 neither installs nor resets it. The migration is additive/repeatable and preserves existing data, checkpoints and sent mail.
2. Merge/pull this PR and deploy latest main. No new packages, keys, environment values or quota changes.
3. Hard-refresh. Health should show app v2.23 / UI workflow-23 and `draft_edit.ready: true` / schema17. Without SQL017, Edit draft is disabled with a setup hint; the AI revision correction still uses existing SQL015.
4. Open an eligible unsent case in Review & approve. Edit and Cancel, then Edit and Save. Confirm Human edited and the updated preview.
5. Redraft with AI: “We spoke with Priya. Mention purchase-order reference PO-7781 and ask for confirmation.” Inspect the added context and change summary, then review before Send reminder.

## Validation

112 backend tests passed across revision/edit, AI drafts, formatting, providers/M4, graph/sending, optional budgets and public mode. After refining context retention/rendering and SQL request checks, all33 targeted revision/edit/AI/formatting tests passed. Coverage includes prior saved draft in the request, new/retained source context, invented numbers/unsupported context rejection, explicit unchanged output, manual save with LLM disabled, replay/restart, protected facts and subject identity, stale edits, ownership/overrides, active/stale model reservations, repeatable/private migration and missing setup.

Actual local HTTP/cookie/SSE JSDOM journey checked Cancel preservation, no-call manual Save, disabled send/AI while editing, saved human content sent to the model, visible Priya/PO context and summary, unchanged-result feedback, edited provenance, exact sent subject/body and reload persistence (two mock LLM calls, one mock email). The prior AI/lost-response UI journey also passed (three mock LLM calls, one mock email). JS/Python/HTML checks passed. Providers are mocked and PostgreSQL is local PGlite; no actual model/email calls, cloud database migration or deployment. Native pixels/focus and live model acceptance remain owner checks.

The established Incognito/session approach remains. No fresh-demo/reset feature or automatic re-generation of historical drafts is added.
