# O2C Collections Agent — Project Plan

Last updated: 2026-10-18
Owner: Charan
Current checkpoint: M0 complete; M1 local execution confirmed; M2 learner-complete on 2026-10-17 (Supabase source edit, immutable results and restart/approval persistence confirmed). M3 PR#4 merged; user reported done and requested M4. Normal setup/run is learner-confirmed; optional source-edit/retraining/understanding exercises not separately verified. M4 PR#5 merged a18edaad; user explicitly defers its live/learning checks until after M5. M5 PR#6 merged0114b768; user reports Resend Connect errors. M6 PR#7 merged; user reports cloud site working. Actual URL/external-loop checks not independently verified. PR#8 merged c5778663 and user confirms preload works. Current v2-visitor-cases implements conversation/case foundation, SQL007 setup pending; V2 inbox/LangGraph/autopilot design in docs/AGENT_V2_PLAN.md.

## Current milestone — V2.14 checkpoint write ordering

SQL013 installed live but valid early pending writes still fail23503. Reproduced with pinned LangGraph and delayed checkpoint transport. SQL014 preserves rows, permits durable writes before checkpoint with case-owned FK, bounded retention/cleanup, private access unchanged. New preflight requires revision14; appv2.14/uiworkflow-15. Branch checkpoint-write-order; lessonV2_14. Review/merge/pull/apply014whenidle/deploy/checkhealth/retryfailed required; no live DB mutation/provider/deploy by assistant. Regression result in PR. Guided walkthrough only after live repair confirmed; visitor editor last.

## Historical milestone — V2.13 workflow guide and LLM transparency

PR22 mergedce3624d9. AddshorteditableMD/twopageguidepopupbesidetitle, runtimeLLMreadinessnotice andperactionauditevidence. UI/staticplusversiononly, nonewSQL/packages/env. PriorSQL013application/retryacceptancenotconfirmed. Versionv2.13/workflow-15. 8regressions+actualHTTP/SSE/JSDOMguideandfulljourney passed; usermerge/deploy/nativevisualacceptancepending. LessonV2_13. Nextverifyrepair/deploytheninterviewerwalkthrough/editorlast.

## Historical milestone — V2.12 checkpoint database repair

PR21 merged796e4ab1. Userlocalca_checkpointfailures; exactSQLSTATEunavailable. ReproducedSQL009retention/delayedwriteFK23503; SQL013functionrepairpreservesbusinessdata/history andstrictunknownreferences. SafeSQLSTATE/actiondiagnostics+checkpointreadygate, healthv2.12/workflow-14. 48targetedSQL/API/graph/report/followup/streamchecks passed. Usermerge/pull/applySQL013/restart/retryacceptancepending; no directDBcredentialsorcloudchangesbyassistant. LessonV2_12. Verifyrepairbeforeguidedwalkthrough/editorlast.

## Historical milestone — V2.11 compact live execution

PR20 mergedd887e836. Compacttopstage names+actual7thgraphprocessing, ownedrun/invoiceSSEfromcommittedSQL, perrowlogbutton9thcolumn, fixglobalbusyblockingreadyinvoiceapproval, clearstalejob/orderedtimestampmerges. NoSQL/packages/env. Healthv2.11/workflow-13. 48targetedchecks+actualHTTP/SSE/JSDOMincludinggate-to-test-ready-buttonpassed; review/merge/manualdeploy/visualchecks pending. LessonV2_11; guidedwalkthroughnext/editorlast.

## Historical milestone — V2.10 reliable portfolio results

PR19 merged279cd108. Publiclivecheckfoundoldworkflow-6build; exactbrowserfailureunavailable. Fixprovenwholeloopabortwithperinvoiceexceptionisolation, safeoperationdiagnostics, explicitfailedcounts and retryfailedonly; retainfatalrecovery/partialresults. Processingdetailscollapsedbelowqueue. Newhealthapp_versionv2.10/ui_versionworkflow-12. NoSQL/packages/env. 40targetedchecks+localHTTP/SSE/JSDOMjourneypassed. Review/merge/manualdeploylatestandverifyversion+newrun; lessonV2_10. Guidedwalkthroughnext/editorlast.

## Historical milestone — V2.9 invoice next step and horizontal flow

PR18 mergeda0fcc746. UI-only: consistent topNextstep controls/explanation, fullwidthhorizontalportfolioflow+collapsedlog, fullwidthtable and invoice-specifichorizontalactivityinsidepopupwithread-onlyrefresh. NoSQL/packages/env. LessonV2_9. 10regressions+localHTTP/SSE/JSDOMselectedswitch/topactions/recovery/followups passed; learnermerge/manualdeploy/nativevisualacceptancepending. Nextguidedinterviewerwalkthrough, editorlast.

## Historical milestone — V2.8 run results and compact queue

PR17 merged1b959e05. Implement saved per-invoice run delta reports in existingjobJSON, frozen results vs currentaction/waitingsections, truthfullegacy/partial handling, countfilters and deliveryseparate. Compactwrappingqueueheader, remove customslider, finalcols Currentstatus/Lastcompletedaction/Nextstep. NoSQL/packages/env; lessonV2_8. 42 targeted SQL/API/graph/reporting checks +HTTP/SSE/JSDOMjourney passed; learnermerge/manualdeploy/visualchecks pending. Next guidedinterviewerwalkthrough, editorlast.

## Historical milestone — V2.7 queue-first invoice dialog

PR16 merged2a0e80f6. Userapproveslandingtable+execution, widerqueue, rowopenssidebysideemail/replydialog, clickhints+favicon. UI-only/noSQL/packages/env; currentlessonV2_7. Keep8fields/policies/Continuecasecontrol/compactheader; dialogreadonlyuntilaction. 8regressions andactualHTTP/SSE/JSDOMdialog/focus/recovery/promise flows passed; learnermerge/manualdeploy/nativebrowseracceptancepending. Nextguidedinterviewerwalkthrough, editorlast.

## Historical milestone — V2.6 collections controls

PR15 mergedaeebec1b. User approves business-friendly names and compactheaderplacement; implement Run collections +Portfolio overview/Payment promises/Collections run history panels, invoicecase reference and conditional Continue invoice processing aboveemail. UI-only; no newSQL/packages/env; keep012prerequisite. 22followup/emailtests +actualHTTP/SSE/JSDOM menu/resume/promise flows passed; live/pixelacceptancepending. LessonV2_6. Nextguidedinterviewerwalkthrough, editorlast.

## Historical milestone — V2.5 promise follow-ups and consistent scrolling

PR#14 mergedebcbe469. User authorizes promise/due follow-ups and fixes for table length/hidden horizontal scrolling/inconsistentstickycolumns. Implement explicit browserdemo clock, durable duechecks, reconciliation-beforefollowup, limited/autopilot sending with separate intents/history; boundedthreepanels and visiblehorizontalnavigation. Setup SQL012+manualdeploy, no newpackages/env. Lesson docs/MILESTONE_V2_5.md; acceptancepending. Keep dailyStartunlimited, free-only model/mailbudgets, originalcasemodes and sourceARunchanged. No actualscheduler/provider/cloudmutationbyassistant. Next guidedinterviewerwalkthrough; visitor editorlast.

## Historical correction — remove daily Start quotas

PR#13 merged774234d3. User authorizes removing daily visitor/global Start limits; implement SQL011 plus truthful health/UI. Preserve public isolation, case history/idempotency, model/email quotas and existing capacity checks. Existing usage retained, not reset. Merge/pull, apply011 inSupabase and manuallydeploy; no packages/envchange. LiveURL https://o2c-collections-agent.onrender.com/ read-only health confirmed24rows/graphready/emailready, LLMoff; signedcallbacksuccess stillunverified. Validate repeatedStarts after old3/20counters and no acceptedemailresends. Learnerdeploymentacceptance pending.

## Previous correction — risk columns and webhook configuration

PR#12 merged0f795f6. Restore dedicated Due / aging, Rule urgency and ML risk · target shown without dropping source balance/status/next/activity. Eight readable columns with panel horizontal scrolling. User's webhook409 is the running EMAIL_ENABLED=false gate; enable it in Render environment, save/redeploy, check health.email.ready and Replay a failed event. Live URL/signed success evidence pending; no live verification claimed. No newSQL/packages.

## V2.4 implementation — learner acceptance pending

PR#11 three-column UI merged58492dc5. The next milestone implements durable LangGraph cases, limited/autopilot modes, separate collection status/next action/latest activity, automatic processing of explicitly simulated website replies and15 additive scenarios. See [V2.4 lesson](docs/MILESTONE_V2_4.md) and authoritative PROJECT_KNOWLEDGE.md checkpoint. Existing two ML models, real fixed-recipient Resend delivery and free-only limits retained.

Implementation validation:135 automated tests passed with actual graph/SQL and mocked providers, plus local HTTP/SSE/DOM checks. No live provider calls, merge or deployment by assistant. Charan must review/merge, pull, apply009then010, installrequirements, deploy and verify. No new paid service/envkey. Existing9+15source rows=24/610400USD unless edited; SQL010 does not reset edits or cases.

Acceptance TODOs:

- Confirm workflow health and current24rows before Start.
- Limited mode: pending approval → Send email → actual delivery webhook.
- Send simulated reply → automatic interpretation/tool → separate status/next/activity.
- Explain source balance vs Demo remaining, partial/unmatched payment and dispute evidence.
- Autopilot new cases: max3 automatic reminders, globalmail10/day, original case modes retained.
- Reload/resume durable approval and explain graph/checkpointer code.
- Then scope demo-clock/due-task execution/guided scenarios; visitor editor last; voice optional only if free.

Older checkpoint paragraphs below are historical; this section and PROJECT_KNOWLEDGE's V2.4 entry govern current work.

## Goal and scope

Build a publicly shareable collections-agent POC. A visitor clicks Start and sees genuine backend actions and results appear in plain language. Charan must be able to explain, run, edit, and deploy the code himself.

Preserve this workflow: ingest AR data → validate and identify exceptions → score payment risk → prioritize accounts → draft reminders → approve/send controlled emails → capture replies → record promises and follow-ups → show audit history.

This is a hands-on learning project delivered one complete runnable milestone at a time, as agreed on 2026-10-17. Provide tested code through a GitHub pull request, explain its components, then let Charan run, inspect and modify it. Verify his results before marking a milestone learner-complete.

## Canonical source and delivery workflow

- Use only https://github.com/CharanCharan/o2c-collections-agent .
- Charan's uploaded baseline: 4777bb5a1d6fa5d7d4fc71507ddf980bd6f87db1.
- The duplicate CharanCharan/collections-agent is unused; Charan handles its deletion.
- Read PROJECT_KNOWLEDGE.md, this plan and current code before each milestone. Deliver a branch and pull request. Charan reviews/merges, then pulls main locally. His edits must be committed and pushed before subsequent work.
- The original hosted Sites demo is a presentation prototype; this GitHub repository and the local Python application are the working source for the real POC.

## Historical M6 implementation checkpoint

M5 merged; user authorizes cloud hosting and reports Resend Connect errors for sent/delivered/received callbacks. Exact URL unprovided: connectivity root cause not verified. M6 uses one RenderFree Python web service/direct HTTPS webhook with existing Supabase. Adds signed browser sessions, visitor-owned history, owner-only real email data/private-event filtering and SQL-backed UTC caps (20runs/40LLMattempts global,3runs/8LLM perbrowser). Public paid routing blocked, no tier/account verification. No new paid infrastructure or runtime package.

render.yaml pins Python3.12.14, one worker, manual deploy; SQL006 adds access/quotas without deleting priorhistory. /livez, publiccallbackGETprobe and read-only smoke script simplify deploymentdiagnosis. docs/MILESTONE_6.md covers account/secrets setup, health/probe, Resend URL/secret/replay and coldstartlimits. Assistant does not deploy/obtainkeys. 97localtests and cookie-aware HTTP/SSE/DOM checks passed with mocks/isolated SQL. Actual Render service URL/live health, visitor isolation and M5 callback/inbox/task tests pending; M4 learning remains deferred. Return to those live checks before allmilestones acceptance. Visitor editor remains optional after acceptance.

## Recommended stack

| Responsibility | Choice | Reason |
|---|---|---|
| Frontend | Existing HTML, CSS, JavaScript | Preserve UI; understand browser behavior first |
| API and orchestrator | Python + FastAPI | Fits Charan's Python background; explicit tool functions and run state |
| Live progress | Server-Sent Events (SSE) | Server pushes run events to browser; ordinary POST requests handle actions |
| Durable storage | PostgreSQL on Supabase | SQL tables for invoices, runs, interactions, and promises |
| ML | scikit-learn baseline, trained offline | Separate measurable payment-risk model from language generation |
| Language tasks | LLM API, provider selected in M4 | Reminder drafts and structured reply classification |
| Email | Resend HTTPS API and verified inbound webhook | Outbound email plus reply capture |
| Source control | Charan-owned GitHub repository | Edits, history, rollback, and hosting integration under his account |
| Hosting | One Render Python web service serving UI and API | One public URL; frontend need not be hosted separately |

Keep secrets in local environment variables and host-managed secrets. Never put API keys in HTML or Git. Hosted API usage is separate from a ChatGPT subscription.

## Milestones and acceptance checks

### M0 — Own and understand the existing code [LEARNER COMPLETE]

1. Download and extract the source bundle.
2. Open the folder in VS Code.
3. Serve `dist` locally using Python.
4. Run the demo; inspect `baseInvoices`, `run()`, `renderQueue()`, and `addEvent()`.
5. Change a visible heading; reload; explain what changed.
6. Create a repository in Charan's own GitHub account and commit the source.

Acceptance: Charan can start the site locally, edit it, and identify which parts are simulated.

### M1 — Execute a real backend run [LOCAL RUN VERIFIED; INPUT EXERCISE SUPERSEDED BY M2]

Build a small FastAPI service. First serve the existing frontend and a health endpoint. Then add a run endpoint and an event stream. Replace timer-driven claims with backend-produced results calculated from the six sample invoices. Calculate displayed totals and counts from the data.

Proposed API:

- `GET /api/health`: service status.
- `POST /api/runs`: create a run and return a unique run ID.
- `GET /api/runs/{run_id}/events`: SSE event stream for that run.
- `GET /api/runs/{run_id}`: run status and results.

Events should contain `run_id`, `event_id`, `stage`, `status`, `message`, `timestamp`, and structured `result` or `error`. A displayed step is complete only after the operation succeeds. Each visitor's run is isolated. On failure show a clear failed stage rather than continuing as though it succeeded.

Acceptance: Browser Start triggers Python execution. Changing the input changes actual results. No invented load counts or timer-only completion claims.

### M2 — Supabase data source and persistence [LEARNER COMPLETE]

Use Supabase Free, a hosted Postgres database, as both the invoice data source and durable store. Replace runtime invoice JSON reads with Supabase reads; seed the same synthetic rows once using SQL. Keep a simple five-table design for settings, invoices, runs, events and interactions. M1's amount remains the outstanding balance; normalized payment/credit ledgers are deferred unless a later feature needs them.

The revised checklist is docs/MILESTONE_2_PLAN.md. CSV import and a second hosted-source connector are removed from this milestone. PR #3 merged; Charan confirmed Supabase setup, expected outputs, source edits/immutable history and restart/approval persistence. docs/MILESTONE_2.md preserves the original setup lesson.

Acceptance: the Supabase rows produce the expected portfolio; owner data edits affect the next run; records/events/approvals survive Python restart; duplicate actions stay idempotent; failures are visible without JSON fallback. Historical run snapshots remain immutable.

### M3 — Train and evaluate payment risk [MERGED; NORMAL RUN LEARNER-CONFIRMED]

Two stage-specific targets: (1) at exactly seven days before due, not fully paid by end of due date; (2) positive overdue balance remains at snapshot+30days. The second replaces the original due+30 candidate for recovery; the first adds Charan's requested prevention use case. A date outside the pre-due checkpoint is explicitly not scored, rather than backdating features. No current-invoice aging/future outcomes in pre-due features.

Separate generated histories with mature labels, chronological gaps, train-only scaling, validation C choice and untouched later-date tests. Save/version numeric artifacts, model card, parameters and evidence. Website labels targets, shows separate queues and calibration/holdout evidence; never combines probabilities or calls one independent proof of the other. Disputes/zero balances/policy gates stay enforced. M3 preventive risk is review-only; actual reminder policy/sending is later work.

PR#4 merged; learner reported done. Optional deeper checks still not separately confirmed: change Harbor history and observe new risk while saved history stays unchanged. Explain timing windows, probability vs urgency, separate queue ranking and synthetic evaluation limits. Optional generator/trainer exercise for both models. Detailed steps docs/MILESTONE_3.md.

### M4 — Add language reasoning and policy [MERGED; LEARNER CHECKS DEFERRED BY USER UNTIL AFTER M5]

Use an LLM for reminder drafts and structured reply classification. Use SQL/Python for finance calculations and policy checks. Validate LLM output against invoice facts. Implement explicit tools and state transitions; no multi-agent expansion unless a demonstrated need arises.

Implemented: modular Groq Chat Completions/default Free model and optional explicitly selected OpenAI Responses structured language tools with exact fact echo and Python financial block; nonfinancial prose guards/human review; version/usage/hash/duration audit; visible provider/validation/cap fallbacks; five fixed synthetic reply cases and quote/promise checks, always review-only. Live calls require local opt-in and a confirmed Groq Free account for zero-cost operation, no credentials received/spending by assistant. SQL004 stores review/event atomically, duplicates avoid another provider call. See M4 lesson for cost explanation and local controls.

Acceptance pending: successful live API draft/evidence, invalid-output fallback understanding, sample classification/dedup/restart persistence, user can explain policy and limitations. Drafts use validated amounts and dates; disputed accounts pause; invalid output routes to review; tool inputs, outputs, versions, duration, and errors are recorded. Display action summaries and evidence, not private chain-of-thought.

### M5 — Close the email loop [MERGED; LIVE CALLBACK REPAIR PENDING]

Connect outbound email, record provider IDs, and verify delivery events. Capture real replies through a signed webhook; match by message/thread ID. Extract intent, promised date/amount, or dispute reason. Save a human-reviewed follow-up work task with due date and audit record; no unattended follow-up email sending. A customer saying 'paid' must not itself mark an invoice paid: require a payment source/reconciliation.

Use controlled test recipients, server-enforced recipient allowlists, approval, deduplication/idempotency, and rate limits. Public visitors must not be able to use the POC as an arbitrary email relay. Never send to contacts found in public invoice datasets.

Acceptance: Controlled reminder arrives in a real inbox; reply produces a verified event; retries do not duplicate emails or follow-ups.

### M6 — Deploy and demonstrate [CODE/DEPLOYMENT GUIDE PREPARED; ACTUAL CLOUD SETUP PENDING]

Deploy the repository under Charan's own account. Keep one service for UI/API. Use an external persistent database; do not depend on an ephemeral web-server disk. Configure API secrets, per-run isolation, usage caps, and resettable demo data before public access to live actions.

Make the demo understandable without narration: purpose, Start, stage explanation, input/output evidence, updated queue, action history, and final summary. Clearly distinguish synthetic data, predictions, generated text, and actual delivery/reply events.

Acceptance: An independent visitor opens one URL, starts an isolated run, sees real events, and can inspect the final result. A failed integration shows a truthful error. Charan can redeploy a visible change from his own GitHub repository.

## Optional enhancement after M0–M6

Offer visitors a data-edit/testing playground only after the core milestones are achieved. Use an isolated/resettable portfolio per session so edits do not change shared seed data or another visitor's run. Do not add these UI controls during M2; Charan can edit the source tables through Supabase for learning.

## Cost notes — checked 2026-10-17, verify before purchasing

- Render offers free static sites and free Python web services. Free web services sleep after 15 idle minutes and can take about a minute to wake. They have ephemeral local storage. Free Render Postgres expires after 30 days, so it is not the proposed durable demo database.
- Paid compute is optional; check current Render pricing before changing plans. Free service selection does not automatically bound all supplementary account usage charges.
- Supabase Free lists 500 MB database space and pauses free projects after one inactive week. A paused database can interrupt a portfolio demo even if the web server is paid.
- Resend Free lists 3,000 transactional emails/month and 100/day; received emails count toward the quota. Sender verification and domain configuration still apply.
- LLM API calls and an optional domain can cost extra. Provider subdomains remove the need to buy a website domain. A custom email sending domain may be a separate decision.
- Initial local learning can cost zero. Infrastructure can stay zero for small demos within free limits, but reliable always-on availability is a separate decision.

Official references:

- https://render.com/docs/free
- https://render.com/pricing
- https://render.com/docs/deploy-fastapi
- https://supabase.com/pricing
- https://resend.com/pricing

## Session protocol

At continuation, read PROJECT_KNOWLEDGE.md, this plan and canonical repository code; identify the last learner-confirmed checkpoint. Deliver a runnable milestone through a PR with explanation, test evidence, setup and an exercise. Verify Charan’s execution before updating learner acceptance. Implementation tests alone do not establish learner completion.

## Progress log

| Date | Checkpoint | Evidence / next action |
|---|---|---|
| 2026-10-17 | UI prototype live | Browser run and dry-run approval checked; no real integrations |
| 2026-10-17 | Portable source prepared | Source and initial learning guides exported |
| 2026-10-17 | M0 learner complete | Local run, heading edit and commit 4777bb5 confirmed |
| 2026-10-17 | Delivery workflow agreed | Runnable milestone PRs in o2c-collections-agent; Charan merges/pulls and learns locally |
| 2026-10-17 | M1 implementation merged | PR #1; implementation 05fa17b, merge af9944b; API, HTTP/SSE and DOM checks passed |
| 2026-10-17 | M1 normal local run verified | Charan reported expected results; amount-edit exercise/understanding check pending |
| 2026-10-17 | Knowledge and M2 checklist prepared | PROJECT_KNOWLEDGE.md and docs/MILESTONE_2_PLAN.md; no M2 implementation yet |
| 2026-10-17 | M2 scope simplified by user | Supabase Free source/store; runtime JSON replaced in M2; minimal schema; visitor edits deferred until after M6 |
| 2026-10-17 | M2 implementation ready in PR #3 | Supabase source/history, SQL scripts, saved-run UI; 14 local tests + HTTP/SSE/DOM passed; cloud setup and learner exercises pending |
| 2026-10-17 | M2 learner complete | User confirmed all working and both source-change/persistence checks; PR #3 merge ea7a5fb |
| 2026-10-17 | M3 implementation prepared | Synthetic-trained logistic model, saved evidence, risk ranking and lesson; 22 local tests + HTTP/SSE/DOM; learner verification pending |
| 2026-10-17 | M3 extended at user request | PR#4 now includes due-7 prevention plus overdue recovery, SQL003 examples and separate queues; 29 local checks; learner confirmation pending |
| 2026-10-17 | M3 merged / learner normal run confirmed | PR#4 merge f3acb263; user said done/next; optional exercises not separately confirmed |
| 2026-10-17 | M4 prepared | LLM-assisted phrasing, bounded API adapter, visible fallbacks and sample reply review;64 local tests/mock providers; live setup pending |

| 2026-10-17 | User requested free model and modular control | PR#5 updated to Groq default, separate provider adapters/keys, env model/limits, free-only routing, no paid failover; account Free status/live output still learner checks |

| 2026-10-17 | M5 authorized and prepared | PR#5 merged a18edaad; user defers M4 checks. Controlled Resend send/verified replies/review/tasks + SQL005; live owner setup pending. Next M6, then visitor editor |

| 2026-10-17 | M6 authorized/prepared | PR#6 merged0114b768; user reports Resend Connect error. One RenderFree service, SQL006 session/privacy/quotas, deployment guide and webhook probe. Actual cloud URL/replay/live acceptance pending |

## Latest V2 direction — after user-reported live deployment

User requests a product-facing invoice/email workspace, data on first load and a more autonomous LangGraph workflow with visitor replies and optional voice, retaining zero spend. Follow docs/AGENT_V2_PLAN.md: phase1 UI/preload now; next per-session simulated inbox/case status without visitor owner token; then durable LangGraph/checkpoints/approval modes/automatic reply handling; scenario polish and optional simulated browser voice. Current real email remains owner-controlled. Arbitrary visitor email needs verified sending domain; sustainable real IVR not assumed free. No unsafe blanket send or payment closure from customer claims. Existing future visitor editor remains separate.


## Latest milestone — V2.1 visitor conversations and persistent cases

User confirms initial loading works; no further preload diagnosis required. Prepared v2-visitor-cases based on PR#8 mergec5778663. Add isolated SQL007 cases/messages, unsent reminder copy, typed simulated reply, bounded automatic classification-for-review and saved proposed case status. Reload restores this session beside fresh current AR, never another browser’s messages. No LangGraph/visitor send/control dialog/financial action yet. Setup/exercise docs/MILESTONE_V2_1.md; acceptance pending until user runs it.

Latest approved channel choice: real Resend outbound to project test inbox with session-only display, simulated quick replies. That supersedes earlier simulated-outbound recommendation above. Existing M5 owner send stays intact for this foundation; next graph/control milestone adds narrow visitor authorization to fixed-recipient sends and provider status projection, without exposing owner inbox. Then business tools for document/dispute/payment reconciliation and promise due checks with labelled demo clock. Optional editing/voice remains later.


## Latest V2.2 correction — simplify the actual send flow

PR#9 merged00128867. User rejects token/private controlled-email panel and dry-run UI. Prepared draft-email-action: direct manual Send email beside saved draft, case auto-open, actual Resend send/status projection without visitor token. SQL008 after007; no newpackage/service. Legacy approvals never sent email and UI is removed, history retained. EMAIL_OWNER_TOKEN no longer needed for website readiness. Holds/idempotency/global10mailreservations/day kept server-side. Next remains durable LangGraph/modes: auto calls same send tool, limited pauses for actual Send; disputes need reviewed response tools, no blind chase. See docs/MILESTONE_V2_2.md. Live acceptance pending.


## Latest V2.3 UI milestone — before LangGraph

PR#10 merged9c140532. three-column-workspace implements user-requested fixture-classifier removal, readable fullwidth styling, desktopAR/customer/liveexecution columns, expandedexecution, headerPrevious runs andOverdue/Preventivebuttons. DefaultOverdue, fullportfolio totals, selectionfilter persists acrossStart/history; responsive2/1columns. No newbackend/SQL/packages/env.23 regressiontests + actuallocalHTTP/SSE/cookieDOM flows passed; no realviewport rendering available, responsiveCSSreviewed. User reviews/merges/pulls/manuallydeploys; currentlesson docs/MILESTONE_V2_3.md. Next dedicatedPR: durableLangGraph/checkpoint/controlmodes/actions/resume usingexisting real-send tool. No cosmetic LangChainclaim or paid infrastructure.
