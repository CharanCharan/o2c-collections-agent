# Collections Agent — hands-on source

Start with PROJECT_PLAN.md. It records the goal, stack, milestones, current limitations, and last learning checkpoint.

## Included now

- `dist/index.html`: complete current website; HTML, CSS, sample invoices, and JavaScript together.
- `PROJECT_PLAN.md`: agreed implementation and learning roadmap.
- `AGENTS.md`: instructions for an assistant working on this project.
- `.gitignore`: excludes local secrets and generated development files.

No backend has been implemented yet. This package is the starting UI prototype, not a completed agent.

## First hands-on lesson — run and edit the page

1. Extract this ZIP into a folder named `collections-agent` on your computer.
2. Open that folder in VS Code. Open a terminal in the project root (the folder containing README.md).
3. Check Python:

   Windows: `py --version`

   macOS/Linux: `python3 --version`

4. Serve the website:

   Windows: `py -m http.server 8000 --directory dist`

   macOS/Linux: `python3 -m http.server 8000 --directory dist`

5. Open http://localhost:8000 in your browser, then click Start collections run.
6. In VS Code, open `dist/index.html`. Find `Collections command center` and change it to `Charan's Collections Agent`.
7. Save and refresh the browser. Your heading should change. Stop the server with Ctrl+C when done.

The local Python HTTP server only serves files. It does not yet execute an agent or provide application API endpoints. Do not expose this development server to the public internet.

## How the current code works

Use VS Code search to jump to these names:

| Code | Responsibility | What to learn |
|---|---|---|
| `<style>` | Page layout, colors, responsive behavior | CSS controls appearance |
| `baseInvoices` | Six sample invoice objects | Data is currently hard-coded |
| `renderQueue()` | Creates the visible invoice rows | JavaScript renders data into the DOM |
| `renderDetail()` | Shows the selected invoice and reminder | Draft is a template, not an LLM call |
| `run()` | Schedules the demonstration sequence and sorts invoices | `setTimeout` is simulated timing, not backend execution |
| `addEvent()` | Adds a message to the activity feed | UI event renderer; messages are currently prewritten |
| `logDryRun()` | Marks a simulated reminder action | No email provider is called |
| `simulateReply()` | Adds a sample reply message | No inbox integration is present |

The supplied file preserves the deployed prototype. Long lines are an artifact of its initial creation; use editor formatting if useful. We will separate frontend files while learning, rather than hiding that change in this handoff.

## Source ownership and deployment

You can put these portable source files in a repository in your own GitHub account. The package deliberately excludes managed-host identity, Git metadata, deployment archives, and credentials. It can be deployed independently.

To host only this current UI on Render: create a Static Site connected to your repository, use `dist` as the publish directory, and leave the build command empty. This deploys the simulation only.

The planned real POC will instead be one Python/FastAPI Web Service serving both this frontend and `/api/...` routes. The backend files and deployment commands will be added in the next lessons, not assumed to exist now. Render's FastAPI guide is https://render.com/docs/deploy-fastapi .

## Proposed later layout — not implemented yet

| Path | Future purpose |
|---|---|
| `backend/main.py` | API routes, static frontend, event streaming |
| `backend/orchestrator.py` | Collections run and tool calls |
| `backend/services/` | Ingestion, risk, email, and reply handlers |
| `backend/models/` | Data validation and event schemas |
| `data/` | Documented sample data and generation scripts |
| `ml/` | Model training and evaluation |
| `requirements.txt` | Python dependencies |
| `.env.example` | Names of required secrets, without values |

## Your next checkpoint

Run the page locally and make the heading edit. Report the Python version and whether your changed heading appears. If anything fails, share the error text without keys or passwords. Then continue M1 from PROJECT_PLAN.md.
