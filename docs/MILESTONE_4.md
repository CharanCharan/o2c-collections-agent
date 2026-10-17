# Milestone 4 — LLM-assisted drafts and reply review

M3 PR#4 is merged. Charan reported completion and requested the next milestone. Its optional source-edit/retraining exercises were not separately confirmed. M4 implementation/local verification are ready for review; live OpenAI and learner checks are pending.

## 1. Merge, pull and add the review function

Review/merge the M4 pull request, stop Python with Ctrl+C, and from the existing VS Code project folder:

```powershell
git status
git switch main
git pull --ff-only origin main
```

Preserve/push local edits before pulling. In the existing Supabase **SQL Editor**, paste/run **`sql/004_language_review.sql`**. This adds backend-only functions for schema readiness and atomically saving sample reply reviews. No tables or previous history are dropped. Re-running is safe. Existing SQL001/002/003 source/model setup remains.

Start your existing server:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000
```

Refresh http://localhost:8000 . First run M4 with live API disabled. It should retain the same nine-row totals and four eligible reminder drafts, clearly labelled **TEMPLATE · NO LLM**. This is free template mode, not a claim that a language model ran. Health reports M4 and the language configuration; it does not make an OpenAI request.

## 2. Understand cost before enabling the API

Provider: OpenAI Responses API. Model: **gpt-5.6-luna**, chosen for this small structured task and low token price. Official model documentation checked 2026-10-17 lists USD0.20 per million input tokens and USD1.20 per million output tokens, with structured outputs and reasoning effort none supported. No web-search/tool fees are requested by this app. Account/model availability must be verified on your own API project.

Illustration, not a quote: four calls at1000input/500output tokens each =4×[(1000×.20+500×1.20)/1,000,000] = **USD0.0032 per run**. Actual token use may differ; failed/timeout requests may still incur provider charges. Additional reply classification requests also cost tokens. API usage has separate billing from ChatGPT subscription usage. Check current provider billing/pricing before funding an account; the POC does not require a paid web host or Supabase upgrade.

Built-in boundaries in `backend/language.py`: max4draft attempts per run, max20total API attempts per Python process including replies, max1024output tokens per call, timeout30sec, no automatic retries. A process restart resets this local counter; it is **not an account spending limit or public-hosting abuse control**. It may produce visible fallbacks after several demonstrations. Inspect usage before restarting. Public quotas/auth remain M6.

Official references:

- https://developers.openai.com/api/docs/models/gpt-5.6-luna
- https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses
- https://developers.openai.com/api/docs/pricing
- https://learn.chatgpt.com/docs/pricing

## 3. Configure the key privately when ready

Use your own project at https://platform.openai.com . Review its Billing/Usage, enable API access/credits if required, and create a project API key. Do not paste it into chat or Git. This assistant has not created/funded an account, received your key or made a paid call.

Edit your **existing** ignored `.env` locally. Keep both Supabase entries. Append these settings (do not overwrite the file by copying `.env.example` again):

```dotenv
COLLECTIONS_LLM_ENABLED=true
OPENAI_API_KEY=YOUR_PRIVATE_API_KEY
```

Only the exact value true (case-insensitive) enables live calls; missing/false remains template-only. Model/caps are explicit code constants for this POC, not hidden settings. Restart Python after changing `.env`. Existing terminal environment variables take precedence over `.env`. The browser never receives the key.

Start a new run. On successful calls, eligible overdue drafts show **LLM · REVIEW REQUIRED**. Inspect **Draft validation and tool evidence** and the live `llm_draft` events: tool name, factual inputs, input/output hashes, prompt/validator versions, requested/returned model, response ID, token usage and duration. New runs use the current configuration; old runs retain their own outputs/evidence.

Four successful calls yield21events instead of13 (four extra tool started/completed pairs). Approval adds one more event. Count can vary with future eligible rows/actions; event timing reflects actual work, not artificial delays.

If credentials/quota/network/provider output fail, the page explicitly shows **FALLBACK TEMPLATE · REVIEW** and warning evidence. A completed collection run with fallbacks is not proof of successful LLM generation. Live OpenAI access/output quality remain your learner acceptance step.

## 4. What is generated and what is checked?

Python chooses eligible overdue invoices using existing policy: positive overdue balance, no dispute, urgency≥35. Pre-due predictions stay review-only; M4 does not change contact eligibility or enable their reminder approval. Finance calculations/model scoring remain deterministic Python, not LLM calculations.

The LLM returns structured `facts`, `opening`, `request` and `closing`. Checks:

1. Pydantic strict schema, expected keys/types and length bounds.
2. Exact invoice ID/amount/currency/due/as-of echo against the saved validated snapshot.
3. Reject numbers/dates/currency/payment routes and selected unsupported policy/payment claims in free prose.
4. Python constructs subject, greeting, financial fact block and signature from source facts; model wording fills only the short nonfinancial paragraphs.
5. Every draft requires human review. Numeric/date/keyword checks do not prove arbitrary natural-language meaning, politeness or complete absence of hallucination.

Disputes/monitor/no-balance/not-due records do not call the model for reminders. Raw provider error bodies and keys are not exposed. Refusal/incomplete JSON/schema/fact/prose violations route to a labelled template, with a reason/hash rather than secretly accepting it. Templates and LLM outputs have different generation_mode values. No message is sent by either mode.

## 5. Try the synthetic reply classifier

After a completed run, select an invoice and find **Review a synthetic reply example**. Choose one of five fixed fixtures: promise, payment claim, dispute, document request or untrusted instructions. Click **Classify example**.

With live API enabled, the model returns intent plus exact evidence quote and optional promise fields. Python checks invoice ID, literal quote, promise-only fields, future ISO date evidenced in the quote, positive two-decimal amount within invoice balance and evidenced literally. Relative/unsupported dates or hallucinated amounts go to manual review. These checks validate extraction support, not prove the model's intent label correct.

With API disabled/unavailable/capped, it records **manual_review** with no invented classification. This is explicitly synthetic input: no inbound email/webhook happened. Classification always requires human review. A payment claim never marks the invoice paid; disputes/promises/follow-ups are not automatically applied or scheduled in M4.

Reviews persist in `row.reply_reviews[example_id]` plus a new saved event. Repeating the same invoice/run/example reopens the existing review without another API call. SQL row-lock/dedup prevents duplicate saved records; single-process review lock prevents concurrent duplicate provider requests. A failed DB write after a paid provider response can still cost tokens and requires retry; no distributed paid-call transaction is claimed. To re-evaluate an example after configuration/model changes, use a new run.

## 6. Read the code hands-on

| File | What to understand |
|---|---|
| backend/language.py | Explicit draft_reminder/classify_reply tools, schemas, prompts, guards, provider adapter and limits |
| backend/runner.py | Await language stage; commit per-invoice tool evidence and results |
| backend/pipeline.py | Existing calculations/policy/template fallback, result.drafting and workflow M4 |
| backend/main.py | Configuration in health, fixed examples, per-run review endpoint |
| sql/004_language_review.sql | Backend-only readiness/review RPC, atomic result+event and dedup |
| fixtures/replies.json | Disclosed synthetic input and expected labels for tests; not live email |
| dist/app.js | Actual LLM/template/fallback badges, tool evidence and sample review UI |
| tests/test_milestone_4.py | Fact errors, failures, caps, output validation, dedup and immutable payment totals |

The browser does not choose prompts/models/secrets or send arbitrary reply text. This is a bounded agent workflow with explicit tools and policy, not an unconstrained autonomous collector. No LangChain/multi-agent layer is needed to demonstrate these tool boundaries.

## 7. Learning and verification checkpoints

- Run once in template mode. Explain why it is not LLM output.
- Enable API privately, start a new run, and inspect one successful `llm_assisted_validated_facts` draft and usage/model evidence. Review the actual wording; do not assume tests establish provider quality.
- Classify the paid example. Explain why the invoice balance/payment state is unchanged and review_required remains true. Repeat it: no duplicate event/call.
- Restart Python and reopen the run: draft/reply evidence should remain. Toggle API false and start a new run to observe mode differences; prior records stay unchanged.
- Optional local test exercise: inspect `test_strict_fact_echo_and_prose_guards` and see a wrong amount rejected. Never simulate errors by exposing real credentials.

Assistant evidence: **42 tests passed on Python3.12.14** including actual isolated PostgreSQL schema/functions. OpenAI response paths use **mocked HTTP transport**, not a live provider. Real local Uvicorn HTTP/SSE + frontend DOM passed template mode/manual reply review and injected-provider mode/LLM badges/reply classification/history/legacy playback. Syntax checks passed. One upstream Starlette/httpx deprecation warning remains. User Python3.13.5, actual Supabase SQL004 and live OpenAI permission/quota/latency/quality remain pending.

Run tests with requirements-dev and pytest. SQL tests need optional Node/PGlite; two training parity tests need requirements-ml; absent dependencies skip those checks explicitly. Tests force live API off and blank any inherited API key; injected mocks do not spend credit. App runtime adds no Python dependency.

## Troubleshooting and next milestone

- Missing ca_language_health/review RPC: run SQL004 in the project matching SUPABASE_URL.
- Template badge despite expecting LLM: check language.enabled/key_configured in health and restart after.env changes.
- Fallback warning: inspect redacted reason; billing/quota/access may cause401/403/429, unavailable proxy/network/timeout or invalid output can also cause fallback. Correct configuration and use a new run; never claim the fallback was generated by LLM.
- Process cap: inspect API usage first; local restart resets the cap, not provider billing. Do not automate restarts to bypass limits.
- SOCKS proxy initialization: a proxy-enabled local environment may need httpx SOCKS support; template mode initializes no provider transport. Use appropriate local proxy dependencies rather than sharing credentials.
- Existing sample review unchanged after enabling API: expected dedup; use a new run for new classification.

After learner M4 confirmation: M5 adds controlled recipient allowlist, real outbound provider IDs, signed inbound webhooks/thread matching, human-reviewed promises and scheduled followups with idempotency/audit. A claim paid still needs reconciliation. M6 public hosting/auth/caps, visitor data editing afterward. Do not publish paid live actions before those controls.
