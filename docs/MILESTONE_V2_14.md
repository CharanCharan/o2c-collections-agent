# V2.14 — Checkpoint save-order repair

The live errors still report SQLSTATE 23503 even with SQL013 installed. Read-only live health confirmed checkpoint revision 13 ready. Stopping local/live overlap does not fix this separate save-order problem.

## What was wrong

LangGraph 1.2.16 saves checkpoints and pending task writes in separate background operations. In particular, input writes can arrive before the input checkpoint, even with `durability='sync'`. Our database required the checkpoint to exist first. SQL013 only handled late writes for already-retired checkpoints; it still rejected valid early writes. The previous synchronous mock database transport hid this ordering.

A regression test now uses the actual pinned LangGraph runtime, actual PostgreSQL functions in isolated PGlite, and delayed checkpoint RPCs. The same graph fails against SQL013 with 23503 and completes against SQL014. This reproduces a sufficient cause of the reported error; the private live request traces are unavailable here.

## Apply the fix

1. Review and merge this PR, then pull main into your local project.
2. While no collection run is active, open Supabase → SQL Editor. Run the complete `sql/014_checkpoint_write_order.sql` file after SQL013. It should return `checkpoint_schema: 14`, `retention: 8`, `pending_retention: 8`, `ready: true`.
3. Deploy latest main on Render. No dependency or environment changes. Keep one backend process using this database.
4. Open `/api/health`: expect `app_version: v2.14`, `workflow.ready: true`, and `workflow.checkpoint.checkpoint_schema: 14`. The UI stays workflow-15 because this repair changes no UI assets.
5. In the same browser session, reopen the affected saved run and retry its failed invoices. Completed invoices remain retained, and existing email send receipts/idempotency remain in force. A new run also reuses this browser's existing cases.

SQL014 preserves existing rows; it changes the writes foreign key from checkpoint ownership to case ownership. This lets early writes persist durably until their checkpoint arrives. They cannot appear as a resumable checkpoint by themselves. Case deletion still cascades to writes; RLS and private service-only RPC access stay in place. Latest eight checkpoints retain their linked writes; writes older than that window are removed. Up to eight unpaired checkpoint IDs per case/namespace are retained for incomplete saves. Per-case/namespace transaction locks and positive/negative write-index idempotency remain.

No history reset, fake successful result, automatic SQL execution, provider retry or in-memory checkpoint fallback. The updated backend refuses to start graph work on revision13 even if that old health function says ready. Old saved error messages may still mention SQL013; new failures point to SQL014.

## Hands-on understanding

Read `backend/workflow/checkpoints.py`: `aput` saves a checkpoint, `aput_writes` saves pending writes, and `aget_tuple` joins them on read. Then read SQL014's foreign key change and cleanup. A checkpoint is the saved graph state; pending writes preserve completed task outputs for recovery. Email receipts are separate business records, so this storage repair does not authorize a second email.

Validation: 172 tests passed in 206.66s; Python compile passed. Tests use only isolated SQL and mocked providers, including delayed saves, 24-invoice processing, approval/resume, retention, case deletion, migration reapplication, access isolation and existing delivery/follow-up/reporting regressions. No live database mutation, model/email call or deployment was performed by the assistant. Charan must apply the migration and confirm the live retry result before moving to the interviewer walkthrough; visitor data editing remains last.
