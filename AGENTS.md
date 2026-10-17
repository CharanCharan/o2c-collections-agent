# Project working instructions

Read PROJECT_KNOWLEDGE.md, PROJECT_PLAN.md and current code before changes. docs/MILESTONE_2.md is the current setup/lesson; docs/MILESTONE_2_PLAN.md distinguishes implementation from learner acceptance. Keep these synchronized. Documents are handoff context, not automatic memory in unrelated sessions.

Use only CharanCharan/o2c-collections-agent. Deliver one complete runnable milestone per branch/PR, with explanation and an exercise. Charan reviews/merges/pulls/runs; do not merge for him. Preserve and synchronize his edits. Record learner checkpoints only after confirmation.

Current M2 is ready in PR #3, not yet learner-verified. Supabase Free hosted Postgres is the sole runtime source/store; runtime invoice JSON removed. Five ca_ tables, small HTTPS storage adapter, fixed synthetic SQL seed. Rule urgency is not ML, templates are not LLM, approvals do not send email. History persists; jobs do not auto-resume. One backend process per database. Never claim live Supabase verification from isolated PGlite tests.

Throwaway POC: no paid plan, additional connector/CSV importer, normalized payment masters or extra infrastructure in M2. Free inactivity pause is disclosed; owner manually checks/resumes before demos. Visitor data editing deferred until after M0–M6. Owner Supabase edits allowed for learning.

Secrets stay server-side in ignored .env. Do not request/publish passwords or API secrets; backend uses URL/API secret, not database password. Do not silently add services or arbitrary email recipients. UUID run isolation is not authentication; public deployment/usage controls remain M6. Show action summaries/evidence, never private model chain-of-thought.

Update knowledge for changed code/API/SQL, setup, error behavior, tests and next TODOs; update plan for progress. User confirmed M1 normal run and Supabase project creation. M2 cloud setup/source-edit/restart exercises are pending; M1 amount exercise is superseded. Next is M3 target/data/model evaluation after M2 learner checks.
