---
document_role: implementation_knowledge_and_session_handoff
repository: CharanCharan/o2c-collections-agent
updated: 2026-10-17
implementation_milestone: M4_language_tools
implementation_branch: milestone-4-llm-drafting
implementation_status: ready_for_review_not_learner_verified
learner_status: M3_merged_user_reported_done_normal_run
pending_learning_check: M4_SQL004_template_and_live_API_reply_review
next_milestone: M5_controlled_email_and_replies
---

# Project knowledge — continuation context

## Current M4 checkpoint — supersedes historical M3 setup notes below

M3 PR#4 merged f3acb263a4ce64d35e534d77136a8158eac3f6b5. User said "done next step please"; record normal setup/run reported, not independent proof of optional source-edit/retraining mastery. M4 is prepared on milestone-4-llm-drafting, learner/cloud/OpenAI checks pending. Read docs/MILESTONE_4.md first. Canonical repo only; preserve edits and user merge/pull workflow.

M4 keeps both models and overdue eligibility unchanged. It adds backend/language.py: explicit draft_reminder and classify_reply tools via OpenAI Responses POST https://api.openai.com/v1/responses. Model gpt-5.6-luna, reasoning none, JSON Schema strict, store false, max output1024, timeout30sec, no retries. Checked current official docs on2026-10-17. Request includes only bounded facts/fixed sample text, no keys in input/browser/logs. Lazy HTTP client avoids initializing paid-provider transport in disabled mode. No live API key obtained, no paid requests made by assistant.

Opt-in: COLLECTIONS_LLM_ENABLED=true plus private OPENAI_API_KEY in existing ignored.env. Default false makes no API calls and labels template_no_llm. Do not overwrite existing Supabase.env. Fixed code caps4draft attempts/run,20total attempts/process (includes replies). Lock protects aggregate count; resets on restart and is not account/public spending control. Model/caps explicit code, no arbitrary browser override. Official price listed $.20/Minput,$1.20/Moutput: illustrative4×(1000input+500output)=$.0032, actual usage differs. API billing separate from subscription. Provider account access/quota not verified. No paid hosting/database upgrades added.

Draft workflow first builds existing Python templates; policy-ineligible/disputed/pre-due/monitor rows skip provider. If enabled, call once per eligible draft subject to caps. Structured Facts must exactly match saved invoice_id,amount,currency,due_date,as_of_date; strict opening/request/closing bounds. Numeric/date/currency/payment-route and selected unsupported policy/payment-claim prose guards. Python builds subject,greeting,fact block,signature, LLM supplies short nonfinancial phrasing. Keyword guards are not semantic correctness proof: human review always. No actual send. Valid generation_mode=llm_assisted_validated_facts; failed/config/missingkey/refused/incomplete/invalid/capped output retains template_fallback_no_llm_approval with redacted reason/review_required. Disabled template_no_llm never claims generation. No fallback to fake provider success.

Persist row.draft_audit: status,tool,provider,requested/returned model,prompt/validator versions,facts,input/output hashes,response ID,usage,duration,API-attempt flag when known. No raw provider error bodies/keys. context/result.drafting stores mode/counts/config. Six stages stay; enabled eligible tools add llm_draft started/completed or warning events, each with committed result snapshot.4eligible calls →21events instead13, approval adds1. Warnings do not stop run; actual database failure still stops. Disabled13events. Workflow_version M4, renderer supports oldM2/M3/M4; never rewrite history.

SQL004 is additive backend-only ca_language_health + ca_record_reply_example(uuid,text,text,jsonb). No new tables/action constraints/data deletion. Health/start initialization require readiness, preventing paid run before required schema. Reply RPC locks completed run, verifies invoice, dedupes example_id in row.reply_reviews, atomically appends event+result. No changes to balance, eligible, dispute, contacted or payment fields. Same run/invoice/example reopens review; per-process reply_lock avoids concurrent duplicate calls. Provider call and DB write cannot be one distributed transaction: a failed write after paid response can charge again on retry; do not claim exactly-once billing.

Fixtures/replies.json has5synthetic cases: promise,paidclaim,dispute,documents,injection. Browser selects fixed example, no visitor data editor/arbitrary reply endpoint. GET /api/reply-examples returns inputs without expected test labels. POST /api/runs/{UUID}/invoices/{id}/classify-example accepts only example_id, requires completed run. Unknown404, extra fields422. Returned strict intent+literal evidence+optional promise fields; date future/literalISO,amountliteral2decimalpositive≤balance, promise fields only for promise intent. These support extraction, not prove intent correctness. Always review_required/simulated_input, invoice_payment_updated=false. Disabled/provider-invalid/capped =>manual_review,classificationnull. Actual email/webhooks/promises/followup scheduling remain M5; a claim paid is not reconciliation. Reviews persist as result row map and reply_classification event; repeat after enabling still returns old review, use new run to re-evaluate.

New API health includes language.enabled/key_configured/provider/model/caps/counter without key, plus existing models/source. New.sql readiness errors actionable503. UI LLM/TEMPLATE/FALLBACK badges, tool evidence, fixed sample reply display. Runtime requirements unchanged. Tests autouse fixture forces paid API off/empty key even with learner.env, injected httpx mocks only.42localtests passed; real local HTTP/SSE/DOM template+mock-provider modes cover labels/reviews/dedup/history. No live provider or learnerPython3.13.5/cloudSQL004 proof. Existing Starlette/httpx warning remains. Full SQL/training tests optional deps as before.

Next learner checks: merge/pull M4, SQL004, template run, privately configure billing/key+enable, successful live draft/usage evidence, paid example leaves invoice unchanged, duplicate does not call again, restart/history. Do not mark live success from mocks or a fallback badge. Optional M3 exercises remain unconfirmed.

Next M5 TODO: select controlled outbound provider/test recipient and sender/domain policy, explain cost before requirements; server allowlist/approval/idempotency before send; provider IDs/delivery events; signed inbound webhook+thread match; structured human-reviewed promises/disputes and followup audit/scheduling; payment claim never closes invoice without reconciliation. Provider secrets local/server only. No publishing until M6 auth/quotas/cost controls. Visitor editing afterM6. Update knowledge/plan with actual code and learner evidence.

## Historical M3 contracts and model background (unchanged unless overridden above)

## Read first / delivery agreement

Canonical repository https://github.com/CharanCharan/o2c-collections-agent . Read this file, PROJECT_PLAN.md, docs/MILESTONE_3.md and current code before changes. One complete runnable milestone per branch/PR, then explanation/exercise. Charan reviews/merges/pulls/runs/edits; do not merge for him. Preserve/push his edits before next work. Documents are explicit handoff context, not automatic memory in unrelated sessions. Verify current refs and PR state; documents do not prove a PR merged.

Goal: publicly shareable interview O2C POC showing genuine backend actions and inspectable evidence. User must own/edit/explain source. Preserve ingest→validate/exceptions→assess/predict→prioritize→draft→controlled send→replies/promises/followups→audit. No unrelated source connectors, extra agents or production infrastructure detours.

## Last learner checkpoint and latest scope decision

- Windows VS Code from Anaconda Prompt, Python3.13.5; `python` works, `py` unavailable. Use `.venv\Scripts\python.exe` directly to avoid PowerShell activation issues. Git/auth/identity configured.
- M0 complete, M1 normal run confirmed. Its unconfirmed JSON-edit exercise was superseded by M2 DB edit.
- M2 PR#3 merge ea7a5fb7c3d1d2747c35182c97d4280f63f70d2f. User confirmed Supabase operation, source edit with immutable history, restart/approval persistence. Learner-complete based on his report, not assistant live-cloud access.
- M3 initial single-model PR#4 head76aa354 added overdue recovery. PR was still open/unmerged when this extension started. User explicitly requested predicting becoming overdue first, retaining recovery as additional decision support; approved extending M3 before M4. Continue same branch/PR if still open, never silently merge. Inspect status if user merged during work.
- M3 includes two models and SQL003 examples; user later reported done/next. Optional deeper exercises unconfirmed; current M4 checks above are pending.
- Only canonical repo. Duplicate CharanCharan/collections-agent unused; user handles deletion, not verified. M1 merge af9944b; docs PR#2 merge692f03d.
- Old static URL https://collections-agent-live-demo.blithecomet33.chatgpt.site/ is a presentation prototype. Current Python/Supabase/ML app is local; public hosting M6, not silently deployed through Sites.

## POC constraints

Throwaway/free-first. Supabase Free (hosted Postgres) is sole online invoice source/history store. Runtime invoice JSON removed. Source seeds SQL002(original6) + optional SQL003(3future). Offline synthetic training CSVs are separate from runtime ingestion. No CSV invoice importer, arbitrary connector, normalized finance ledger, second DB or paid plan. Owner edits via Supabase allowed; visitor editing only afterM0–M6.

Free projects may pause; manually check/resume before demos, no keepalive/always-on promise. Secrets server-side in ignored.env; backend uses project URL/API secret, not DB password. No secrets received or live-cloud verification by assistant. Single backend process per DB; saved history durable, jobs not automatically resumed. UUID isolation is not authentication; public access/caps remain M6. No real email without controlled recipients/explicit integration.

## Two model contracts — do not conflate

| | Prevention | Recovery |
|---|---|---|
| Scoring point | Exactly7days before due | Positive overdue snapshot |
| Target | Not fully paid by end of due date | Balance remains at snapshot+30days |
| Inference field | probability_overdue | probability_unpaid_30d |
| risk_type | pre_due_overdue | overdue_30d |
| Artifact | artifacts/pre_due_risk.json | artifacts/payment_risk.json |
| Version | ar-predue-7d-v1-5f467038df08 | ar-logreg-30d-v1-4e1935af6cbd |
| Features | late_rate, broken_promises_capped, log_balance, no_history | Same plus days_overdue_capped first |
| Model endpoint | /api/model/pre-due | /api/model (backward compatible) |

Neither model is independent proof of the other; related predictors, different stages/outcomes. Do not combine/average/compare probabilities across targets. Prevention/recovery queues rank separately by balance×their own probability. Sorting recovery bucket first is display grouping, not a global economic comparison. Index is risk-weighted exposure, not cash-loss/recovery forecast.

Prevention only scores when due−snapshot=7days. Other nonoverdue dates return explicit not_scored/no matching historical snapshot; no backdating/reconstruction. Due today not scored; once overdue, recovery model applies. Positive balance required. A pre-due dispute can show risk but preventive_eligible=false and reminders paused. Pre-due is review-only in M3: eligible remains false; no template/approval through overdue tool. M4/M5 can extend controlled policy. No scheduled daily scoring or stored due-7 score lookup.

Source as_of_date is scoring t, not laptop date. Pre target due end, outcome_check_date=due+1; payment on due is label0, next day is label1. Adequate observation through due+1 required. Recovery horizon t+30 and observation through it required. Synthetic full-settlement assumption excludes partial ledger/credits/writeoffs. Real deployment needs dated reconciled snapshots/outcomes.

Feature transformations: late/previous (0 with separate no-history flag); min(promises,4); log1p(min(balanceUSD,250000)); recovery min(overdue_days,180). Pre-due excludes current-invoice overdue aging, IDs/urgency/future settlements. History assumed known at snapshot; simplified schema cannot audit historical availability. Outside support warned: amount<100/>250000, previous>40, promises>4; recoverydays>180. Fixed caps precede train/serve; no-history disclosed.

## Training and evidence

Separate project-authored synthetic datasets,4,000 unique customer/invoice snapshots each. No real or private records; neither includes the9live demo invoices. Invented noisy mechanisms encode the signal types; favorable metrics demonstrate ML engineering, not real ERP accuracy/business impact.

| | Prevention | Recovery |
|---|---|---|
| Generator / seed | ml/generate_pre_due.py v1 /123 | ml/generate.py v1 /42 |
| Source SHA256 | e01d656ea50157b8cbd9ab22d4d4ea80f6db24cfbcd87e576725b08d73c6aa21 | 02a0ffbc8d61a77e804bc8a16175fa30a042b56eedc4a4723e56d9f3b0f6ef36 |
| Train / validation / test / embargo | 2860/353/511/276 | 2887/390/500/223 |
| Latest outcome observation | 2026-09-08 | 2026-09-30 |
| Selected C | 10 | .1 |
| Test AUC model / baseline | .738486/.5 | .807976/.5 |
| Test AP model / baseline | .553646/.342466 | .798793/.466 |
| Test Brier model / baseline | .194845/.225192 | .180169/.249267 |

Chronological train snapshotsJan2024–Nov2025, validationJan–Mar2026, untouched testMay–Aug2026. EmbargoDec2025/Apr2026 allows labels to mature. Unique independent entities avoid duplicate customer leakage. ml/train.py uses stage-specific labels/features; requires matching generator/hash manifest, rejects immature labels and wrong pre-due date. Fit StandardScaler+LogisticRegression only on train, choose C among .1/1/10 by validation Brier, no refit on validation/test. Constant baseline predicts train prevalence. Test never used for model selection.

Calibration imperfect: pre tail has6cases/.852mean predicted/.500observed; recoverymiddle n123/.489predicted/.610observed. Brier includes probability/discrimination effects; bins shown separately. No claims of real calibration, intervention uplift, fairness or drift resilience. See ml/MODEL_CARD.md for actual limitations. Top-fifth precision is not overall accuracy. No seed-shopping by test performance.

Training environment Python3.12.14/scikit-learn1.9.1/NumPy2.5.4. JSON exports match independent sklearn inference within1e-12. Runtime standard-library sigmoid, no sklearn/pickle/hosted bill or training per Start. Mean/scale/coefficients/intercept learned offline, version binds payload/report; identity is consistency not malicious-author signature. Missing/stale/incompatible artifact fails ModelError; both required for new dual run even if no matching pre-due rows. No silent single-model/rule-as-probability fallback.

CSV+manifest generated under ignored ml/data, reproducible; trained artifacts tracked. Commands: python -m ml.generate_pre_due; python -m ml.train --stage pre_due; python -m ml.generate; python -m ml.train. Optional requirements-ml. Metadata/path/float differences may change identity across environments; no universal bitwise guarantee. Stop/restart Python around replacement.

## Saved prediction contracts

Each scored prediction records risk_type, target-specific probability rounded6decimal, scored_as_of, horizon_date, transformed inputs, modelversion/artifacthash, intercept and contribution list/warnings. Pre also outcome_check_date and lead7. Contributions=coefficient×standardized feature, relative to training means; sum+intercept reconstructs log-odds. Associations, not causes/percentage-point effects/agent-action confidence.

Result.workflow_version remains M3 for existing six-stage playback. prediction_mode=dual_stage_v1 distinguishes new runs. result.models={overdue,pre_due} saves both cards inclparameters/environment/report; result.model retains overdue card for compatibility. Current endpoints show current artifacts; saved runs render their own stored cards. M2(old5stages) and initial single-modelM3(savedonlymodel) remain unchanged/readable; never retro-score history.

## Finance and validation rules

Source object as_of_date/currency/invoices. USD only,1–500rows, canonicalJSONlimit1MB. Fresh atomic Supabase source read once/run; sorted compact JSON SHA256. No runtime JSON fallback. Perinvoice id/customer/segment/amount/due/previous_invoices/late_payments/broken_promises/disputed, extra fields rejected. Decimalnonnegative≤2places/max14digits, validdates/history, uniqueIDs, late≤previous. Amount is supplied outstanding balance, not derived from payment applications.

Days overdue=max(0,t−due). New lifecycle: settled/noamount; overdue; pre_due; due_today. days_to_due=max(0,due−t). Recovery eligible=positive+overdue+notdisputed. preventive_eligible=positive+due−t7+notdisputed. Pre-due/due-today rule urgency=None/not_due. Overdue rules unchanged:

- Aging=min(days,90)/90×40.
- Lateness=late/previous×40 (0 with disclosed no history).
- Broken-promise points20 if any, else0.
- Decimal ROUND_HALF_UP integer; high≥65/med≥35/low<35.
- Eligible overdue score≥35 gets template; lower monitored. Disputes pause regardless.

Policy collections-policy-v1; template reminder-template-v1, generation_mode template_no_llm. No LLM or real email; language/tool reasoning M4. Display action evidence, not private chain-of-thought.

priority_bucket=overdue ifeligible,pre_due ifpreventive_eligible,else none. Sort bucket, descending index/days thenID. Decimalmoney/index strings; prediction floats converted throughstr toDecimal for index. Separate summaries keep AR, overdue exposure and pre-due review distinct.

## Demo source and expected outputs

SQL001/002 remain original schema/sixrows. SQL003 adds/restores only Harbor28000due+7,Willow19500due+7,Vista12000due+14, relative to source date. No schema change, no history deletion or original6 reset. Repeat upsert no duplicates. Run SQL003 manually in owner's Supabase. Optional: without it app still reads six rows with no preventive examples; must not invent new source data locally.

Fullseed9rows/source2026-10-17: open431700,pastdue372200,recoveryeligible308000,pre_due59500(3),preventivecheckpoint47500(2),4overdue drafts,1dispute,1highurgencyeligible,0at90+. Harbor .718791,Willow .147210 becomes-overdue; Vista no prediction(window14). Pre horizonOct24/checkOct25. Recovery horizonNov16. Original six forecasts unchanged: Cedar .711312,Northstar .356656,Meridian .258685,BluePeak .245919,Atlas .090755,Solace .448718(dispute paused).

Prior M2 exercises remain valid on original source: Northstar86400→96400 adds10000toopen/eligible. With SQL003 totals instead441700/318000. Old six-row runs retain372200/308000. New M3 exercise Harborlate8→0,promises1→0 lowers preventive risk/rank, balances unchanged; restore8/1. Cedarhistory9/2→0/0 lowers recoveryurgency/prediction anddraftcount4→3; restore9/2. Datewindow exercise due+6(no pred),due−1(recovery); SQL003 restores futureexamples.

## Code / sequence / API

| File | Contract |
|---|---|
| backend/main.py / runner.py | Routes/lifecycle/health/SSE, six-stage persist-before-success orchestration |
| backend/storage.py | Supabase HTTPS RPC/config/sanitized errors |
| backend/pipeline.py / models.py | Typed source, lifecycle/eligibility, policy, routepredict, separatequeues, templates/results |
| backend/risk_model.py | Separate artifact specs/features, shared portable scoring and explanations |
| ml/generate*.py / train.py | Synthetic generators, stage-specific labels/splits/fit/export/reports |
| artifacts/*.json | Two learned parameter/provenance reports |
| dist/index.html / app.js | Target-labelled UI, stagefilter, two model sections, saved/legacy playback |
| sql/001,002,003 | Existing schema,originalseed,optional pre-due examples |
| tests/ | Storage, actualSQL/API, ML chronology/export/routing/failure checks |

Start persists queuedrun; ingest→validate→assess→predict→prioritize→draft. Each started/completed event and state/result writes atomically via SQL; only committed success shown.13events normally, approvaladds14. Freeze both artifacts for whole run. SSE polls stored events aftercursor every.35sec; Last-Event-ID replay; no fake work delays. Latest20list is not deletion; older history retained. Runs can finish while browser disconnected.

| Route | Contract |
|---|---|
| GET /api/health | M3,sourcecount,6stages,model_version(overdue legacy)+model_versions{overdue,pre_due}; DB+both artifacts checked |
| GET /api/model | Current recovery card |
| GET /api/model/pre-due | Current prevention card |
| POST /api/runs | 202 UUID/status/events_url, max5active |
| GET /api/runs | Latest20metadata |
| GET /api/runs/{UUID} | Saved input/result/models/events/interactions |
| GET /api/runs/{UUID}/events | SSE update, orderedIDs and resume |
| POST /api/runs/{UUID}/invoices/{id}/dry-run | Atomic eligible overdue template approval; pre-due blocked409 |

## DB / failure / secret contracts retained

Tables ca_demo_settings/invoices/runs/run_events/interactions. RPCs ca_health/source/create_run/append_event/get_run/event_feed/recent_runs/recover_runs/approve_dry_run. RLS on, no anon/authenticated/PUBLIC access, service_role grants; fixed search_path securitydefiner. Secret sb_secret via apikey; legacy service_roleJWT alsoAuthorization. URL HTTPSproject.supabase.co, notSQLconnectionstring/password. Dotenv.envignored, processvars takeprecedence; restart afterchanges. Never expose credentials in Git/chat/browser.

Append event/state/result/input atomic underlock; monotonicID/eventkeyUUIDdedup. Approval lock requirescompleted+eligible+draft+non-dispute, unique run/invoice/action, duplicate recordedfalse/noextraevent. Approval changesfinalresult nothistoricalsnapshots. Seedupserts source only. No live truncation. Test SQLBridge exec/reset runs isolated PGlite only.

States queued/running/completed/failed/cancelled/interrupted. UUIDvalidation; absent404; eligibility409; activecap429; config/DB/model503. Midrunartifactfailure predictfailed, no downstream fabricatedsuccess. DBoutagefailurepersistencebesteffort; SSEconnection-error transientnotinventedsavedevent. Nextstartup marks otherprocessactive jobs interrupted, not resumed. One backendprocess/database; no concurrent independentservers/workers. Completedhistorysurvivesrestart.

## Setup / validation / troubleshooting

Historical M3 lesson docs/MILESTONE_3.md: review updated PR#4, pullmain, runSQL003, restartexistingUvicorn/env, refreshStart. Freshproject useM2guideSQL001/002first. Existing.env andrequirements; no newpaidservice/runtimeMLdependency. Optional retraining requirements-ml, sourcegeneration commands above.

Local Python3.12.14:29tests including prior22regressions, prelabel boundaries/maturity, generator reproducibility, train-onlyscale/sklearnparity, SQL003idempotence, stage routing/date transition, no-window refusal, guards, source change/immutable snapshots, missingmodel truthful failure. Actual Uvicorn HTTP/SSE+DOM9rows/totals/two modelcards,preventivefilter/risklabel,approval14events,savedreopen,legacyM2 rendering. UserM3cloud/Python3.13.5 stillpending. Isolated PGlite is not live Supabase. OptionalNode/PGliteSQL and optional sklearntraining; tests skip affectedchecks ifmissing. One upstreamStarlette/httpxdeprecationwarning remains.

Troubleshoot missingpreexamples→runSQL003inURLproject; 503model→restorecommittedmatchingartifactortraincorrectstage; 503schema/key→sameprojectURL+serversecretSQL001/002; pause→manualresume; envignored→restart/checkterminalvars; wrongwindow→sourceasof/due difference7; oldresultsunchanged→expected; interrupted→newrun; staticpage/portbusy→stopoldserverrunUvicornatroot; wrongrepo/unpushededits→gitstatus/remote/log,preservechanges.

## Historical M3 next-step plan — implemented in M4 above

1. Record9rowrun,Harborinputedit/savedhistory and user's explanation of two targets, fixedwindow, risk vs urgency, separatequeues, syntheticlimits. Do not markcomplete from tests.
2. Inspect pushedcode/plan and preserveedits; choose lowcostLLMprovider/model, explain APIbilling separatefromChatGPT before requiringkey.
3. Explicit server draftingtool uses validatedfacts/structuredoutput. Deterministic invoiceID/amount/currency/due/asofchecks, dispute gate, reviewpolicy. If adding preventive drafts, use stage-appropriate pre-due wording and eligibility/approval checks; never call them overdue or bypassdisputes.
4. Persist provider/model/prompt/toolversions/latency/validatedoutput/errors. Invalid/providerfailed outputs visiblyreview/fallback, templatevsLLMlabelled. No fake generation or sending.
5. Structuredreplyclassification labelledfixtures M4, actualsignedinbound/outbound loopM5. Customertextuntrusted, claimpaidnotreconciliation.
6. RunnablePR+lesson/exercise. M5allowlist/idempotentemails+signedreplies/promises/followupaudit; M6ownhosting/auth/caps; visitorisolatededitingafterM6.
