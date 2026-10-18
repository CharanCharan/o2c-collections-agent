# V2.20 — More reliable LLM draft formatting

The old Groq-compatible schema omitted minLength/maxLength while Python enforced them locally. The prompt asked for short prose but did not specify the actual limits. This mismatch could produce valid provider JSON that failed local validation. The previous live response is not retained, so its exact failing field cannot be proven.

## Changes

- Share opening 10–180, request 10–240 and closing 5–100 character limits between local fields, prompt instructions and schema descriptions. Descriptions survive the existing portable schema conversion.
- Specify the exact output keys, string types, exact fact copying and concise examples in the prompt.
- Explain schema rejection safely, for example: `LLM draft format rejected: closing must contain 5–100 characters. Template used; review required.` Missing fields, unexpected fields and invalid types also receive specific reasons. Never expose raw Pydantic input, model prose or unexpected key names.
- Keep exact invoice-fact matching, prohibited-claim checks, quotas, no automatic retries/failover and truthful template fallback. A model can still fail; this is improved guidance and observability, not a guarantee.

Prompt: collections-language-v2. Validator diagnostics: collections-language-checks-v2. Backend app v2.20; existing UI workflow-20 renders the saved reason without a frontend change. No new SQL, packages, environment variables or quota changes.

## Validation

47 tests passed: `tests/test_draft_format.py`, `tests/test_llm_providers.py`, `tests/test_milestone_4.py`. Includes portable prompt/schema constraints, short/long/wrong-type text, no untrusted-value leakage, persisted HTTP-200 overlength fallback with usage/audit retained and no extra model request, valid drafts/replies, provider errors and existing fact/prose controls. Integration uses mocked HTTP providers and isolated local SQL; no live LLM/email calls.

## Your next steps

1. Merge this PR and deploy latest main on Render. Health should show app_version v2.20; no setting changes are needed.
2. Existing saved cases retain their original drafts and reasons. Use the established Incognito workflow for a new case, within shared model/email budgets; do not reset the database or recreate cancelled fresh-demo functionality.
3. Run collections in Review & approve mode to inspect new drafts before sending. Check their audit prompt_version is collections-language-v2. A successful draft is labelled as checked LLM output; a failure now gives a safe field-specific reason when the schema is the problem.
4. If a failure persists, share that safe reason and invoice ID. Do not share credentials or private provider payloads. Caps, timeouts, incomplete output, fact mismatch and prohibited prose continue to have their own reasons.

Prior saved drafts are not regenerated, and deploying does not reset shared quotas. Live acceptance remains the owner's check after deployment.
