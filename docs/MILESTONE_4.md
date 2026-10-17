# Milestone 4 — Modular language tools on Groq Free

M3 PR#4 merged; Charan reported normal execution. M4 PR#5 merged, including the requested free-tier switch. Live account/API and learner checks are deferred at Charan's request until after M5; see docs/MILESTONE_5.md for current email work. No actual email is sent or received by the M4 tools.

## 1. Merge, pull and prepare Supabase

Review and merge https://github.com/CharanCharan/o2c-collections-agent/pull/5 . Stop Python with Ctrl+C. Preserve/commit/push local edits before pulling. From the existing VS Code project:

```powershell
git status
git switch main
git pull --ff-only origin main
```

Run `sql/004_language_review.sql` in your existing Supabase SQL Editor if you have not already done so. It adds backend-only readiness/review functions without dropping tables/history. No additional SQL is needed for switching providers. Keep SQL001/002/003 and your existing Supabase environment settings.

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000
```

Open http://localhost:8000 . With live API disabled, expect nine invoices and four eligible **TEMPLATE · NO LLM** drafts, six stages/13 events with the original seeds. This mode makes no model requests. Health at `/api/health` reports configuration without contacting the model or revealing a key.

## 2. Set up Groq Free privately

Default provider is **Groq**, default model **openai/gpt-oss-20b**. The model name contains openai because of its publisher; requests go to Groq, not the OpenAI API. It does not use your ChatGPT subscription or its linked card.

Visit https://console.groq.com . Confirm your account is on **Free**, do not upgrade to Developer, and create an API key. Keep it private: never paste it in chat, Git, screenshots or browser code. Groq documents that upgrading to Developer requires a payment method and starts usage billing. The application cannot identify a Free versus paid account from the key: `LLM_FREE_ONLY=true` is a provider/model routing restriction, **not billing-tier verification**. If your account is already paid, the same model can incur charges. Verify the account first.

Edit your existing ignored `.env`; preserve Supabase values. Replace old duplicate language entries rather than appending competing values. Do not copy `.env.example` over a working `.env`.

```dotenv
COLLECTIONS_LLM_ENABLED=true
LLM_PROVIDER=groq
LLM_MODEL=openai/gpt-oss-20b
LLM_FREE_ONLY=true
GROQ_API_KEY=YOUR_PRIVATE_GROQ_KEY
LLM_MAX_CALLS_PER_RUN=4
LLM_MAX_CALLS_PER_PROCESS=20
LLM_MAX_OUTPUT_TOKENS=2048
LLM_TIMEOUT_SECONDS=30
```

Restart Python after any settings/key change. Existing terminal environment variables override `.env`; remove stale terminal settings if health differs from the file. The Groq adapter only reads `GROQ_API_KEY`; an old `OPENAI_API_KEY` is never used for Groq or automatic failover. Set `COLLECTIONS_LLM_ENABLED=false` to return to templates without deleting your key.

Free capacity is limited and shared by account/model; inspect your Groq console's current limits. HTTP429 produces labelled fallback, no automatic retry, upgrade or alternate-provider call. Local defaults allow four draft attempts/run, twenty total API attempts/process including replies, 2048 maximum completion tokens/call and a 30-second timeout. Counts reset on restart: these are local safeguards, not durable public-user quotas. Reasoning can consume completion capacity; incomplete outputs safely fall back. No always-available/unlimited-free claim is made.

Official documentation, checked 2026-10-17; recheck availability before a demo:

- https://console.groq.com/docs/billing-faqs
- https://console.groq.com/docs/rate-limits
- https://console.groq.com/docs/structured-outputs
- https://console.groq.com/docs/reasoning

## 3. Observe a real model run

Start a new run. Successful overdue drafts show **LLM · REVIEW REQUIRED**. Inspect **Draft validation and tool evidence**: selected/returned model, provider, adapter/prompt/validator versions, facts, request/output hashes, response ID, normalized token usage and duration. Four successful drafts add eight `llm_draft` events: 21 events total, before approval. Timing reflects actual work.

Missing key, blocked settings, quota, timeout, refusal or invalid output produces **FALLBACK TEMPLATE · REVIEW** and warning evidence. A completed run with template fallbacks does not establish successful model generation. Old runs keep their original evidence when you change settings.

The free-only guard permits the reviewed Groq models `openai/gpt-oss-20b`, `openai/gpt-oss-120b`, and `qwen/qwen3.8-27b`. Change `LLM_MODEL` and restart to try another; check your account's model availability and limits first. This allowlist must be maintained as providers change. It cannot enforce account pricing.

## 4. Understand the modular code

| File | Responsibility |
|---|---|
| `backend/llm/config.py` | Environment parsing, defaults, separate provider key names, free-only routing and bounded limits |
| `backend/llm/providers.py` | Shared structured request/result interface; Groq Chat Completions and optional OpenAI Responses adapters; fixed endpoints |
| `backend/llm/errors.py` | Safe shared error type |
| `backend/language.py` | O2C prompts, schemas, validation, deterministic rendering, orchestration and template/manual-review fallback |
| `backend/runner.py` | Commit actual per-invoice progress and results |
| `backend/main.py` | Health/configuration, fixed reply examples and review endpoint |
| `sql/004_language_review.sql` | Backend-only atomic saved review/event and deduplication |
| `fixtures/replies.json` | Synthetic examples, not inbound messages |
| `dist/app.js` | Provider/model status, draft badges and evidence/review UI |
| `tests/test_llm_providers.py` | Groq contract, configuration/key isolation, no failover and failure cases |
| `tests/test_milestone_4.py` | Domain policy, OpenAI adapter regression, reply deduplication and persistence |

Both adapters accept `StructuredRequest` and return `StructuredResult(value, audit)`. The service selects one adapter; business rules do not depend on the wire API. Groq uses strict JSON Schema Chat Completions with reasoning excluded from returned evidence. OpenAI uses Responses with store false. Portable wire schemas omit length keywords; full Pydantic length/type checks still run locally. No additional SDK/runtime dependency is required.

To support another provider, add an adapter implementing `generate`/`close`, register it in `PROVIDERS`, and add its default/key mapping in config. Test its wire contract and failure behavior before use. It is not free-only approved automatically. Provider model families can require different capabilities/parameters: changing a model string does not guarantee compatibility. Arbitrary base URLs and browser-supplied models/keys are deliberately unsupported.

Optional paid OpenAI compatibility remains explicit: `LLM_PROVIDER=openai`, `LLM_MODEL=gpt-5.6-luna`, private `OPENAI_API_KEY`, `LLM_MAX_OUTPUT_TOKENS=1024`, and **LLM_FREE_ONLY=false** are all required with live enablement. Do not select this for the zero-cost POC. ChatGPT subscriptions do not include API usage. There is no fallback from Groq to this adapter.

## 5. Business rules and reply review

Python retains eligibility: positive overdue balance, no dispute, urgency at least35. Pre-due predictions remain review-only. Both risk models and source data remain unchanged. Language models provide short nonfinancial opening/request/closing paragraphs; Python supplies the financial block, subject, greeting and signature.

Validation requires strict expected fields/types/lengths and exact echo of invoice ID, balance, currency and dates. Prose guards reject numbers/dates/currency/payment routes and selected unsupported claims. These checks do not prove arbitrary prose meaning or politeness: **human review is always required**. Invalid output retains a clearly labelled template. Raw error bodies, secrets and model reasoning are not shown.

After a completed run, choose one of five **synthetic reply examples**: promise, paid claim, dispute, documents or untrusted instructions. Classify the example. Output requires literal evidence and supported future ISO promise date/positive two-decimal amount within the balance. Unsupported extraction routes to manual review. Intent still needs human judgment. Disabled/unavailable/capped calls record manual review with no invented classification.

A paid claim never marks an invoice paid. No balance, dispute, contacted state or scheduled follow-up is changed. Reviews persist in `row.reply_reviews` and audit events. Repeating the same run/invoice/example returns its saved review without another provider call. Use a new run after model changes. SQL locking/dedup and a process review lock prevent duplicate saved reviews; API and database operations are not a distributed exactly-once transaction. A failed save after generation can consume quota again on retry.

## 6. Hands-on checkpoints and verification

1. Run template mode; explain why no model ran.
2. Confirm Groq Free, configure privately, restart and inspect one successful Groq draft/model/usage. Read its wording.
3. Change an allowed model in `.env`, restart, start a new run and confirm its audit model. Prior history must remain unchanged.
4. Classify paid; verify balance unchanged. Repeat and verify no new event/call. Restart and reopen saved evidence.
5. Read `config.py` → `providers.py` → `language.py`; explain how provider configuration is separated from financial rules. Optional: lower process cap to1 and observe explicit fallbacks, then restore it.

64 automated tests passed on Python3.12.14; local Uvicorn HTTP/SSE/frontend DOM passed with mocked Groq, including draft labels, reply review, approval and saved/legacy playback. Python/JavaScript syntax checks passed. One existing upstream Starlette/httpx deprecation warning remains. Details are recorded in PROJECT_KNOWLEDGE.md. Provider requests are mocked: tests establish contracts and error handling, not live account availability, free status, wording quality or latency. No real provider key/call was used by the assistant. User Python3.13.5, actual Supabase SQL004 and live model checks remain pending. Tests force inherited keys/settings off. SQL tests need optional Node/PGlite; training tests need requirements-ml; absent dependencies skip explicitly.

Troubleshooting: missing `ca_language_health` means run SQL004 in the matching Supabase project. Configuration-blocked health means check provider/model/free-only/bounded numeric settings. Missing key means check the selected provider's own key. A429 means wait for quota/rate reset and inspect the console; fallback is intentional. Invalid structured text or output truncation means review the warning; do not call a template model-generated. Existing saved reply reviews stay deduplicated after configuration changes.

## Next milestone

After M4 learner checks, M5 adds controlled email recipients, approval/idempotency, delivery IDs/events, signed inbound replies, human-reviewed promises and recorded follow-ups. M6 adds hosting/access and durable visitor/daily quotas before public exposure; the current process counter is insufficient. Visitor editing follows M6. Supabase Free can pause: manually check/resume before an interview demo.
