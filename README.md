# Charan's O2C Collections Agent

Canonical repository: https://github.com/CharanCharan/o2c-collections-agent

Milestone 2 reads six synthetic invoices directly from Supabase Postgres, validates them, calculates collection urgency, prioritizes accounts and prepares reminder templates. Real backend events stream to the browser. Runs, input snapshots, events and dry-run approvals survive Python restarts.

Scores are policy rules, drafts are templates, and approval sends no email. ML, LLMs, real email and public deployment remain later milestones. This app currently runs locally; the earlier hosted presentation prototype is separate.

## Start here

Follow [Milestone 2 setup and exercise](docs/MILESTONE_2.md): run the two SQL scripts in your own Supabase project, create a private local `.env`, install dependencies, then start Python. The database password is not used by this app. The backend uses a project URL and server API secret.

After database and environment setup, from the repository root in Windows / Anaconda:

```powershell
# Only create the environment if it does not already exist:
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000
```

Open http://localhost:8000 . Health: http://localhost:8000/api/health . API explorer: http://localhost:8000/docs . Direct environment Python avoids PowerShell activation-policy issues; no extra Python installation is needed. On macOS/Linux use `.venv/bin/python` instead.

Expected seeded output: USD 372,200 open AR, USD 308,000 eligible exposure, four template drafts, one monitored invoice and one paused dispute. Fixed snapshot date: 2026-10-17.

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
| `tests/` | Storage, API and actual PostgreSQL-function checks |

- [Project knowledge](PROJECT_KNOWLEDGE.md): implementation contracts and continuation context.
- [Project plan](PROJECT_PLAN.md): scope, learner progress and future milestones.
- [M2 checklist](docs/MILESTONE_2_PLAN.md): implementation versus learner verification.
- [M1 guide](docs/MILESTONE_1.md): historical first-backend lesson.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

The ten SQL integration tests use optional Node.js and an isolated PostgreSQL/WASM engine. To run them too, install Node.js then run `npm install --prefix tests` before pytest. Without that dependency they are skipped; four storage tests still run. Node is not needed to run the application. Tests do not access your live Supabase project.

## Boundaries and shared workflow

Run one backend process per database, with no multiple Uvicorn workers. Restart marks abandoned active runs interrupted; completed history stays saved. This is persistence, not a durable job queue. Saved-run controls list the latest 20; older runs remain in the database.

This is a small local POC without production authentication. Use only synthetic data. Visitor data editing is deferred until after M6. Supabase Free can pause after inactivity; check/resume before demos. No paid upgrade is required by this milestone.

Use only this repository. Push your edits before the next milestone. Review/merge milestone PRs, then pull `main` locally. Keep `.env` private and ignored; never paste secrets into chat, browser code or Git.
