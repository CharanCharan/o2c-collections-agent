# Milestone 2 — connect your Supabase database

Implementation is ready for review in PR #3. Local automated checks passed; your live Supabase connection and learning exercises are still pending. Use your existing project. Do not create another repository or another Python installation.

## 1. Synchronize code

Review and merge https://github.com/CharanCharan/o2c-collections-agent/pull/3 . In VS Code's terminal, from the existing project folder:

```powershell
git status
git remote -v
git switch main
git pull --ff-only origin main
```

`origin` must point to `CharanCharan/o2c-collections-agent`. If you have uncommitted edits, commit/push them first; do not discard them. Stop the current server with Ctrl+C before restarting with new dependencies/configuration.

## 2. Create tables and seed invoices

In your Supabase project's **SQL Editor**, open a new query:

1. Copy the complete contents of `sql/001_schema.sql`, paste and run. This creates five `ca_` tables and the backend functions/permissions.
2. In another query, paste and run `sql/002_seed_demo.sql`. This seeds the fixed date and six synthetic invoices.
3. Open **Table Editor → ca_invoices**. You should see six rows. Alternatively run:

```sql
select count(*) from public.ca_invoices;
select public.ca_health();
```

Expected: count 6; health contains schema_version 2 and seeded true. Schema creates project-specific prefixed objects; seed uses upserts. Re-running the seed restores those six source records without duplicate IDs and does not erase saved runs. It does not remove extra rows you manually added. Source edits are owner-only through Supabase for now.

## 3. Configure the backend privately

From the repository root:

```powershell
Copy-Item .env.example .env
```

Do this once; if `.env` already exists, edit it rather than overwrite your settings. Open `.env` in VS Code. Fill these two values locally:

```dotenv
SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
SUPABASE_SECRET_KEY=YOUR_SERVER_SECRET_KEY
```

- Copy the **Project URL** from the project's Connect dialog or API settings. Use the HTTPS project URL, not a Postgres connection string.
- Under **Settings → API Keys**, copy/create a **Secret key** (`sb_secret_...`) for this backend. If using legacy keys, the server `service_role` key is supported. A publishable or anon key is insufficient.
- Your **database password is different** and is not needed for this HTTPS connection. Do not paste it or API secrets into chat.
- `.env` is ignored by Git. Only blank `.env.example` is committed. Secrets stay in Python; none are sent to the website. Modern secret keys go in the `apikey` header, not a Bearer token; `storage.py` handles this.

Official key guide: https://supabase.com/docs/guides/api/api-keys . Restart Python whenever you change `.env`; existing terminal environment variables take precedence over file values.

## 4. Install and run

Reuse the existing `.venv`:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000
```

If the environment is missing, first run `python -m venv .venv` from your Anaconda-enabled terminal. Open http://localhost:8000/api/health . Expected fields include `status: ok`, `milestone: M2`, `storage: supabase_postgres`, `invoice_count: 6`.

Open http://localhost:8000 and click **Start collections run**. Expected: USD 372,200 open AR, USD 308,000 eligible exposure, six invoices and four drafts. You should see 11 stored events. Approve an eligible template as a dry run: it adds one interaction/event and sends no email.

## 5. Prove that it is a database workflow

### Exercise A — source edit and immutable history

Complete a run and note its ID. In Supabase SQL Editor run:

```sql
update public.ca_invoices set amount = 96400.00 where id = 'INV-10482';
```

Start a new run. Open AR should be **382,200**, eligible exposure **318,000**. Reopen the earlier run through Saved runs: its original totals must stay unchanged. This proves each run stores its own input/result snapshots.

Restore the amount afterward:

```sql
update public.ca_invoices set amount = 86400.00 where id = 'INV-10482';
```

### Exercise B — persistence and duplicate protection

Approve one eligible dry-run draft. Note the run ID. Stop Python with Ctrl+C, restart with the same command, refresh the website, choose the run from **Saved runs**, and open it. The same result and approval should still appear. Clicking approval again must not create a second interaction. Different runs have independent approval state.

You can inspect `ca_runs`, `ca_run_events`, and `ca_interactions` in Supabase. The dropdown lists the latest 20 runs; listing fewer rows does not delete older history.

### Explain it back

Trace one run: browser POST → Python orchestration → Supabase source snapshot → validation/rules → committed events/results → SSE → website. Explain why editing source does not rewrite old results, and why storing history does not automatically resume a crashed job.

## What changed and why

M1 read a local JSON file and forgot history on restart. M2 replaces both with Supabase Postgres through a small server-side HTTPS adapter. SQL functions keep event append/state updates and approvals transactional. The browser renders committed outputs; failed database operations cannot masquerade as successful ingestion. There is no runtime JSON fallback.

| Piece | Read it to understand |
|---|---|
| `storage.py` | Credentials, HTTP RPC calls, sanitized database errors |
| `runner.py` | Stage sequence, actual source read, persist-before-success |
| `001_schema.sql` | Row locks, permission boundaries, event ordering, approval deduplication |
| `pipeline.py` | Existing finance rules; canonical source hash and validated snapshot |
| `main.py` | HTTP endpoints and SSE replay from database |
| `app.js` | Live events and saved-run reopening |

## Limits and troubleshooting

- One backend process per database. No multiple workers or simultaneous independent development servers using the same project. Startup marks other-process unfinished runs interrupted. Completed history remains; interrupted jobs are not automatically resumed.
- The source is online but synthetic. Urgency is a rule, not ML; drafts are templates, not LLM output; approvals are dry-run records, not email. Later milestones add those capabilities.
- Missing `.env`, schema or seed: health returns an actionable 503 and Start stays unavailable. Complete setup and restart. No local fallback is used.
- Wrong/insufficient API key: use backend secret/service_role, not publishable/anon. Never expose it in screenshots.
- Project paused/network unavailable: resume/check Supabase and retry. Free projects can pause after one week of inactivity; manually check before interviews. Pricing reference: https://supabase.com/pricing .
- Run interrupted after reload/crash: start a new run. Inspect the old failure record for evidence; do not claim it resumed.
- No rows/history in the page: check health, selected project URL and whether SQL ran in that same project.
- Public access, authentication/usage controls and deployment remain M6. Visitor data-edit controls remain after M6.

## Validation evidence and next checkpoint

Assistant validation on Python 3.12.14: 14 tests passed, including actual SQL execution in isolated PGlite PostgreSQL/WASM (not a live Supabase account). Real local HTTP/SSE plus frontend DOM checks passed Start, results, approval and saved-run reopening. SQL tests cover persistence across app restart, source changes, snapshots, approvals, SSE resume, permission restrictions, abandoned runs and database errors. Syntax checks passed.

Your Python 3.13.5 and actual Supabase gateway/key/schema configuration still need the steps above. After you report Exercise A/B results, update learner completion and move to M3. M3 first defines a payment-risk target, prediction time and suitable historical training data; six demo invoices are not enough to validate a useful model.
