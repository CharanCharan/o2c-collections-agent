# Project working instructions

Read PROJECT_KNOWLEDGE.md and PROJECT_PLAN.md before making changes, then inspect current code. They hold implementation/resume context and the scope/progress record. docs/MILESTONE_2_PLAN.md contains the planned next milestone. Keep documents synchronized with merged behavior and distinguish tested, learner-confirmed and planned work.

Use only CharanCharan/o2c-collections-agent. Deliver one complete runnable milestone at a time through a branch and pull request, as agreed on 2026-10-17. Explain its components and provide a small exercise. Charan reviews/merges, pulls, runs and edits locally. Update learner checkpoints only after his confirmation. Preserve the agreed O2C scope.

M1 executes a real local JSON pipeline in Python, with SSE events and calculated totals. Data is synthetic, scores are policy rules, drafts are templates, approvals are dry-run only, and storage is process memory. Do not claim these are real ERP ingestion, trained predictions, LLM output, actual email or persistent storage. Preserve explicit labels until integrations are implemented and verified.

Do not silently add external services, credentials, paid plans, or arbitrary email recipients. Keep every public visitor's run isolated. Keep secrets server-side and out of source control. Show evidence-backed action summaries, not private model chain-of-thought.


When delivering implementation changes, update PROJECT_KNOWLEDGE.md for changed contracts, calculations, limits, setup and troubleshooting, and PROJECT_PLAN.md for progress. Record Charan's evidence accurately: M1's normal local run and expected outputs are confirmed; its amount-edit exercise is not yet confirmed. Never claim documentation provides automatic memory in unrelated sessions; continue from the current repository documents.


Scope decision 2026-10-17: this is a throwaway POC. M2 uses Supabase Free (hosted Postgres), reads invoice data directly from its tables and persists history there. Replace runtime invoice JSON; seed via SQL. Prefer one small server-side Supabase API module and the revised minimal tables. CSV import, an additional online data-source connector, normalized payment masters and extra production infrastructure are not M2 requirements. Visitor data editing is deferred until after M0–M6; owner Supabase edits for learning are allowed. Respect the Free plan's inactivity pause rather than assuming always-on availability or a paid upgrade.
