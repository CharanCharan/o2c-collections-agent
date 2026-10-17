# Milestone 2 — Supabase source and persistent run history

Status: PLANNED. Scope simplified by Charan on 2026-10-17 for a disposable, low-cost interview POC. Current M1 still reads JSON until M2 is implemented and merged.

## Decisions

- Use Supabase Free, which hosts Postgres. These are one database choice, not two competing databases.
- Runtime invoice data comes directly from Supabase tables through Python using Supabase's HTTPS data API/client. Supabase is both the online data source and durable store.
- Replace data/invoices.json as runtime input. Seed the same synthetic invoices once using a checked-in SQL script; no local JSON fallback will masquerade as database ingestion.
- Keep the current FastAPI/frontend/SSE flow and simple business rules. No extra import service, ORM, separate database server, customer-login system or queue infrastructure is required for this milestone.
- Drop the previously planned CSV importer and second arbitrary HTTPS dataset connector from M2. Owner data setup uses Supabase's SQL/table editor.
- Browser visitors editing data is deferred until all core milestones M0–M6 are complete. Owner edits in Supabase for learning/testing are allowed now; the app UI remains read-only apart from existing run/approval controls.

## Cost boundary

Supabase pricing checked 2026-10-17: Free is USD 0/month with 500 MB database space and a limit of two active projects. Free projects pause after one week of inactivity. This is suitable for the small POC but is not guaranteed always-on hosting. Check/resume the project before demonstrations; do not introduce a paid plan or artificial keep-alive automation to hide this limitation.

Source: https://supabase.com/pricing
Data API: https://supabase.com/docs/guides/api

## Minimal data design

Start with five small tables; use additional schema only if a demonstrated requirement needs it:

| Table | Purpose |
|---|---|
| demo_settings | Snapshot as-of date, currency and seed/demo label |
| invoices | Existing source fields: stable ID, customer, segment, outstanding amount, due date, payment history and dispute flag |
| runs | Run ID/status, immutable input snapshot, final result and timestamps |
| run_events | Ordered event IDs and exact stage output/error payloads per run |
| interactions | Approved dry-run records; uniqueness by run/invoice/action |

For this milestone amount remains the supplied outstanding balance, as in M1. Normalized customer/payment/credit masters and an invoice-application ledger are deferred unless needed by a later feature; do not claim payment reconciliation is implemented. Preserve Decimal/NUMERIC amounts and USD-only checks. Store per-run input snapshots so source edits cannot rewrite historical results.

## Setup and implementation TODO

- [x] M1 merged; Charan confirmed expected local results.
- [ ] Record or explicitly defer the M1 amount-edit exercise; push any learner edits.
- [ ] Charan creates/selects a Supabase project on Free under his own account.
- [ ] Add SQL schema and idempotent synthetic seed scripts; execute in Supabase SQL editor.
- [ ] Guide local backend configuration using ignored .env; check in only blank .env.example. Keep server credentials out of browser code, Git and chat.
- [ ] Add one small storage module around the Supabase HTTPS API/client. Show connection/configuration failures clearly.
- [ ] Replace JSON-file ingest with a fresh database read per run; validate the returned rows and record source/time/snapshot hash.
- [ ] Persist run state, ordered events, result snapshots and approvals. Emit persisted-success events only after writes succeed.
- [ ] Enforce dry-run approval uniqueness transactionally in Postgres, including retry/concurrent requests.
- [ ] Reopen/replay a saved completed run after Python restart using existing run/event endpoints.
- [ ] Define interrupted-run behavior after restart; do not claim persisted history automatically resumes background work.
- [ ] Remove runtime JSON dependency and update source/storage labels, code map, tests and guides.
- [ ] Keep visitor-edit controls out of M2. Add a lightweight history/open-run control only if needed to demonstrate persistence.
- [ ] Prepare the complete runnable M2 PR and docs/MILESTONE_2.md; Charan merges, pulls and verifies locally.

## Acceptance checks

- [ ] Database-seeded sample produces the same six invoices, USD 372,200 open balance, USD 308,000 eligible exposure and four drafts.
- [ ] Owner changes Northstar's balance in Supabase; the next run shows the new amount and totals, without editing local invoice JSON.
- [ ] Restoring seed data restores expected results without duplicate rows.
- [ ] Restart Python, then retrieve the same completed run, stage events and approval.
- [ ] Historical run results remain unchanged after source-table edits.
- [ ] Different runs do not overwrite one another's approval state.
- [ ] Duplicate/concurrent approval creates only one interaction.
- [ ] Disputes and low-urgency/no-draft rules retain M1 behavior.
- [ ] A paused/unavailable database produces a visible failure, never silent fallback or invented success.
- [ ] Charan can explain the database read, inspect rows in SQL, and demonstrate restart persistence.

## Deferred work

M3: trained payment model. M4: LLM drafting/reply classification. M5: real email/replies. M6: public deployment and essential access/usage controls. After M6: optional visitor-edit playground with isolated/resettable data, not edits to the shared seed portfolio.
