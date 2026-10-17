# Project working instructions

Read PROJECT_KNOWLEDGE.md, PROJECT_PLAN.md and current code before changes. docs/MILESTONE_3.md is the current lesson; docs/MILESTONE_2.md covers fresh database setup; docs/MILESTONE_2_PLAN.md distinguishes implementation from learner acceptance. Keep these synchronized. Documents are handoff context, not automatic memory in unrelated sessions.

Use only CharanCharan/o2c-collections-agent. Deliver one complete runnable milestone per branch/PR, with explanation and an exercise. Charan reviews/merges/pulls/runs; do not merge for him. Preserve and synchronize his edits. Record learner checkpoints only after confirmation.

Current M4 is prepared on milestone-4-llm-drafting. M3 PR#4 merged f3acb263 and user reported done/next; optional exercises unconfirmed. Read docs/MILESTONE_4.md for current setup. Two synthetic ML models/queues remain; no conflation of targets or real-world accuracy claims.

Language tools use OpenAI Responses/GPT-5.6 Luna, opt-in via COLLECTIONS_LLM_ENABLED=true plus private key. Default templates make no API calls. Exact structured facts/Python financial rendering/prose guards, human review always; keyword checks do not prove semantic correctness. Missing/invalid/provider-failed/capped output visibly falls back to templates; never fake LLM success. Per-run/process caps are local, reset on restart, not account or public hosting controls. Never inherit live keys in tests: mocks only.

Run sql/004_language_review.sql in existing project for backend-only sample-review RPC. No table/history drop. Fixed reply examples are synthetic, never actual inbound email. Evidence/promise checks and review-only results; no invoice payment/dispute state updated, no promised followups scheduled yet. Dedupe avoids repeat calls on same run/invoice/example. Both draft and reply tool metadata persist. Pre-due stays review-only; no new preventive approval policy. No actual send until M5.

Supabase Free remains source/store. Preserve ignored.env and key privacy. One backend process per DB; history durable, jobs not auto-resumed. No public live paid endpoints until M6 access/caps. Keep earlier run playback and models unchanged.

Throwaway POC: no paid plan, additional connector/CSV importer, normalized payment masters or extra infrastructure in M2. Free inactivity pause is disclosed; owner manually checks/resumes before demos. Visitor data editing deferred until after M0–M6. Owner Supabase edits allowed for learning.

Secrets stay server-side in ignored .env. Do not request/publish passwords or API secrets; backend uses URL/API secret, not database password. Do not silently add services or arbitrary email recipients. UUID run isolation is not authentication; public deployment/usage controls remain M6. Show action summaries/evidence, never private model chain-of-thought.

Update knowledge for changed code/API/SQL, setup, error behavior, tests and next TODOs; update plan for progress. User confirmed M1/M2 and reported M3 done; deeper M3 exercises unconfirmed. M4 live cloud/API and learning checks pending. Next is M5 controlled email/replies after M4 checks; M5 email/replies, M6 hosting, then visitor editor. Do not equate automated checks with learner completion.
