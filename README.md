# Charan's O2C Collections Agent

Canonical repository: https://github.com/CharanCharan/o2c-collections-agent

Milestone 3 reads invoices from Supabase and applies a saved logistic-regression model to predict an overdue balance remaining 30 days after the snapshot. The website shows actual predictions, feature contributions, model version and evaluation evidence. Results/events/approvals remain saved in Postgres.

The model is trained on clearly disclosed synthetic history, not real customer outcomes. Urgency remains rules; drafts remain templates; dry-run approvals send no email. LLMs, controlled email and public deployment remain later milestones. The older hosted presentation prototype is separate from this local app.

## Start here

For a fresh setup, follow [Milestone 2 database setup](docs/MILESTONE_2.md): run the two SQL scripts in your own Supabase project, create a private local `.env`, install dependencies, then start Python. The database password is not used by this app. The backend uses a project URL and server API secret.

If M2 already works, no new SQL or keys are needed. Follow [Milestone 3 lesson and exercises](docs/MILESTONE_3.md). The committed trained artifact runs without installing ML packages.

After database and environment setup, from the repository root in Windows / Anaconda:

```powershell
# Only create the environment if it does not already exist:
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000
```

Open http://localhost:8000 . Health: http://localhost:8000/api/health . API explorer: http://localhost:8000/docs . Direct environment Python avoids PowerShell activation-policy issues; no extra Python installation is needed. On macOS/Linux use `.venv/bin/python` instead.

Expected seeded output: six stages / 13 stored events; ML-risk percentages beside rule urgency. Financial totals: USD 372,200 open AR, USD 308,000 eligible exposure, four template drafts, one monitored invoice and one paused dispute. Fixed snapshot date: 2026-10-17.

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
| `artifacts/payment_risk.json` | Learned parameters, dataset hash and measured metrics |
| `tests/` | Storage, API, PostgreSQL, ML export/label/policy checks |

- [Project knowledge](PROJECT_KNOWLEDGE.md): implementation contracts and continuation context.
- [Project plan](PROJECT_PLAN.md): scope, learner progress and future milestones.
- [M3 lesson](docs/MILESTONE_3.md): run, understand predictions, edit inputs and optionally retrain.
- [Model card](ml/MODEL_CARD.md): data provenance, target, measured results and limitations.
- [M2 checklist](docs/MILESTONE_2_PLAN.md): prior milestone, learner-complete.
- [M1 guide](docs/MILESTONE_1.md): historical first-backend lesson.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

The SQL integration tests use optional Node.js and an isolated PostgreSQL/WASM engine. To run them too, install Node.js then run `npm install --prefix tests` before pytest. Without that dependency SQL tests skip explicitly. The training/export parity test also requires optional `requirements-ml.txt`; otherwise it skips. Node is not needed to run the application. Tests do not access your live Supabase project.

## Optional offline training

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-ml.txt
.\.venv\Scripts\python.exe -m ml.generate
.\.venv\Scripts\python.exe -m ml.train
```

This generates 4,000 synthetic historical records, fits on past data and evaluates later dates. Dataset/manifest are ignored and reproducible; artifact is versioned. Stop/restart Python around artifact replacement. Full instructions and measured metrics are in the M3 lesson. No new paid service is involved.

## Boundaries and shared workflow

Run one backend process per database, with no multiple Uvicorn workers. Restart marks abandoned active runs interrupted; completed history stays saved. This is persistence, not a durable job queue. Saved-run controls list the latest 20; older runs remain in the database.

This is a small local POC without production authentication. Use only synthetic data. Visitor data editing is deferred until after M6. Supabase Free can pause after inactivity; check/resume before demos. No paid upgrade is required by this milestone.

Use only this repository. Push your edits before the next milestone. Review/merge milestone PRs, then pull `main` locally. Keep `.env` private and ignored; never paste secrets into chat, browser code or Git.
