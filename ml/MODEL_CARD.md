# M3 model cards — prevention and recovery

Educational collections POC, two separate probability targets. Trained/evaluated on **synthetic history only**, no actual customer or business-uplift validation. Neither model independently confirms the other's predictions; do not combine their probabilities.

## Prevention — due-7 checkpoint

- Target: invoice not fully settled by end of due date; predict exactly seven days before due. Settlement on due date is on-time; next-day settlement is late. Observation must extend through due+1day. No arbitrary-day pre-due inference/backdating of features.
- Artifact: `artifacts/pre_due_risk.json`; model `ar-predue-7d-v1-5f467038df08`.
- Project-authored generator `ml/generate_pre_due.py v1`, seed123, 4,000 independent invoices/customers. Source hash `e01d656ea50157b8cbd9ab22d4d4ea80f6db24cfbcd87e576725b08d73c6aa21`. Observation cutoff2026-09-08.
- Features: prior late-payment rate; broken promises capped4; log(1+balance capped250000USD); no-history indicator. No current-invoice overdue days, future payments, IDs or urgency score.
- Train2,860; validation353; test511; embargo276. Selected C10 by validation Brier.
- Test AUC .738486 vs .5 constant; AP .553646 vs .342466; Brier .194845 vs .225192. Tail calibration uncertain: six predictions in .8–1 bin, .852 mean predicted vs .500 observed. No real calibration claim.
- Decision: rank preventive reviews within stage by balance × probability_overdue. M3 does not allow pre-due reminder approval through the overdue approval tool.

## Recovery — overdue snapshot

- Target: positive overdue balance remains at snapshot+30days; mature outcomes required.
- Artifact: `artifacts/payment_risk.json`; model `ar-logreg-30d-v1-4e1935af6cbd`, unchanged from initial M3.
- Generator `ml/generate.py v1`, seed42, 4,000 independent snapshots. Data hash `02a0ffbc8d61a77e804bc8a16175fa30a042b56eedc4a4723e56d9f3b0f6ef36`. Observation cutoff2026-09-30.
- Features: prevention's four plus overdue days capped180.
- Train2,887; validation390; test500; embargo223. Selected C.1 by validation Brier.
- Test AUC .807976 vs .5; AP .798793 vs .466; Brier .180169 vs .249267. Middle-bin calibration .489 predicted vs .610 observed (n123). Not validated on real receivables.
- Decision: eligible-first recovery ranking by balance × probability_unpaid_30d. Policy urgency still controls the threshold35 draft rule. Disputes always pause regardless of risk.

## Shared engineering and statistical boundaries

Training Python3.12.14/scikit-learn1.9.1/NumPy2.5.4. Numeric JSON export, no pickle. Export matches independent sklearn inference to 1e-12. Exact reports, learned parameters, versions and source/artifact hashes are persisted per run, so later retraining cannot rewrite history. Version binds payload for consistency, not cryptographic authenticity against a malicious author.

Train snapshots Jan2024–Nov2025; validation Jan–Mar2026; test May–Aug2026; December2025/April2026 gaps allow outcome maturity. StandardScaler/model fit only on train; C selected among .1/1/10 using validation, no refit on validation/test. Constant baseline uses train prevalence. One unique customer/invoice per row avoids entity duplicates; real repeated-customer use needs a suitable grouping/time design. Synthetic generators and datasets are independent of the nine source demo invoices.

Prior history/amounts are assumed known at scoring time; the simplified source schema cannot audit that assumption. No-history defaults rate0 with a separate flag. Fixed clipping and out-of-support warnings disclosed. Contributions are additive standardized log-odds relative to training means, not causal effects, percentage-point changes, confidence in an AI action or expected cash recovery.

Synthetic settlement mechanisms deliberately contain the signal types available to the models; favorable test results are not evidence of real ERP accuracy. Full-settlement labels simplify partial payments, credits, write-offs and collector interventions. No macro drift, fairness, intervention effect, economic benefit or real calibration validated. A real deployment requires permitted dated snapshots/reconciled outcomes, mature labels, appropriate temporal/group splits, business baselines, calibration/group/drift evaluation and owner review.

Serving never retrains, stores no scheduled historical pre-due scores and runs one backend per demo database. Dates outside the fixed pre-due window are explicitly not scored; overdue model starts only after due. Zero balances not scored. Both artifacts are required for a new dual-model run; failures never silently substitute the other model or urgency rules. Older saved M2 and single-model M3 results remain unchanged/readable.

Reproduce both datasets/training using docs/MILESTONE_3.md. CSV/manifests ignored/reproducible; artifacts tracked. Metadata/floating-point differences can change identities across environments. No real private dataset, license dependency, paid model endpoint or new runtime ML dependency introduced.
