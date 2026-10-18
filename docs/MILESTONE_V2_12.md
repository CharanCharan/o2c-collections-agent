# V2.12 — Non-destructive checkpoint storage repair

## Diagnosis and evidence

User reported ca_checkpoint failures on INV-10287, INV-10482 and INV-10604, with storage_operation_failed/process_invoice and a stopped saved job. The old diagnostic omitted the underlying PostgreSQL code and checkpoint action, so the exact failure in the user's Supabase project cannot be confirmed from that message alone.

A deterministic isolated PostgreSQL/PGlite reproduction of the repository's SQL009 function confirmed a bug: insert more than eight checkpoints, then deliver a delayed pending-write request for an older checkpoint. Retention has deleted its parent row and cascaded its existing writes; the delayed request fails with foreign-key SQLSTATE23503. Local in-memory integration calls did not previously exercise this delayed-write order. Production network timing can expose it.

The assistant has no SUPABASE_URL/key or local .env in this workspace and cannot apply SQL to the user's actual project. No live database changes, cleanup, provider calls or deployment were performed. Do not claim the user's database is already fixed or that the exact original SQLSTATE was established.

## Apply the repair

1. Merge this PR and pull main locally.
2. Stop the local backend before applying the migration. In your existing Supabase project's SQL Editor, paste and run all of `sql/013_checkpoint_repair.sql`, after existing SQL009–012. Do not rerun old seed/schema files or delete history.
3. The final query should return checkpoint_schema13, retention8, readytrue.
4. Restart Python. `/api/health` should show app_versionv2.12, ui_versionworkflow-14 and workflow.checkpoint.readytrue.
5. On the existing failed run use Retry failed invoices or Recover unfinished processing. Existing successful entries, baselines, modes, mail intent IDs and receipts are retained.
6. After local verification, manually deploy latest main in Render and hard-refresh. If localhost and Render share this Supabase project, test with only one backend active. Current startup recovery assumes one process/database and another server startup can mark active jobs as stopped.

The migration is function-only: no DROP/TRUNCATE, no invoice edits, no clearing runs, no resetting mail/LLM budgets or idempotency. Source AR, cases/messages, mail receipts and saved runs remain. New normal checkpoint puts still maintain the existing latest-eight retention policy.

## What the SQL changes

- Replaces ca_checkpoint with explicitly qualified reads and explicit insert columns.
- Uses a transaction-scoped advisory lock per case/namespace for puts/writes, serializing retention against concurrent write requests without a global portfolio lock.
- A write whose parent is missing is ignored only when there are at least eight retained checkpoints and its ID is older than the oldest retained ID. The RPC returns retiredtrue. Such writes fall outside the supported resume window; the function does not recreate obsolete checkpoints or erase newer state.
- Unknown/newer missing checkpoint references, including another namespace with no matching parent, still fail. It does not convert arbitrary persistence failures into success.
- Preserves positive-index write idempotency and replaceable negative-index LangGraph special writes.
- Keeps service-only RPC permissions and table RLS.
- Adds a private read-only ca_checkpoint_health function reporting the installed repair revision. Its ready flag verifies the function revision marker, not a claim that all possible runtime database failures are impossible.

No business/financial tool or provider retry policy changes. Existing eight-checkpoint/40-activity retention remains. Deleting all past runs would not correct this SQL logic and could remove valuable send receipts; no reset is included.

## Better diagnosis if a different issue remains

SupabaseStore now preserves only safe SQLSTATE and ca_checkpoint action (get/put/writes) in diagnostics. Error categories distinguish missing schema, checkpoint reference/schema errors and database timeouts. Public run issue rows show SQLSTATE/action alongside operation/reference. Raw provider/SQL error text, credentials and checkpoint payloads remain hidden.

New graph runs check ca_checkpoint_health before creating work. Health reports workflow.readyfalse if the repair is absent or older code replaced the function. Current AR preview remains available. This prevents creating more graph runs on known-unrepaired storage.

## Verification

48 targeted isolated SQL/LangGraph/storage/reporting/follow-up/event-delivery tests passed with mocked providers. New tests cover old23503 reproduction, repeated repair application with preserved counts, delayed retired writes, latest-eight bound/newest data retained, unknown/future/other-namespace references still failing, write-index dedup/negative-index updates, anon access denial, safe SQLSTATE/action diagnostics and blocking new graph runs before repair. Existing case approval/restart/provider dedup, promise follow-ups, run reports and owned event streams remain covered.

JavaScript syntax/Python compilation passed. No live Supabase repair verification yet; user's SQL execution and retry results are the remaining acceptance checks. No new packages, keys or paid infrastructure.

Next: verify this database repair before continuing feature milestones. Then guided interviewer walkthrough; visitor editor last.
