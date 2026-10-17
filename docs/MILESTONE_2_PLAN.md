# Milestone 2 — data ingestion and persistent receivables history

Status: PLANNED ONLY. No Supabase project, database migrations, CSV importer or
online connector has been implemented or user-confirmed yet.

## Outcome

Import receivables into durable Postgres storage, calculate open balances from
invoice values/credits/payments, and preserve runs, events and approved dry runs
after restarting Python. Keep the current frontend/API and observable workflow.
Add CSV import and one configured HTTPS source for documented synthetic AR data.

This extends M1; ML is M3, LLM tasks M4, email/replies M5, public deployment M6.
Persisted history does not automatically make in-progress execution crash-resilient.

## Prerequisite and decision checklist

- [x] Canonical GitHub repository established; M1 PR merged.
- [x] Charan reported normal local M1 output matching expected values.
- [ ] Finish/record the small M1 amount-edit exercise, or explicitly defer it.
- [ ] Commit/push any learner edits; check current main and clean local status.
- [ ] Guide Charan to create/select his own Supabase project on an eligible plan.
      Inspect current plan limits before choosing services; no paid upgrade assumed.
- [ ] Select the server-to-Postgres connection method and document its configuration.
      A pooled TLS DATABASE_URL is the initial preference, subject to account access.
- [ ] Configure credentials locally/server-side with ignored .env and blank
      .env.example names. Never ask for passwords/keys in chat or put them in JS.
- [ ] Choose one controlled HTTPS location for sanitized synthetic CSV/JSON data;
      hosting location is undecided. Record source URL, license/provenance, schema,
      as-of date and synthetic status. Do not use contacts from public invoices.

## Implementation checklist

### A. Database foundation

- [ ] Add a small storage/repository interface so pipeline functions stay readable.
- [ ] Add versioned SQL migrations and a documented apply/rollback procedure.
- [ ] Define tables and keys for datasets/imports/import_rows, customers, invoices,
      payment applications, runs, run_events and interactions. Include the agreed
      dispute/promise-to-pay structures, with no email/reply automation yet.
- [ ] Use stable source IDs and dataset ownership/partition keys; different demo
      visitors/runs must not overwrite one another's state.
- [ ] Use NUMERIC/Decimal for amounts, explicit currency, UTC event times and
      explicit as-of dates. Keep foreign keys and appropriate check constraints.
- [ ] Define unique import/source identifiers and unique (run_id, event_id) keys.
      Add an approval uniqueness constraint appropriate to one action/invoice/run.
- [ ] Keep schema-only setup separate from seed imports. Do not store real data
      or secrets in migrations.

### B. Import and finance data

- [ ] Introduce invoice_amount, credit_amount and applied payments with a written
      definition of open_balance. Current M1 amount is already an open balance.
- [ ] Handle partial payments and closed invoices. Keep unapplied cash distinct;
      a customer email saying paid is never proof of an applied payment.
- [ ] Implement CSV import using a fixed documented schema and safe size/row limits.
- [ ] Add one server-configured HTTPS connector; validate content and source,
      use timeouts, and avoid arbitrary visitor-supplied fetch URLs.
- [ ] Record import batch ID, source, raw/sanitized input reference/hash, timestamp,
      accepted/rejected rows and clear validation reasons.
- [ ] Define retry/idempotency behavior so reimport does not duplicate invoices or
      payment applications. Keep historical run input snapshots immutable.
- [ ] Reject/segregate unsupported currencies; no silent cross-currency totals.
- [ ] Seed a small readable synthetic dataset with partial-payment, duplicate and
      dispute examples. Keep labels explicit; this is not yet an ML training claim.

### C. Persistent runs and event stream

- [ ] Save a run and its input snapshot before starting work.
- [ ] Persist event order, operation outputs, errors and final results; emit success
      only after the corresponding record is committed.
- [ ] Read run history and replay SSE events from Postgres after a restart.
- [ ] Preserve the existing browser deduplication and Last-Event-ID behavior.
- [ ] Record dry-run approvals transactionally and idempotently across processes,
      not only under an in-memory lock.
- [ ] Define interrupted-run behavior on restart. Mark abandoned work interrupted
      rather than complete; no automatic replay of side effects is assumed.
- [ ] Show a truthful database-unavailable failure. Do not silently fall back to
      temporary memory while claiming records are persistent.

### D. Learner interface and documentation

- [ ] Add only the controls needed to import/select the demo dataset and reopen
      a saved run; keep the Start/event/queue experience recognizable.
- [ ] Show import source, row counts, as-of date and rejection reasons.
- [ ] Update health/storage labeling so users can distinguish configured Postgres
      from any explicit local-only learning mode.
- [ ] Add docs/MILESTONE_2.md with setup, schema map, import flow, SQL inspection
      queries, expected results and a restart-persistence exercise.
- [ ] Update PROJECT_PLAN.md and PROJECT_KNOWLEDGE.md based on implemented behavior.

## Required verification and acceptance

- [ ] Import a known valid dataset and verify counts and exact Decimal balances.
- [ ] Reimport/retry without duplicate invoice/payment records.
- [ ] Invalid/duplicate rows get explicit treatment; valid/rejected counts reconcile.
- [ ] Partial payment reduces the correct invoice; closed invoices get no reminder.
- [ ] A dispute remains paused regardless of urgency.
- [ ] Run IDs isolate results and approvals; no cross-run overwrites.
- [ ] Restart Python and retrieve the same completed run, events and approved action.
- [ ] SSE replay returns only events after Last-Event-ID, without new duplicates.
- [ ] Duplicate/concurrent approval does not create multiple interactions.
- [ ] An interrupted run is not reported completed after restart.
- [ ] Database outage and connector timeout fail visibly, without invented success.
- [ ] Charan imports a dataset, checks a balance using SQL, restarts the app and
      retrieves saved history himself. Only then mark M2 learner-complete.

## Delivery

One tested milestone PR in CharanCharan/o2c-collections-agent. Charan merges and
pulls before running the guide. Do not create a second repository or change the
original public prototype to imply these integrations already exist.
