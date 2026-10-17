# V2 current implementation checkpoint

V2.10: processingdetailscollapsedbelowtable; perinvoicefaultisolation/explicitexceptionresults+retryfailedonly, fataljobfailuresretaintruthfulrecovery/partialresults. Healthv2.10/workflow-12 distinguishesdeployments; publiccheckwasoldworkflow-6, exactuserfailureunknown. NoSQL/packages/env; lessonV2_10; deploy/acceptancepending.

V2.9 overrides historicalsidebar: horizontalfullwidthportfolioflow+collapsedeventlogabovequeue, selectedinvoicehistoryinsidepopup withread-onlyrefresh/explicitidentity and topNextstepspecificcontrols. NoSQL/packages/env; lessonV2_9; merge/deploy/visualacceptancepending.

V2.8 implements saved run processing results vs current attention/waiting, clearer status reasons and clickable filters, compact queue header, native scroll without custom slider. Final columns Current status / Last completed action / Next step. NoSQL/packages/env; lessonMILESTONE_V2_8; learnermerge/deploypending.

V2.7 overrides historicalthree-columnlayout: landingwideARqueue+Collectionsactivity, selectedinvoice opensnative dialog withemailleft/simulatedreplyright; obviousrowcue/keyboard/focusreturn, customlocalSVG/ICOfavicon. All8cols/businesscontrols/conditionalcaseContinue/policies retained. UI-only/no newSQL/packages/env; lessonMILESTONE_V2_7.md, learnerdeploy/nativebrowseracceptancepending.

V2.6 UI uses Run collections, compact Portfolio overview/Payment promises/Collections run history panels beside it, and a selected-invoice case reference/conditional Continue invoice processing aboveemail. Business mode/action names, existing backendbehavior unchanged. No newSQL/packages/env, keep012prerequisite. LessonMILESTONE_V2_6.md; merge/deploy/learneracceptancepending.

V2.5 implements explicit demo-clock due checks and fixed-recipient follow-up email with durablejobs, savedapproval/automaticallocations and separate initial/followup history. Full/partial/unmatched syntheticledger evidence controlsoutreach; no sourcebalancechange or scheduler. Currentlesson MILESTONE_V2_5.md; SQL012+manualdeploy. UI nowboundedpanels, nonstickyexecution and persistenthorizontalnavigation, all8columnsretained. Review/liveacceptancepending.

User override: SQL011 removes daily browser/global Start quotas; signed ownership and all metered model/email limits stay. No daily run allowance after migration, repeatedStarts preserve cases and do not resend. Apply SQL011 +manualdeploy; see current lesson. Prior run-cap design below is historical.

V2.4 implements the durable case workflow described in [the hands-on lesson](MILESTONE_V2_4.md). Actual LangGraph nodes, Supabase checkpoints, limited-mode interrupts, bounded autopilot, server-side Start continuation and controlled scenario tools are implemented on langgraph-case-workflow; merge/SQL009+010/deploy and learner acceptance remain pending. PR#11 UI is merged. No live external calls/deployment by assistant.

The AR table separates source balance, collection status, next action and completed activity. Send simulated reply automatically processes website events; real outbound still uses Resend to the configured project test inbox. Source AR is never marked paid by a claim/demo match. Existing cases keep original mode/history, autopilot reserves max3 newly eligible sends/job, free-only/global limits remain. Documentary evidence is synthetic and retrieved for review, not automatically emailed. Promise check-after dates are stored; demo clock/unattended due scheduling/voice/editor remain future work. Real inbound remains the private review channel.

The rest of this document preserves earlier design history. Statements saying graph/modes are “next” are superseded by this checkpoint and PROJECT_KNOWLEDGE.md. The current layout is three columns with execution always visible, not collapsed below.

---

> Latest V2.3 UI overrides earlier layout: three desktop columns AR|customer/draft/conversation|live execution, execution always expanded, header Previous runs, Overdue/Preventive buttons and larger type. Fixture classifier UI removed; typed conversation stays. This UI PR requires no new SQL/packages/env. LangGraph/checkpoint/modes follows as the next dedicated milestone.

> Latest V2.2 implementation supersedes earlier token/send phasing below: direct Send email beside draft, automatic case opening, real Resend send to fixed project test inbox and session-only status projection are implemented on draft-email-action. Owner/dry-run UI removed; owner token optional legacy API only. SQL008 after007. Graph/autopilot/limited-mode interrupts remain next. docs/MILESTONE_V2_2.md is current.

# Collections workspace V2 — business-first, autonomous within a policy

Status: phase1 merged in PR#8 (c5778663), user confirms preloaded data is working. Phase2 case/conversation foundation is implemented on v2-visitor-cases, learner setup pending. Remaining graph/autopilot phases are planned. PR#7 merged b8c0bc96. Actual public URL not supplied for independent verification. User asks for invoice/email-first layout, preloaded data, LangGraph, automatic/limited control, visitor replies without owner token, and voice/IVR ideas. Constraint remains no paid services. This document separates shipped phase1 from proposed V2 work. The case/conversation foundation is implemented below; LangGraph/autopilot are not implemented yet.

## Implemented immediately: workspace and first-load experience

Invoice queue, selected invoice/reminder and existing email panel appear before technical diagnostics. Execution stages, event evidence, model cards, saved-run controls and owner settings move to a collapsed lower section. Legacy technical IDs/behavior remain for existing history/tests. Header language emphasizes collections work rather than Python/backend implementation.

GET /api/portfolio loads the current synthetic Supabase source and computes validation, urgency, both stage-specific ML predictions and ranking as a read-only preview. No LLM, draft generation, email, saved run, event or quota reservation. Initial website load populates totals/invoices before Start is enabled. Preview is explicitly labelled; it does not claim a collection run executed. Start still invokes the genuine saved workflow. Existing source snapshot date and privacy boundaries remain. No new SQL/environment settings.98localtests passed, including the preview zero-side-effect check; cookie-aware HTTP/SSE/DOM verified nine preloaded rows,431700balance,zeroevents,collapsed diagnostics after email and the existing owner email loop with mocked providers. No live deployment by assistant.

M5 real email remains owner-only in this foundation milestone. The next graph/control-mode milestone will add narrowly scoped visitor sends to the fixed project test inbox. Moving owner controls is not removing backend authorization. New V2 permissions must replace the visitor experience before deleting its token dependency; exposing real inbox/secrets publicly is not the design.

## Recommended visitor journey

1. Open URL: see current invoices, amounts, risk/collection status and a customer inbox panel immediately. Later iterations overlay this session's saved case state; never show another visitor's inbox/history.
2. Choose Start agent. Dialog offers **Review actions** (limited control) or **Autopilot demo** (automatic actions within displayed policy).
3. Agent identifies priority accounts, pauses disputes, chooses eligible action, drafts/validates wording and either requests approval or sends through Resend to the project test inbox, while displaying only this session’s message/status copy.
4. Visitor acts as the customer: type a quick reply or choose a suggested scenario. The reply is a real application event, explicitly simulated customer communication rather than an externally received email.
5. LangGraph resumes that case automatically, interprets intent, validates extracted facts and records the supported next state/action. No separate manual Classify button in autopilot mode.
6. Changes appear beside the invoice and conversation: real reminder delivered to project test inbox, promise recorded, payment claim awaiting reconciliation, dispute held, documents requested or review needed. The bottom trace explains selected action/evidence/policy/outcome, not private chain-of-thought.
7. Reload restores that browser session's saved conversation/cases. Start processes new/pending work and due tasks; it does not resend every draft merely because it exists.

## Permission modes

| Action | Review actions | Autopilot demo |
|---|---|---|
| Read synthetic AR/risk/prioritize | Automatic | Automatic |
| Propose reminder/next action | Automatic | Automatic |
| Send real email to fixed project test inbox | Ask approval | Automatic if session/policy/budget checks pass |
| Read/classify newly submitted demo reply | Automatic | Automatic |
| Record clear supported promise/schedule demo task | Propose for approval | Automatic if literal date/amount/policy pass |
| Pause collection on dispute | Immediate hold, then review | Immediate hold, then review |
| Ambiguous promise or unsupported request | Pause for clarification | Pause for clarification |
| Claim of payment | Reconciliation required | Reconciliation required |
| Mark invoice paid/write off/change balance or terms | Never from model/customer claim | Never from model/customer claim |
| Arbitrary recipient email / actual phone call | Not part of default demo | Not part of default demo |

“Full control” should not mean unrestricted tools or arbitrary recipients. UI can explain exactly what Autopilot is allowed to do. A low-confidence/unavailable model or exhausted budget must pause/label fallback, not silently invent an action or permission.

## Make it agentic with LangGraph

Use one LangGraph state machine for the collection case, not multiple agents added for appearance. Mix deterministic finance/policy nodes with LLM decisions over a small allowed action set. LangGraph adds branching, state, interrupts and resume; the model/policy/tools implement business judgment. No paid LangSmith/deployment product is needed to use the library in our existing backend.

Suggested nodes:

- Load case: fresh source version plus session conversation, prior contacts, promises, holds and due tasks.
- Assess: existing Python/ML urgency and prevention/recovery estimates; no LLM finance calculations.
- Choose next action: model returns a structured action, supporting evidence and required facts from allowed actions. Python enforces eligibility, dispute hold, contact cooldown, due date, permissions and budget.
- Draft/validate: existing modular provider and exact financial rendering; one bounded repair attempt at most, consuming the existing budget. Invalid result goes to review or clearly labelled template.
- Approval: use LangGraph interrupt for limited-mode side effects or exceptional actions. Resume same thread with explicit approval.
- Deliver: narrowly scoped server-side tool uses Resend to send only to the fixed project test recipient. Persist reservation/idempotency and show this session’s message copy plus verified provider status. Do not expose the private owner mailbox.
- Await response: persist and end this invocation; do not hold a sleeping server task/socket indefinitely.
- Classify/validate response: on a new message event, resume with original case/thread and enforce extraction checks.
- Resolve/route: record promise, reconcile payment claim, hold dispute, prepare document response or request clarification. Save follow-up and end or loop to the next allowed action.

Persistence requirements: use durable LangGraph checkpoints backed by the existing Supabase Postgres, with server-side connection settings if the standard Postgres checkpointer is selected. Current saved snapshots are audit history, not a LangGraph checkpointer. Do not call an in-memory checkpointer durable, and do not use ephemeral Render SQLite. Add checkpoint tables/connection setup in the dedicated graph PR, test disconnect/restart/resume, and count storage within Supabase Free. Final adapter/connection choice remains implementation work.

Thread IDs must be generated/mapped by backend to the authenticated browser session/case, not accepted as unrestricted visitor pointers. Preserve API ownership checks. Side-effect nodes need durable idempotency keys and a reservation/commit pattern; graph replay/resume must not duplicate messages or tasks. Keep approval separate from the send side effect because interrupted nodes can replay. Put maximum steps, per-invoice contact limits and existing global model quotas around loops. Model attempts only on business events, never on page rendering/polling.

## Business use cases worth demonstrating

| Trigger | Agent action | Business pain addressed |
|---|---|---|
| High risk before due | Propose preventive reminder with stage-appropriate wording | Reactive collections/avoidable late payments |
| Large overdue exposure | Pick next best eligible account/action | Collector time spent on low-value work |
| Multiple open invoices for one customer | Propose consolidated communication where source supports grouping | Duplicate/conflicting reminders |
| Customer promises a dated amount | Record supported promise, hold repetitive chase, schedule check | Promises lost in inboxes |
| Promise date passes | Recheck payment evidence, prepare follow-up if still unpaid | Manual follow-up tracking |
| Customer says paid | Create reconciliation case; wait for matched payment evidence | Incorrect closures and unnecessary chasing |
| Dispute reply | Hold outreach, record reason and route to AR owner | Repeatedly chasing disputed balances |
| Invoice/document request | Retrieve only a controlled synthetic document or ask for missing artifact | Back-and-forth/document delays |
| Invoice lacks contact/data | Explicit exception/clarification | Silent bad sends and poor data quality |

Keep invoice financial lifecycle (open/overdue/settled) separate from collection case status (awaiting response/promise recorded/dispute hold/reconciliation required). Model confidence is not payment truth. Do not display “cash recovered” unless a disclosed payment ledger event supports it.

For repeatable demos, add a session-local **demo clock** and an explicit “advance demo date” action later. This demonstrates a promise becoming due without waiting actual days. Label it simulated time; real Resend events retain actual receipt time and the existing real-date rules. Do not silently mix fixed portfolio dates with actual UTC promise expiry.

## Visitor email/inbox choice under zero-cost constraints

Recommended default (latest user-approved design): **real outbound via Resend to the existing project test inbox, with simulated customer replies in the website**. Visitors see only their session-linked message copies and verified provider status; label the real recipient as the project test inbox, not the visitor’s personal inbox. Typed replies are clearly labelled simulated and go through the same classifier/policy as live messages. Do not claim they are Resend receipts.

This milestone implements only session cases, an **unsent draft copy**, typed replies, automatic classification-for-review and persistent proposed collection status. Opening a case does not send or simulate delivery. Real outbound is still the existing owner-controlled M5 flow. The next LangGraph/control-mode milestone will implement server-authorized visitor sends scoped to their own case and the fixed configured test recipient, preserving idempotency/global mail limits and keeping all unrelated owner messages private. No visitor-supplied recipient/body/sender and no exposed owner credential.

An actual Resend receiving mailbox can receive messages at the account's managed subdomain, but it is not a public writable inbox widget to expose wholesale. A reply typed into our website is application input, not a Resend received webhook. If we later display actual messages, retrieve/relay only session-matched content server-side and retain signature/thread/sender checks; never expose API keys, shared inboxes or unrelated messages.

The current onboarding@resend.dev test sender only sends to the account signup address. Arbitrary visitor recipients require a verified sending domain. If Charan already owns a suitable domain, sending may fit the provider Free quota, but domain ownership/verification is still needed; buying a domain is not zero cost. An optional future real-email path needs recipient verification/consent, durable recipient and global caps, session-scoped access and no relay capability. Do not simply replace EMAIL_TEST_RECIPIENT with visitor text or remove owner auth from the existing real-email endpoint.

Public visitor experience should need no owner token. Keep a private operator credential for account administration and a server-enforced narrow visitor tool boundary for fixed-recipient sends; remove those controls from the main visitor journey rather than granting anonymous access to the owner's inbox. Existing private email history must remain private.

## Voice and IVR

Real phone calls are a useful escalation channel but are not a sustainable zero-cost default. Twilio offers a time/usage-limited trial, then paid service. Do not build a permanent public demo around trial credits or switch to paid automatically.

Optional free demonstration: an in-browser “Voice conversation demo” with typed replies and browser speech playback where supported. Label it a simulation, not a telephone/IVR call. Browser speech availability varies; typed flow remains fully usable. A future real-voice adapter can share the case state/classification/policy, disabled by default, with explicit recipient consent and separate budget.

Before voice, higher-value low-cost additions are promise tracking, dispute holds, reconciliation exceptions, document responses and a clear customer timeline. They demonstrate O2C process knowledge and materially richer decision paths.

## Delivery order and acceptance

1. **Workspace/preview PR (this PR):** invoice/reminder/email first, technical details below, initial current-data preview. No graph/email authority change. Merge/pull and manually redeploy existing Render service; no new SQL/env.
2. **Visitor conversations + case state (implemented, setup pending):** SQL007 case/messages, one case per browser/invoice with immutable originating-run snapshot; unsent draft copy, typed simulated replies, automatic classification-for-review or visible manual fallback. No owner token for this channel. Private M5 email stays protected. Initial load restores cases beside fresh AR; duplicate request UUID does not repeat model work. No graph/checkpoint or promise/task/payment mutation yet.
3. **LangGraph + control modes:** replace linear orchestration where useful, install/pin library, durable checkpoints, permission dialog, policy-checked decisions/approval interrupts and automatic resume on message. Test fresh/reload/restart/duplicate callback/no paid fallback; expose model-unavailable behavior honestly.
4. **Scenario polish:** preventive outreach, promises/expiry with explicit demo clock, disputes/payment claims/documents, outcome counters and short guided interviewer scenarios.
5. **Optional browser voice:** only after above. Actual arbitrary-recipient email/phone adapters require a separate justified plan; not part of no-cost default.

No blanket automated send on existing drafts. Only eligible, newly approved/authorized, non-duplicate case actions may execute. No background forever-loop: Render Free can sleep. Incoming events or explicit run/check-due actions resume saved work; exact-time unattended scheduling would need a separate reliable scheduler/hosting decision. No free 24/7 autonomy claim.

Pending learner evidence: user reports live site works, but actual URL not supplied for assistant verification. Prior Groq quality/real Resend callback loop checks remain separate; do not treat a new simulated inbox as proof that the external transport works.

Official references reviewed2026-10-17:

- https://docs.langchain.com/oss/python/langgraph/overview
- https://docs.langchain.com/oss/python/langgraph/interrupts
- https://docs.langchain.com/oss/python/langgraph/persistence
- https://github.com/langchain-ai/langgraph/blob/main/LICENSE
- https://resend.com/docs/knowledge-base/403-error-resend-dev-domain
- https://www.twilio.com/docs/usage/trials


## V2.1 implementation contract

Read docs/MILESTONE_V2_1.md for setup/exercise and PROJECT_KNOWLEDGE.md for handoff. SQL007 is additive; existing runs/AR/mail remain unchanged. Session keys are server-derived and never returned. Cases are session-private even for another browser with an owner role. Twelve cases/browser,500 global stored cases;12 replies/case;20 replies/browser/day and120 global/day. Caps are SQL-atomic; global/actor model quotas still apply. Case caps do not reset on UTC midnight. A new run reuses an existing case for that invoice, preserving original snapshot and contact history. No reset/delete button this milestone.

Reply is saved as pending before the bounded LLM attempt. Same request UUID/text returns stored outcome without another model attempt, including after failure/restart. A crash can leave a pending/manual review case; there is no silent retry or recovery-worker claim. A classified dispute sets a sticky **demo case** hold; separate owner mail is unchanged in this foundation. All promise/date/amount results are proposals requiring review, not committed promises or scheduled tasks. Payment claims require reconciliation and never reduce AR.

Public uses the existing signed7-day cookie/secret. Local HTTP also gets a browser cookie; set private DEMO_SESSION_SECRET32+characters locally for persistence across Python restarts. Without it a local process-random signer means cases persist in SQL but the new process cannot recover that browser identity. Public configuration remains fail closed and Secure cookies stay enabled.
