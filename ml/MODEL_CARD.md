# Payment-risk model card — M3

Purpose: educational collections POC. Predict an outstanding balance remaining 30 days after the scoring snapshot for a positive overdue invoice. Not a production credit or cash forecast model. Six Supabase demo invoices are inference examples, never training/evaluation rows.

## Provenance and artifact

- Project-authored synthetic generator: `ml/generate.py`, v1, seed 42, 4,000 independent customer/invoice observations. No outside/private data or dataset license obligations introduced.
- Data hash: `02a0ffbc8d61a77e804bc8a16175fa30a042b56eedc4a4723e56d9f3b0f6ef36`.
- Artifact model version: `ar-logreg-30d-v1-4e1935af6cbd`; actual SHA-256 returned by `/api/model` and persisted per run.
- Scikit-learn 1.9.1, Python 3.12.14, NumPy 2.5.4. Optional training dependencies are separate from serving dependencies.
- Trained means/scales/coefficients/intercept and full evaluation: `artifacts/payment_risk.json`. Numeric JSON inference; no pickled object. Model identity binds parameters and report; it is a consistency check, not a signature against a malicious repository author.
- Regenerate ignored data and manifest with `python -m ml.generate`; fit/export with `python -m ml.train`. No training during visitor runs. Metadata/floating-point differences can change identity across environments.

## Target and assumptions

Scoring date t is source snapshot as_of_date. Only positive overdue balances qualify. Label 1 = not fully settled by t+30; 0 = fully settled by that horizon. Labels require observation through t+30. Settlement dates/labels never enter features. No-history rate uses zero plus a separate indicator. Historical counts must be known at t; assumed in this generator, not independently auditable from the simplified live schema. A real implementation needs dated events and balances to enforce this.

Features: days overdue capped180; prior late-payment rate; broken promises capped4; log(1+balance capped250000 USD); no-history indicator. Amount below100, above250000, overdue above180, previous count above40 or promises above4 is outside declared synthetic support and warned. Fixed caps precede training/serving; StandardScaler learns only from train. Disputes are policy gates, not model features. Partial settlements, credits, write-offs, collector interventions and payment reconciliation are absent.

## Evaluation protocol

2,887 training snapshots Jan2024–Nov2025; 390 validation Jan–Mar2026; 500 untouched test May–Aug2026; 223 embargo rows excluded. December2025 and April2026 gaps allow 30-day labels to mature. Independent unique customers/invoices across all splits. Choose C from .1/1/10 using validation Brier; selected .1; no refit on validation/test. Constant baseline uses train prevalence, not test prevalence. Latest outcome observation Sep30 2026.

Test ROC AUC .807976 vs .5 baseline; average precision .798793 vs .466; Brier .180169 vs .249267. Top20% precision .84 vs prevalence .466. Baseline has no ranking, so its expected top20% rate is prevalence. Full bins show imperfect calibration (e.g. .489 predicted vs .610 observed in the middle bin). No post-hoc probability calibration or real-world calibration claim. Export probability difference from sklearn maximum 2.22e-16 on generated splits.

## Decision use and limitations

Priority = balance × predicted probability among eligible invoices, a ranking index. Policy urgency remains separate; existing threshold35 controls templates. Disputes always pause regardless of model output; zero/not-due balances not scored. A prediction never authorizes email. Contribution explanations are additive log-odds relative to training means, not causal effects or confidence in an action.

Synthetic labels are sampled from an invented noisy mechanism using overlapping signal types, so favorable scores are expected. Temporal tests do not simulate genuine ERP drift, collection-policy changes or economic shocks. No real outcomes, business uplift, subgroup fairness, interventions, portfolio calibration or cost benefit validated. Dates beyond the training window and new portfolios need validation. No runtime learning/drift monitor/retraining scheduler. Six synthetic demo invoices do not establish these properties.

Before real use: use permitted historical snapshots and reconciled settlement labels; ensure cutoff/maturity and customer/time split choices suit deployment; compare business baselines, evaluate probability calibration and group outcomes; test drift and intervention bias; define human ownership and validation/monitoring. This is future work, not required infrastructure for the throwaway POC.
