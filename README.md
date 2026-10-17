# Charan's O2C Collections Agent

Canonical repository: https://github.com/CharanCharan/o2c-collections-agent

Milestone 4 adds opt-in LLM-assisted reminder wording with deterministic invoice-fact checks, visible template fallback and synthetic reply classification for review. Supabase stores the actual inputs/results/tool evidence. Existing pre-due prevention and overdue recovery models/queues remain.

Live API is off by default; template mode makes no model calls. No real email is sent or received. Classification never marks an invoice paid. Both risk models use synthetic history. Human review remains required.

## Start here

For a fresh setup, follow [Milestone 2 database setup](docs/MILESTONE_2.md): run the two SQL scripts in your own Supabase project, create a private local `.env`, install dependencies, then start Python. The database password is not used by this app. The backend uses a project URL and server API secret.

If M3 already works, follow [Milestone 4 setup and lesson](docs/MILESTONE_4.md): merge/pull, run `sql/004_language_review.sql`, restart and try template mode, then configure a Groq Free account privately. Keep existing `.env` values. No new runtime dependency.

For the nine-invoice demo, `sql/003_seed_pre_due.sql` adds three future examples after SQL001/002. No schema change or new database key is needed for those examples. [M3 lesson](docs/MILESTONE_3.md) covers the two models and retraining.

After database and environment setup, from the repository root in Windows / Anaconda:

```powershell
# Only create the environment if it does not already exist:
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000
```

Open http://localhost:8000 . Health: http://localhost:8000/api/health . API explorer: http://localhost:8000/docs . Direct environment Python avoids PowerShell activation-policy issues; no extra Python installation is needed. On macOS/Linux use `.venv/bin/python` instead.

Expected after SQL003 plus original seed values: nine invoices, USD 431,700 open AR, USD 372,200 past due, USD 308,000 eligible recovery exposure, three not-yet-due invoices (two at the scoring checkpoint), four overdue templates. Six stages / 13 events; separate prevention/recovery risk labels. Fixed snapshot date: 2026-10-17.

## Code and learning map

| File | Responsibility |
|---|---|
| `dist/index.html`, `dist/app.js` | Website, requests, SSE and saved-run controls |
| `backend/main.py` | FastAPI routes and frontend hosting |
| `backend/runner.py` | Run orchestration; persist events before displaying success |
| `backend/storage.py` | Server-only Supabase HTTPS RPC adapter |
| `backend/pipeline.py`, `backend/models.py` | Validation, Decimal calculations, rules and templates |
| `sql/001_schema.sql` | Tables, permissions and transactional functions |
| `sql/002_seed_demo.sql` | Repeatable synthetic source data |
| `backend/risk_model.py` | Shared features, JSON logistic inference and explanations |
| `ml/generate.py`, `ml/train.py` | Optional offline synthetic history, chronological training and holdout evaluation |
| `artifacts/payment_risk.json`, `pre_due_risk.json` | Separate trained recovery/prevention parameters and measured metrics |
| `sql/003_seed_pre_due.sql` | Three additional online source examples, no schema change |
| `backend/language.py` | Structured O2C tools, guards, rendering, caps and fallback |
| `backend/llm/` | Modular Groq/OpenAI adapters, environment settings and separate keys |
| `sql/004_language_review.sql` | Atomic backend-only sample-reply review persistence |
| `fixtures/replies.json` | Disclosed synthetic reply cases, not received email |
| `tests/` | Storage, API, PostgreSQL, ML export/label/policy checks |

- [Project knowledge](PROJECT_KNOWLEDGE.md): implementation contracts and continuation context.
- [Project plan](PROJECT_PLAN.md): scope, learner progress and future milestones.
- [M4 lesson](docs/MILESTONE_4.md): Groq Free setup, modular providers, invoice checks, draft labels and synthetic reply review.
- [M3 lesson](docs/MILESTONE_3.md): run, understand predictions, edit inputs and optionally retrain.
- [Model card](ml/MODEL_CARD.md): data provenance, target, measured results and limitations.
- [M2 checklist](docs/MILESTONE_2_PLAN.md): prior milestone, learner-complete.
- [M1 guide](docs/MILESTONE_1.md): historical first-backend lesson.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

The SQL integration tests use optional Node.js and an isolated PostgreSQL/WASM engine. To run them too, install Node.js then run `npm install --prefix tests` before pytest. Without that dependency SQL tests skip explicitly. The two training/export parity tests also require optional `requirements-ml.txt`; otherwise they skip. Node is not needed to run the application. Tests do not access your live Supabase project or model account; paid API settings are overridden off and provider responses are mocked.

## Optional offline training

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-ml.txt
.\.venv\Scripts\python.exe -m ml.generate_pre_due
.\.venv\Scripts\python.exe -m ml.train --stage pre_due
.\.venv\Scripts\python.exe -m ml.generate
.\.venv\Scripts\python.exe -m ml.train
```

This generates two independent sets of 4,000 synthetic records each, fits on past data and evaluates later dates. Dataset/manifest are ignored and reproducible; artifact is versioned. Stop/restart Python around artifact replacement. Full instructions and measured metrics are in the M3 lesson. No new paid service is involved.

## Boundaries and shared workflow

Run one backend process per database, with no multiple Uvicorn workers. Restart marks abandoned active runs interrupted; completed history stays saved. This is persistence, not a durable job queue. Saved-run controls list the latest 20; older runs remain in the database.

This is a small local POC without production authentication. Use only synthetic data. Visitor data editing is deferred until after M6. Supabase Free can pause after inactivity; check/resume before demos. No paid upgrade is required by this milestone.

Use only this repository. Push your edits before the next milestone. Review/merge milestone PRs, then pull `main` locally. Keep `.env` private and ignored; never paste secrets into chat, browser code or Git.

## API configuration and cost boundary

Default provider/model: Groq / `openai/gpt-oss-20b`. Enable only with your own Groq **Free** account and private `GROQ_API_KEY`. `.env.example` exposes provider, model, free-only guard, timeout and call/output limits; restart after edits. No automatic provider fallback or key sharing. `LLM_FREE_ONLY=true` blocks OpenAI and unreviewed models, but cannot verify the Groq account's billing tier. Confirm Free in its console; do not upgrade for this POC.

Defaults: four draft attempts/run, twenty total attempts/process, 2048 max completion tokens, thirty-second timeout, no retry. Quota/errors produce labelled templates/manual review. Local caps reset on restart; public daily/visitor controls remain M6. [M4 lesson](docs/MILESTONE_4.md) explains configuration, adapter extension and explicit optional paid compatibility. No live provider/account verification by assistant.
