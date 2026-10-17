# Milestone 2 checklist

Status: CODE READY in PR #3; live Supabase setup and learner acceptance pending. Detailed steps: [M2 setup and exercise](MILESTONE_2.md). Scope: Supabase Free hosted Postgres as sole invoice source/store, minimal five ca_ tables, SQL seed, existing Python/frontend. No JSON fallback, CSV importer, second source connector, normalized finance ledger or visitor editor.

## Completed implementation

- [x] User created Supabase project; database password copied (not used by app).
- [x] SQL schema, RLS/grants, transactional functions and repeatable six-invoice seed.
- [x] Server-only HTTPS storage adapter and blank .env.example; secrets ignored.
- [x] Fresh database source read per run; validation and canonical snapshot hash.
- [x] Persistent input/results/events/approvals, ordered commit-before-success events.
- [x] Transactional duplicate approval protection and unchanged dispute/monitor policy.
- [x] Saved-run list/reopen UI, SSE replay and restart-interrupted policy.
- [x] Visible sanitized failure, no JSON fallback or fake success.
- [x] Local verification: 14 tests including isolated actual SQL; HTTP/SSE/frontend DOM flow passed.
- [x] M1 unconfirmed JSON exercise explicitly superseded by database edit exercise.

## Learner/live checks — do not infer from implementation tests

- [ ] Review/merge PR #3 and pull canonical main; preserve any local edits.
- [ ] Execute SQL001 and SQL002 in user's Supabase project.
- [ ] Configure local ignored .env using project URL and backend API secret, not DB password.
- [ ] Health shows M2/supabase_postgres/six rows; Start yields expected seeded totals.
- [ ] Owner DB edit changes next run to 382,200 open / 318,000 eligible; old run stays unchanged.
- [ ] Restore Northstar source balance to 86,400.
- [ ] Approval, events and results survive Python restart; duplicate is not recorded twice.
- [ ] User can trace source → rules → committed evidence → SSE and explain no automatic job resume.

Supabase Free pricing reference: https://supabase.com/pricing . Plan selected for zero-cost POC; actual account billing state not independently inspected. Free projects can pause after inactivity; check/resume before demos. Run only one backend process per DB. No paid upgrade or keepalive assumed.

Next M3: define payment-risk target/prediction time, historical data and leakage-safe holdout before training. M4 LLM; M5 controlled email/replies; M6 deployment; visitor data editing after M6 only.
