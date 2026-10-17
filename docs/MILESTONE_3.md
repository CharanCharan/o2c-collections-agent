# Milestone 3 — prevent overdue invoices and prioritize recovery

Current delivery: **PR #4**, extended to two models at Charan's request. M2 is learner-complete. M3 local checks pass; Charan's live M3 run/exercises remain pending. Only repository: CharanCharan/o2c-collections-agent.

## 1. Update your code and add the new examples

Review and merge https://github.com/CharanCharan/o2c-collections-agent/pull/4 . Stop Python with Ctrl+C. In your existing VS Code project terminal:

```powershell
git status
git switch main
git pull --ff-only origin main
```

Preserve/push local edits before pulling. Reuse your `.env`, Python environment and Supabase project.

In Supabase **SQL Editor**, paste and run **`sql/003_seed_pre_due.sql`**. This adds/restores three synthetic invoices; it changes no schema and does not delete history. Run it after the existing 001/002 setup. Dates are relative to `ca_demo_settings.as_of_date`: Harbor and Willow are due in seven days, Vista in fourteen. Re-running does not duplicate rows. It does not reset your original six invoices or their edits.

Restart:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000
```

Refresh http://localhost:8000 and click **Start**. No new API key or paid service is needed. Both trained artifacts are committed; ML packages are optional for retraining, not serving.

## 2. What you should see

With the original six rows restored and SQL003 run:

| Check | Expected |
|---|---|
| Invoice count | 9: six overdue, three before due |
| Open receivables | USD 431,700 |
| Past due | USD 372,200 |
| Eligible recovery exposure | USD 308,000 |
| Before-due balance | USD 59,500 |
| At seven-day preventive checkpoint | 2 invoices, USD 47,500 |
| Overdue reminder templates | 4; no actual emails |
| Completed stages / events | 6 stages / 13 events; one approval adds event 14 |

Choose **Stage → Before due · prevention**. Harbor shows about **71.9% becomes-overdue risk**; Willow about **14.7%**. Vista reports no matching prediction because it is fourteen days before due. Click Harbor to inspect its target, due-date horizon, inputs, contributions and model identity. Its overdue rule urgency is marked **Not overdue**.

Choose **Overdue recovery**. Cedar retains about **71.1% risk of still being unpaid another 30 days later**. Disputed Solace stays paused. The two percentages have different meanings; do not average them or describe one as proof of the other.

**Model evidence** shows separate training/holdout evidence for each model. Saved runs retain their own model parameters and results, even after source changes or retraining. M2 history opens without invented ML scores; the earlier single-model M3 history also remains readable.

## 3. Understand the two questions

| | Prevention model | Recovery model |
|---|---|---|
| When scored | Exactly seven days before due | Any positive overdue snapshot |
| Target | Not fully paid by end of due date | Outstanding balance remains at snapshot + 30 days |
| Example scoring date | 2026-10-17 | 2026-10-17 |
| Example horizon | Due 2026-10-24; check overdue on Oct25 | 2026-11-16 |
| Decision support | Review before the invoice becomes overdue | Prioritize recovery efforts |
| Output field | probability_overdue | probability_unpaid_30d |

The prevention model is not applied at arbitrary pre-due dates. At six days before due, due today, or fourteen days before due, this POC does not possess the required historical due-7 snapshot, so it reports no matching prediction. It does not reconstruct or backdate features. After the invoice becomes overdue, the recovery model applies. A future enhancement could store repeated dated snapshots and score at additional validated checkpoints.

Each run scores the actual source snapshot date, not your laptop clock. Source history counts are assumed known at that date. Neither model is independent confirmation of the other: they use related history and predict different events at different times.

## 4. Prediction versus business policy

- Prevention and recovery are **separate queues**, each ordered by balance × its own relevant probability. Queue order across stages is a display grouping, not a claim that the probabilities are comparable.
- Existing rule urgency remains for overdue invoices, controlling the current template threshold of 35. A probability is not an urgency score or confidence that an agent action is correct.
- Disputes, zero balances and other policy exceptions override contact eligibility. A pre-due prediction may be displayed for a dispute, but it cannot authorize a reminder.
- Pre-due results support **review only in M3**. Reminder drafting/approval remains in the overdue workflow; pre-due invoices cannot use its approval endpoint. M4/M5 can extend controlled reminder policy after the model demonstration.
- No LLM, actual email, payment reconciliation or cash-loss forecast is implemented here.

## 5. Follow the code

| Read in order | Responsibility |
|---|---|
| `ml/generate_pre_due.py` | 4,000 independent synthetic due-7 snapshots and later settlement observations |
| `ml/generate.py` | Separate 4,000 synthetic overdue snapshots and 30-day outcomes |
| `ml/train.py` | Stage-specific labels/features; chronological split, train-only scaling, validation selection, test evaluation |
| `artifacts/pre_due_risk.json` | Learned prevention parameters and measured report |
| `artifacts/payment_risk.json` | Existing learned recovery parameters and measured report |
| `backend/risk_model.py` | Shared scoring math, separate feature/target/artifact contracts and explanations |
| `backend/pipeline.py` | Route by invoice dates, preserve eligibility, score, rank separately, persist snapshots |
| `backend/main.py`, `runner.py` | HTTP/SSE and six-stage orchestration |
| `dist/app.js` | Stage filter, target labels, details and two model-evidence sections |
| `sql/003_seed_pre_due.sql` | Three online source examples, repeatable without deleting history |

Training happens offline before a visitor starts a run. Serving reads exported numeric JSON means/scales/coefficients/intercept and computes a sigmoid using Python's standard library. No runtime fitting, pickle loading or hosted model bill. JSON artifacts contain trained parameters; runtime invoices still come only from Supabase.

## 6. Features and label boundaries

Prevention features: prior late-payment rate, capped broken promises, log balance, no-history indicator. **Current-invoice days overdue is not a feature** because the invoice is not overdue at the fixed scoring point. The recovery model additionally uses overdue days.

Transformations: min(broken promises,4), log(1+min(balance,250000)), rate=late/previous (zero with a separate no-history flag), recovery days capped180. Outside synthetic ranges is flagged. No settlement dates, future outcomes, customer/invoice IDs or rule scores enter feature vectors. All prior history must already be known at snapshot. Real ERP integration would require dated events to verify that assumption.

Prevention label0 = fully settled on or before due date; label1 = settled after due or still outstanding. A payment dated on due date counts on-time; next-day payment counts overdue. Observations must extend through the following day. Snapshots not exactly due-7 are rejected by the trainer. Recovery labels require full observation through snapshot+30. Synthetic data assumes full settlement; partial payments/credits/write-offs need a richer real-world label definition.

Explanations show coefficient × standardized feature, relative to training feature means. Contributions plus intercept reconstruct log-odds; sigmoid converts that to probability. These are statistical associations, not causal effects or percentage-point changes.

## 7. Evaluation and limitations

The datasets are project-authored, independent synthetic records with invented noisy settlement mechanisms. They are not real ERP data, and neither includes the nine live demo invoices. Good results on a generator demonstrate a working engineering pipeline, not finance-business uplift or validated real-world probabilities.

Both use chronological splits with December2025/April2026 gaps. StandardScaler/model fit only on train. Select C from .1/1/10 by validation Brier; do not refit on validation/test. Test is an untouched later period. Constant baseline predicts training prevalence.

| Dataset | Train | Validation | Test | Embargo | Latest observation |
|---|---:|---:|---:|---:|---|
| Prevention, seed123 | 2,860 | 353 | 511 | 276 | 2026-09-08 |
| Recovery, seed42 | 2,887 | 390 | 500 | 223 | 2026-09-30 |

Training snapshots: Jan2024–Nov2025. Validation: Jan–Mar2026. Test: May–Aug2026. One unique invoice/customer per row, with labels matured before next split. Full provenance/hashes and environment are in each artifact.

| Test metric | Prevention baseline / model | Recovery baseline / model |
|---|---|---|
| ROC AUC · higher better | 0.500 / 0.738 | 0.500 / 0.808 |
| Average precision · higher better | 0.342 / 0.554 | 0.466 / 0.799 |
| Brier error · lower better | 0.225 / 0.195 | 0.249 / 0.180 |

Brier error also reflects discrimination, not calibration alone. Separate calibration bins show prediction/observed rates; calibration is imperfect. For prevention, the .8–1 bin has only six cases and averages .852 predicted versus .500 observed; do not overinterpret the tail. No real portfolio calibration, intervention impact or subgroup assessment is claimed. [Model card](../ml/MODEL_CARD.md) records the limitations.

## 8. Hands-on exercise — preventive source edit

Complete a full run and note Harbor's prediction. In Supabase:

```sql
update public.ca_invoices
set late_payments=0, broken_promises=0
where id='INV-10501';
```

Start a new run. Harbor's becomes-overdue prediction and preventive rank should fall. Financial totals stay unchanged. Reopen the original saved run: its input/prediction/model evidence must stay unchanged. Restore afterward:

```sql
update public.ca_invoices
set late_payments=8, broken_promises=1
where id='INV-10501';
```

Optional date-boundary exercise: change Harbor due to snapshot+6, then snapshot-1. At +6 there is no due-7 prediction; at -1 the recovery model is used. Each case requires a new run. Re-run SQL003 afterward to restore all three future examples, without touching old history. There is no automatic stored daily scoring history or scheduler in M3.

## 9. Train the models yourself — optional after first run

Stop Python before replacing artifacts. Install optional training dependencies in the existing virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-ml.txt

# Prevention
.\.venv\Scripts\python.exe -m ml.generate_pre_due
.\.venv\Scripts\python.exe -m ml.train --stage pre_due

# Recovery
.\.venv\Scripts\python.exe -m ml.generate
.\.venv\Scripts\python.exe -m ml.train
```

Open generated CSVs/manifests in `ml/data/`. They are reproducible and ignored by Git. Artifacts are committed. Generator metadata/hash must match the selected training stage. Default seeds:123prevention/42recovery. Changing a seed is an experiment, not a way to choose flattering test metrics; do not tune on test outcomes. Environment/path metadata and tiny numerical differences may change model identities. Restart Uvicorn after replacement; historical runs retain their original artifacts' parameters/evidence.

To discard only experimental model edits and restore the committed parameters (copy them first if you want to keep them):

```powershell
git restore -- artifacts/pre_due_risk.json artifacts/payment_risk.json
```

Restart Python. Commit/push any source experiments you wish to keep before the next lesson.

## 10. Checks and next checkpoint

Local Python3.12.14: **29 tests passed**, including previous persistence/policy checks, two-model routing, due-day/next-day label boundaries, fixed-window rejection, independent sklearn export parity, source sensitivity/immutable history, seed idempotence, disputes and truthful missing-model failures. HTTP/SSE + frontend DOM checks passed nine-row totals, separate model display, prevention/recovery filters, approvals and saved/legacy history. User Python3.13.5/live M3 setup still needs the run above.

Runtime needs existing requirements only. Full tests use optional Node/PGlite (`npm install --prefix tests`) for isolated SQL and requirements-ml for training parity; otherwise corresponding tests skip explicitly. One existing upstream Starlette/httpx deprecation warning remains.

Health verifies both artifacts and database readiness; missing/invalid artifact returns actionable503 and predict fails without silent single-model fallback. `/api/model` remains the recovery card; `/api/model/pre-due` is the prevention card. Saved-run `result.models` stores both. Supabase single-process, pause and secrets rules remain unchanged.

After learner M3 confirmation: M4 LLM drafting/fact validation and policy, M5 controlled sending/replies/followups, M6 public hosting, visitor editing afterward. Do not move ahead merely because tests pass.

Official technical references:

- https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html
- https://scikit-learn.org/stable/common_pitfalls.html
- https://scikit-learn.org/stable/modules/calibration.html
