# V2.10 — Finish the portfolio scan and report invoice exceptions

## Live investigation

Read-only checks on 2026-10-18 IST found the public Render URL serving workflow-6 assets, while PR19/main uses workflow-11. Live health returned 24 invoices, graph/email ready, templates-only language, and no newer followups field. Therefore the public service was not running the latest merged code at investigation time. This check made no live run, email, model call or database mutation.

The visitor's existing interrupted job is browser-owned; a fresh read-only HTTP session cannot read it. Its older implementation retained only a generic exception message. The exact original exception cannot be established from these public checks. Do not claim a specific live database/server failure was proved. Local fault injection did prove the code-level reliability issue: any exception in the invoice loop previously abandoned the remaining invoices and labelled the whole job interrupted.

## Apply and verify the actual deployment

Merge/pull this PR, then in the existing Render service manually deploy the latest main commit. Confirm the deploy log names that commit. Hard-refresh the browser.

Open `/api/health`: app_version must be `v2.10`, ui_version `workflow-12`, workflow.ready true and followups.ready true after existing SQL012. If those fields are absent, the deployment is older. A healthy old `/livez` does not prove the latest code is deployed. No new SQL, Python/Node package, account or environment variable. Existing SQL009–012 remain prerequisites.

## What changed

1. A case-specific error is saved against that invoice and the loop continues through the remaining source invoices. Terminal scanning has status completed, with explicit processed/total, attempted and failed counts. UI says Processing finished — N invoices need review when failures exist; it never counts failed invoices as successfully reviewed or invents their actions.
2. Run overview lists failed invoice IDs, a safe message, phase, operation when available, exception type and error reference. Needs-attention counts and queue status include unfinished cases. Supabase adapter attaches safe operation/category metadata; raw SQL/provider/exception bodies and keys are not returned or logged. Server logs contain correlation ID/category/invoice/phase.
3. Retry failed invoices reuses the existing job endpoint, mode, report baselines and automatic authority. Completed entries are skipped, failed entries retried through existing case/checkpoint paths. It does not automatically retry LLM/email providers or expand the three-email authority. Accepted messages retain their existing deduplication/uncertainty safeguards.
4. A job-level load/save/database failure or server cancellation still leaves genuine unfinished work. The UI says Processing stopped — recovery required and shows saved diagnostics, rather than falsely reporting complete. Recovery preserves partial results. Older records explicitly lack detailed diagnostics. The after-run error handler no longer replaces an existing progress report with a generic error-only object.
5. Portfolio processing moves below the invoice table into collapsed Processing details. Horizontal stages and nested event log remain available there; invoice-specific history stays in the invoice popup. Run overview beside Run collections is the business progress/results control. Assets workflow-12.

No automatic provider retry, restart scheduler, worker service, paid infrastructure, budget change, source AR mutation or live deployment by assistant. Free-host process shutdown can still stop in-flight work; it is not honest to promise completion through arbitrary outages with this POC architecture.

## Hands-on exercise

- Deploy and verify the version fields first. These distinguish an undeployed fix from a new runtime failure.
- Start a new Review & approve run. Run overview should show all successfully processed invoices and their saved results. Pending send approval is an expected invoice outcome, not a job failure.
- If an invoice fails, other invoices should still finish. Expand Review processing issues, inspect the affected operation/reference, correct the configuration/data issue and use Retry failed invoices. Do not repeatedly send an uncertain email outcome.
- Existing older interrupted jobs can use Recover unfinished processing. Older successful work is retained; old untracked work remains labelled partial rather than reconstructed.
- Check that Processing details is collapsed below the table, and that invoice popup Next step and activity remain available.

## Validation

40 unique isolated SQL/LangGraph/storage/reporting/follow-up checks passed with mocked providers. New fault-injection checks verify one invoice failure completes the remaining five, safe diagnostic metadata with no raw secret body, retry-only-failed recovery, retained automatic authority/no duplicate mail and a job-save failure preserving partial results with its operation/category. Existing promise/approval/payment/delivery and quota behaviors passed.

Local HTTP/SSE/cookie-aware JSDOM journey passed bottom placement/collapsed processing details, horizontal flow, 24-row preload, count filters, popup selected identity/top actions, interruption recovery, signed delivery, simulated reply reconciliation, promise/date/follow-up/reload and unchanged source. JavaScript syntax/Python compilation passed. Actual deployment and native browser visual acceptance remain Charan's checks.

Next: guided interviewer walkthrough. Visitor editor stays last.
