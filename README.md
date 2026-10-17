# Charan's O2C Collections Agent

Canonical repository: https://github.com/CharanCharan/o2c-collections-agent

M1 connects the website to a real Python workflow. It loads six synthetic invoices from JSON, validates them, calculates rule-based collection urgency, prioritizes accounts, and prepares reminder templates. The browser receives actual backend events through Server-Sent Events (SSE).

ML predictions, LLM generation, email, external ingestion and persistent storage remain later milestones. M1 needs no API keys and makes no external API calls.

## Run locally — Windows / Anaconda

Stop your old HTTP server with Ctrl+C. From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000
```

Calling the environment's Python directly avoids PowerShell activation-policy issues and leaves your Anaconda base packages unchanged. No second Python installation is needed.

Open http://localhost:8000 and click **Start collections run**. The health endpoint is http://localhost:8000/api/health and the API explorer is http://localhost:8000/docs . The same server serves the page and the API.

On macOS/Linux, create the environment with `python3 -m venv .venv`, then use `.venv/bin/python` in place of `.\.venv\Scripts\python.exe` above.

## Learn and verify

- [Project knowledge](PROJECT_KNOWLEDGE.md): current implementation, decisions, formulas, API contracts, learner checkpoint and troubleshooting.
- [Milestone 2 checklist](docs/MILESTONE_2_PLAN.md): planned database and ingestion work; not implemented yet.
- [Milestone 1 guide](docs/MILESTONE_1.md): expected results, code map, event flow and an input-edit exercise.
- [Project plan](PROJECT_PLAN.md): scope, decisions, progress and remaining work.
- [Working instructions](AGENTS.md): instructions for continuing this project.

Expected sample output: USD 372,200.00 open AR, USD 308,000.00 eligible exposure, four reminder templates, one monitored invoice, and one paused dispute. Snapshot date: 2026-10-17.

## Code map

| File | Responsibility |
|---|---|
| `dist/index.html` | Page layout and styling |
| `dist/app.js` | Requests, live events and rendering |
| `backend/main.py` | API routes and frontend hosting |
| `backend/runner.py` | Run IDs, orchestration, isolation and event history |
| `backend/pipeline.py` | Finance calculations, policy rules, priorities and templates |
| `backend/models.py` | Source validation |
| `data/invoices.json` | Editable synthetic AR data |
| `tests/test_milestone_1.py` | API and business-behavior checks |

Run history and approvals are held in process memory and clear on restart. Python edits with `--reload` restart the server. M2 adds Postgres persistence. M1 is for local learning; public deployment and its access/usage controls remain M6.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

## Shared-code workflow

Use this repository for all work. Push local changes before asking for the next milestone. Changes arrive through milestone branches and pull requests. After merging, pull `main` locally. Check `git status` and the commit ID before the lesson. The earlier duplicate repository is not used.

