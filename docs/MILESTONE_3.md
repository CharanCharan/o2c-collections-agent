# Milestone 3 — train, explain and use payment risk

M2 is learner-complete: Charan confirmed Supabase operation, source edits/immutable results, and restart persistence. M3 adds a genuine trained model; local tests are complete but Charan's M3 run/exercises remain pending. Canonical repository remains CharanCharan/o2c-collections-agent.

## Run the new milestone

Review and merge the M3 pull request. Stop Python with Ctrl+C. From your existing VS Code project terminal:

```powershell
git status
git switch main
git pull --ff-only origin main
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000
```

Preserve and push local edits before pulling. Reuse your existing `.env` and Supabase project. No new SQL migration, API key, paid service or runtime ML installation is needed. The trained artifact is included; Python serves its coefficients using standard-library math. Supabase remains the online source and history store.

Open http://localhost:8000 , refresh the page, and Start. Look for:

- Six stages, including **Predict payment risk**; 13 events on a completed run, 14 after one dry-run approval.
- A new **ML risk · 30 days** column beside the separate rule urgency.
- A **Model evidence** panel with a synthetic holdout comparison and calibration bins.
- Invoice detail with prediction horizon, actual feature values, model contributions, version and artifact hash.
- Existing USD 372,200 open AR / 308,000 eligible exposure / four template drafts when source rows are restored to the seed values.

With the committed model and original seed, Cedar shows about **71.1%**, Northstar **35.7%**, Meridian **25.9%**, BluePeak **24.6%**, Atlas **9.1%**, and disputed Solace **44.9%**. These are synthetic-trained estimates, not real-world validated probabilities. Solace stays paused. Opening an M2 run shows its original rule-based evidence, with no retroactive predictions.

Health: http://localhost:8000/api/health reports M3, six stages and model_version. Current model card: http://localhost:8000/api/model . A saved run's own model metadata is in its result; it may differ from the current artifact after retraining.

## What are we predicting?

At snapshot date **t**, an invoice already has a positive overdue outstanding balance. Target = **some outstanding balance remains at t + 30 days**. Label 1 means not fully settled by that horizon; label 0 means fully settled by it. Example: scoring on 2026-10-17 gives a horizon of 2026-11-16. The date comes from the saved snapshot, not the laptop clock.

The earlier plan suggested unpaid 30 days after due date. Many of our invoices are already past that date, so that would classify an outcome already known at scoring time. M3 uses a forward 30-day horizon from the snapshot instead. This keeps the prediction useful for an overdue collections queue.

This is not predicting exact payment date, amount recovered, customer creditworthiness, or the confidence that an AI action was correct. No payment reconciliation or partial-payment ledger is implemented. The synthetic generator assumes full-settlement outcomes; a production target would require audited balances/settlements and write-off treatment.

## Follow the code

| Read in order | What happens |
|---|---|
| `ml/generate.py` | Creates 4,000 independent synthetic historical invoice snapshots and later settlement observations |
| `ml/train.py` | Builds labels, splits by time, fits/scales on training only, chooses regularization on validation, evaluates holdout |
| `artifacts/payment_risk.json` | Learned means, scales, coefficients, intercept, metadata and measured reports |
| `backend/risk_model.py` | Shared feature transformations, artifact validation, logistic inference and contributions |
| `backend/pipeline.py` → `predict` | Scores the actual Supabase invoice snapshot; records date, horizon, inputs and model identity |
| `backend/pipeline.py` → `prioritize` | Ranks eligible balances using balance × predicted probability |
| `backend/runner.py`, `main.py` | Six-stage execution, persisted events/SSE, health/model endpoints |
| `dist/app.js` | Shows model evidence and selected invoice explanation |

Training is offline, done before the visitor clicks Start. Start does inference with the saved model, not retraining. There is no scikit-learn dependency in serving, no pickle loading, no hosted model fee, and no LLM yet.

## How the model learns

Scikit-learn `StandardScaler` + `LogisticRegression`, with five explicit inputs:

| Feature | Transformation at scoring time |
|---|---|
| Days overdue | min(days, 180) |
| Previous late-payment rate | late / previous; zero when no history |
| Broken promises | min(count, 4) |
| Balance | log(1 + min(outstanding USD, 250,000)) |
| No history | 1 if no previous invoices, else 0 |

All history is assumed known at snapshot time. Current counts cannot be reconstructed retrospectively from a real ERP without dated records; this synthetic setup assumes they are historical snapshots. No settlement date, future outcome, invoice/customer ID or rule urgency score is a feature. Dispute status is an explicit policy gate, not a learned permission to contact someone.

Training learns means/scales and coefficients. Serving computes:

`z = intercept + sum(coefficient × (feature - training_mean) / training_scale)`

`probability = 1 / (1 + exp(-z))`

Explanations show each feature's contribution to **log-odds relative to its training mean**. They are not percentage-point effects, causal claims, or private LLM reasoning. Contributions plus the intercept reconstruct the prediction. Inputs outside synthetic ranges are flagged; defined caps apply. Zero balances and invoices not overdue are not scored.

## Evaluate honestly

The seed-42 generator creates independent invoices/customers from an invented noisy settlement mechanism. It is authored for this project and contains no real customer data. Learning a generator is easier than handling real ERP processes: test results demonstrate engineering mechanics, not a successful collections intervention.

| Split | Snapshot dates | Rows | Purpose |
|---|---|---:|---|
| Train | 2024-01-01 to 2025-11-30 | 2,887 | Learn scaler and coefficients |
| Validation | 2026-01-01 to 2026-03-31 | 390 | Choose C from 0.1 / 1 / 10 using Brier error |
| Test | 2026-05-01 to 2026-08-31 | 500 | Report later-date holdout, no model selection |
| Embargo | December 2025 and April 2026 | 223 | Ensure 30-day labels mature before next split starts |

Outcomes observed through at most 2026-09-30; immature labels rejected. One invoice and customer per row avoids duplicate entity overlap. Scaler is fitted only on train; validation/test are transform-only. Selected model uses C=0.1 and is not refitted on validation/test. Comparison baseline predicts training prevalence for every invoice.

| Test metric | Constant baseline | Logistic model |
|---|---:|---:|
| ROC AUC (ranking; higher better) | 0.500 | 0.808 |
| Average precision (higher better) | 0.466 | 0.799 |
| Brier error (probabilities; lower better) | 0.249 | 0.180 |
| Top fifth observed non-settlement rate | 46.6% expected, no ranking | 84.0% |

84% is not model accuracy. It is the observed label rate among the top 100 ranked synthetic test invoices. Overall holdout prevalence is 46.6%. Brier measures probability error and is affected by discrimination as well as calibration; calibration bins are shown separately. For example, the 0.4–0.6 bin averaged 48.9% predicted versus 61.0% observed over 123 records. Calibration is imperfect; there is no claim of accurate real-world probabilities.

Full measured values and provenance: `artifacts/payment_risk.json`. [Model card](../ml/MODEL_CARD.md) records limits and training environment. Exported inference matches scikit-learn within 1e-12 on generated splits.

## Business decision versus prediction

- **Urgency** stays the documented policy score (aging, history, promises). It controls the existing template threshold of 35; this milestone does not redesign collection cadence.
- **ML risk** estimates non-settlement within the next 30 days under the synthetic training assumptions.
- **Priority index** changes to balance × ML probability, with eligible invoices first. This is risk-weighted exposure for ordering, not forecast cash loss or recovery.
- A dispute, zero balance or not-overdue invoice stays ineligible regardless of probability. Approvals remain dry-run only. A high model score does not authorize email or bypass policy.

## Hands-on exercise 1 — change a known input

Complete a seeded run and note Cedar's prediction. In Supabase SQL Editor:

```sql
update public.ca_invoices
set late_payments = 0, broken_promises = 0
where id = 'INV-10287';
```

Start a new run. Cedar's predicted risk and rule urgency should fall; its priority changes. Total open/eligible balances remain the same. With urgency below 35 it becomes monitored; the draft count falls to three. Reopen the first run: its original prediction, version and explanations remain saved.

Restore afterward:

```sql
update public.ca_invoices
set late_payments = 9, broken_promises = 2
where id = 'INV-10287';
```

## Hands-on exercise 2 — train it yourself (optional after first run)

Keep the serving artifact as your starting reference. Stop Python before replacing it. In the same virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-ml.txt
.\.venv\Scripts\python.exe -m ml.generate
.\.venv\Scripts\python.exe -m ml.train
```

Open `ml/data/synthetic_history.csv`: features describe the snapshot; settlement date/observation-through are later outcomes for labels. Generated data/manifest are reproducible and ignored by Git. The committed JSON artifact includes their hash, generator version, seed and metrics. A matching manifest is required by this synthetic-data trainer.

Inspect the chosen C and test report. Restart Uvicorn and compare `/api/model` with a new saved run. Change the generator seed (`--seed 43`), regenerate/retrain and observe changed estimates/metrics/model identity. This is an experiment, not a method for selecting a seed that yields a flattering test score. Do not tune on test results. Metadata and floating point differences across Python/library versions may change hashes or tiny output details.

To restore the original committed model when finished:

```powershell
git restore -- artifacts/payment_risk.json
```

This intentionally discards only your experimental artifact edits; keep a copy first if wanted. Restore the seed-42 data with `python -m ml.generate` if you changed it. Restart Python. Old runs retain their original predictions/metadata. Commit/push any changes you want to keep before the next lesson.

## Tests, errors and next step

22 tests passed locally on Python 3.12.14, including exported/sklearn parity, mature chronological labels, input sensitivity, independent risk/urgency ranking, immutable history, database persistence, policy gates and truthful model failure. Actual Uvicorn HTTP/SSE + DOM checks passed model display, six rows/13 events, approval/14 events and reopening history. Live cloud/Python 3.13.5 M3 verification awaits your run.

App tests: install requirements-dev and run pytest. SQL integration tests require optional Node/PGlite (`npm install --prefix tests`); the training parity test requires requirements-ml. Without those, affected tests skip explicitly. Neither Node nor ML packages are required to serve the app. One known upstream Starlette/httpx deprecation warning remains.

If artifact is missing/incompatible/changed without a matching identity, health returns an actionable 503. If a model fails mid-run, predict fails and later stages do not report success; no fallback to rule-only predictions. Restore the committed artifact or retrain. Existing Supabase configuration/pause and single-backend-process limits still apply.

After confirming your M3 run and exercise, M4 adds LLM drafting with invoice-fact validation and explicit review/fallback policy. Actual sending/replies remain M5; public hosting M6; visitor data editing after M6.

Official technical references:

- https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html
- https://scikit-learn.org/stable/common_pitfalls.html
- https://scikit-learn.org/stable/modules/calibration.html
