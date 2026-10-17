---
document_role: implementation_knowledge_and_session_handoff
repository: CharanCharan/o2c-collections-agent
updated: 2026-10-17
implementation_milestone: M6_cloud_public_demo
implementation_branch: milestone-6-cloud-demo
implementation_status: ready_for_review_not_learner_verified
learner_status: M3_merged_user_reported_done_normal_run
pending_learning_check: M6_Render_URL_health_webhook_replay_M5_loop_then_deferred_M4
next_milestone: live_acceptance_then_optional_visitor_editor
---

# Project knowledge — continuation context

## Current M6 checkpoint — supersedes historical local-only/pending-M6 notes below

M5 PR#6 merged0114b768cf336cd98cfeb66b0953788cb110c899; compare base2ea39335 vs main had no file changes beyond merge. User authorizes cloud server now and reports Resend client error(Connect) for sent/delivered/received events in attempting state. This is evidence of provider events/connection trouble, not proof of successful callback persistence/learner loop. Exact endpoint URL not supplied, root cause unverified. M4 learning remains deferred by user. M6 branch milestone-6-cloud-demo, current docs/MILESTONE_6.md. Render chosen per original plan, not Sites/static hosting. No account/APIkey/actual deploy by assistant; Charan configures account/secrets and returns actual URL for verification.

New render.yaml: one Python web service, planfree, build pip installrequirements, runtime3.12.14 (tested; Windows3.13.5 unchanged), uvicornbackend.main:app host0.0.0.0 port$PORT workers1 proxyheaders/forwardedallowips*, health/livez, manualautoDeployTriggeroff. Defaultmodel/emailfalse, Groq20b/free-onlytrue, publictrue, generatedsessionsecret, privateSupabase/owner values syncfalse. No RenderPostgres/disk/secondUIservice/gateway/worker. Blueprintdeploylink or manualWebService guide. OfficialRenderFastAPI/Free/Python/Blueprint/Deploybutton and Resendretry docs checked2026-10-17. FreeRender sleeps15min/wakeabout1min; callbacks canretryaftercoldstart, no always-on/keepalivepromise. Freebandwidth/build overage canbill ifpaymentmethodpresent; ownerverifyFree/spendcontrols; app cannotverifytiers. ExistingSupabasecanpause, no paidupgradeadded.

PublicConfig PUBLIC_DEMO=false localdefault, DEMO_SESSION_SECRET+EMAIL_OWNER_TOKEN distinct32+chars requiredwhenpublic. RenderautoRENDER=true + publicfalse/invalid config fails503 (includinghealth) ratherthan exposinglocalmode. No secretsreturned. PublicAccess backend/public_demo.py signs7daySecure/HttpOnly/SameSiteLax cookies (id,issued,owner_until) withHMACSHA256. Keys reprhidden. Cookieis browseridentity, notverifiedperson; clearingcookiebypassesperbrowserlimits butglobalcapsremain. CookiepayloadnotencryptedcontainsrandomID/dateonly; changingid/ownerrolewithoutsignature rejected. OwnerloginPOST validatesindependentownerToken, rolecookie1hour; logoutclearsrole. Refreshmayretainownerhistoryroleuntilhour/logout butemailactionsstillneedexplicitX-Collections-Owner token; UIpasswordnotstored. Rotatebothownerandcookiesigningsecretsifexposed. Cross-originmutatingrequests withOriginmismatch/nonHTTPS rejected, no CORSopened; rawproviderwebhook exemptOrigin butsignaturerequired. Anti-frame/nosniff/no-referrer/no-store API headers.

SQL006 adds ca_run_access(runFK,session_key) and ca_demo_usage(dayUTC,actor,kind,attempts) RLS/anonymousdenied; serviceRPC publichealth,reserve,create,allowed,recent. Globaladvisorylock6006, runquota20global/3browser (owner20), LLM40global/8browser (owner/webhookglobal40); owneralso consumesglobal. ca_public_create reservesquota+existingca_create_run+sessionmap inonetransaction beforebackgroundexecution. Inactivecapacityfailure rollsbackquota/link. Oldunmappedruns owneronly. Sessionkeysstoredsha256randomcookieID, neverowner/providersecrets. RunService.create(public_actor) optional preservesoldlocalbehavior. Recentvisitorhistoryfiltersownrun; allread/feed/dryrun/classifyexample enforceownership404; ownercaninspectall. Privateemail activityrequiresowner401. Ownerheadersenableaccess, explicitloginsetsrolecookie.

LanguageService optionalbudget_guard calledunderprocesslockbeforeHTTPattempt/processincrement. Publicclosure enforcesvalidGroqfree-only routing evenifhealthskipped, thenSQLreserve using ContextVar actor propagatedtoasyncbackgroundrun. Realwebhooks useactorwebhook/globalcap; fixedexamplereviews usecurrentbrowser/owner. DBbudgetfailure/quotafailure ->LanguageErrorlabelledtemplate/manualreviewnoegress.4/run20/processcapsremainandcanlimitearlier; countsresetonlyprocessnotdurableSQL. No actualpaidproviderfallback or tierverification. Disabled/missingkey/invalidconfigurationmake nocall. SQLbudgetsreserveattempts conservativelyeveniflaterlocal/transportfailure; no actualcostguaranteeonpaidaccounts.

Main/routesM6, pipelineworkflowM6. /livez processonly; /api/health DB/models/config +SQL006ifpublic +SQL005ifemailenabled. GET/api/webhooks/resend JSONreachable signedPOST required; thisprobe noDB/providercall, notdeliveryproof. ActualPOSTunchanged64KiB/Svix/dedupe/threadguards. Localgateway notneeded oncloud. Privateeventstages email_approval/email_send/email_delivery/email_reply/followup_scheduled removedfromvisitor runJSON/SSE/dryrun/classifyresponses; rawcursormovespastfilteredSSEevents, publiceventIDscan havegaps. Financial/syntheticreplyresults unchanged; M5realreplytext livesseparatemailtables and owneronlyroutes. No originalhistorydeletion. Public data must remain synthetic; do notingestprivateAR beforeadditionalgovernance.

UIpublicmode note/sessionquota, ownerunlockcallsloginandrefreshhistory (workswithemaildisabled), privateemailpanel/pollgate, tokenonlysameoriginheader requests, logoutclearsrole/password/cache/historydisplay. New scripts/check_deployment.py stdlibread-only HTTPS checks /livez,/api/health,callbackGET,newcookieemptyhistory/privateemail401; noPOST/run/model/email. Command python-m scripts.check_deployment https://actualhost; cannotrununtilactualURLprovided.

Cloudlearnersteps: merge/pullM6, SQL006(existing004/005), stoplocalmain againstsameDB, RenderFree WebService/Blueprintmain +secretvalues, waitLive, GETprobe/health andsmoke. Update existingResendwebhook to https://actual.onrender.com/api/webhooks/resend, correctendpointwhsec inRender, enableemailprivatevars/redeploy. StableURL removeslaptop/tunneldependency butfreecoldstartstillpossible. Wakebeforeinterview, thenReplayoldcallbacks (do notresendoriginalemail), inspect200recorded vsignored/dedupe andownermailhistory. Connect/noHTTPstatus ->reachability;401signature;404path;409disabled;503schema/provider/config/matching. Resendcan disablefailedendpoint, reenableifneeded. No rawendpointconnectionrootcauseverifiedwithoutactualURL/logs.

Verification:97 tests passed on Python3.12.14 (16M6cases plus81regressions), including HTTPSsecurecookie isolation acrossread/history/SSE/mutations, tamperedcookie, restartpersistentcaps, globalquota/newcookie, ownerlogin/logout/CSRF, privateeventredaction acrossJSON/SSE/actionresponses, LLM8browser/40global/webhook budget, paidproviderblock withouthealth, invalidcloudconfigfailclosed, publicprobe/signaturegate, anonymousSQLdenial and budgetDBoutage noegress. LocalUvicorn HTTP/SSE/frontendDOM cookie-aware checks passed publicsessionStart/history/ownerunlock/mockemail/signedincomingcallback/review/task/logout withunchangedAR; legacyGroqmockflowalso passed. Pythoncompileall/JSsyntax passed; RenderYAMLparsed locally and settingscheckedagainstofficialreference (notremoteRendervalidation). OneexistingStarlette/httpxdeprecationwarning. All provider calls mocks and SQLisolatedPGlite, no actualRender/Supabase/Groq/Resendkeys/networksend/tunnelexposure. UseractualcloudURL/Livehealth/publicbrowserisolation/Resendreplay+M5inboxreply/task anddeferredM4modelgeneration remainpending. Do not markallmilestoneslearnercompleteuntilconfirmed.

NextaftercloudURL: readlatestrefs/knowledge, verifypublicread-onlyhealth/probe/nohistoryleak; ownerchecksResendReplayandactualincomingreply, optionalGroqFreeenabledsuccessfuldraft. Recordanyproviderfailureshonestly. Onebackendworker/serviceperDB; stoplocalserveroncecloudlive, deployonlywhenidle (restartinterruptsactivework). Monitorusage/storage, noautomaticdelete/keepalive. OnceM0–M6liveaccepted, interviewerwalkthroughandoptionalvisitorisolateddataeditorremain; donotaddeditornow.

## Historical M5 checkpoint — code merged, callback learner checks remain

M4 PR#5 merged a18edaad12c96a1d69e325ecbb074616d09aeb2e; compare to head6350b7f showed no file differences/user edits. User explicitly deferred LLM/email-drafting learning checks until after next milestone and authorized M5 now. Do not require those first or mark M4 live acceptance done. M5 branch milestone-5-email-loop, docs/MILESTONE_5.md current lesson. Canonical repo only; Charan merges/pulls/runs. No real Resend/Groq key, email, tunnel or deployment by assistant.

backend/mail/config.py: EMAIL_ENABLED=false default, RESEND_API_KEY/RESEND_WEBHOOK_SECRET/EMAIL_OWNER_TOKEN repr-hidden, EMAIL_FROM=onboarding@resend.dev, EMAIL_TEST_RECIPIENT one bare lowercase owned signup address, EMAIL_RECEIVING_DOMAIN actual account *.resend.app.32+character random owner token required for send/review (X-Collections-Owner), not provider key. Existing .env loaded server-side; terminal overrides and restart needed. Resend Free account manually confirmed by owner, app cannot verify billing tier. No domain purchase needed for owned-inbox/test sender and free managed receiving subdomain. No runtime dependency added; fixed HTTPS endpoints/httpx/no retries.

SQL005 additive four tables ca_mail_messages,ca_mail_webhooks,ca_mail_replies,ca_followups with RLS/anon denied and backend RPCs. ca_mail_prepare locks global advisory key, checks completed run/overdue eligible draft/no source dispute and any reviewed dispute hold across runs (also on retries), unique(run,invoice), persists exact payload and random reply address before send. Ten new reservations/UTC day durable, failed intents included. Mail approval/send/delivery/reply/followup events append under locked run last_event_id; financial result/source snapshots remain unchanged. Parent run cascade cleans related demo mail data, no automatic deletion introduced.

MailService.send owner/config/schema check -> immutable snapshot policy -> prepare -> ResendPOST /emails with Idempotency-Key collections-{mailUUID}. Test recipient never from source/visitor/model. Synthetic disclaimer/subject, Reply-To collections-{mailUUID}@manageddomain. State reserved/accepted/uncertain; provider response UUID saved, acceptance is not delivery. Accepted repeated send/restart no new call. Timeout/error conservative uncertain; manual retry only same stored payload/key before20h; config recipient/from changes block retry. Resend dedup retention24h, no send for old unknown intent. Daily cap doesn't prevent repeated HTTP attempts for one intent, which have owner auth and same provider key. SQL+provider not atomic; accepted response/lost DB save may need explicit reconciliation. No distributed exactly-once claims. Recover unknown20+h via verified provider dashboard and SQLca_mail_finish, never blindly create new run to resend.

Webhook: POST /api/webhooks/resend max64KiB raw bytes, Svix v1 HMAC SHA256/base64 constant-time and ±300s timestamp. Signature secret exactendpoint. Dedupe eventID and received providerEmailID before calls, global per-process lock. Deliverytypes sent/delivered/delivery_delayed/bounced/complained/failed/suppressed stored as individual signed evidence, no latest-status regression/out-of-order overwrite. Callback before acceptance match503 to request provider retry. Unmatched inbound reply address ignored200, no subject-based matching. Received event metadata -> fixed GET emails/receiving/{UUID}?html_format=cid and GET emails/{originalProviderUUID}; no URLs from email fetched. Match retrieved ID/to/randomalias/sender-originalrecipient/original message_id token in In-Reply-To or References/provider-computed DMARCpass. Missing messageID503retry; mismatch quarantine/APIattemptfalse; HTML-only or text>4000 manualreview, textstored max4000/truncationflag, no HTML/attachment execution. Verified callback doesn't prove author/payment truth.

Matched short plain text may call existing language.classify with current UTC receipt date for futurepromise validation (not fixedportfolioasof); simulated_input=false override; no LLM disabled gives truthful manualreview. Always review_required. UI shows received text/evidence and owner review form; intent manually confirmable without LLM. Promise needs future literalISO/optionalbounded2decimalamount/evidencequote and max1year; task due promise+1day. Other intents tomorrowUTC, paidclaim reconciliation, dispute investigation. Review resolution+one task+audit atomic/idempotent per reply. Resolution doesn't mark invoice paid/disputed/contacted; revieweddispute separately holds further email for invoice acrossruns. No auto-send/jobworker; tasks state scheduled are dated AR work items. Controlled email is separate from historical dry-run approval.

API: GET /api/email/owner-config owner-only reveals target/from, GET /api/runs/{UUID}/email returns run+messages/replies/delivery_events/followups; send-email owner+strictboolconfirm/forbidextras; resolve owner+boundedbody; callbacks verifiedprovider. GET health milestoneM5 includes email readiness/no token/providerkey, pipeline workflow_versionM5. Email schema checked only by email routes, defaultdisabled does not break pipeline without005. Main run/history/mailstate APIs not authenticated; local only preM6. Actual reply text/addresses are now private data to protect/redact in M6 before publiclink, never use real thirdparty AR/emails.

UI separate owner password (memory only/no storage), target confirmation, send confirmation, immutablepayload evidence/acceptedvsdelivery, replyreview/taskrecords. Poll5s after completed run plus manual refresh; add postrun actualevents without replayingstages. M2/M3/M4 old snapshots still supported. Refresh/reset doesn't imply resending.

Local callback connectivity: backend/webhook_gateway.py only POST /api/webhooks/resend, no docs/run/history/DBstartup; raw bytes/Svix forward fixed127.0.0.1:8000 trust_env=false/no redirects, max64KiB. Start main8000 and helper8001; VSCodePorts publicforward8001only, registeractualHTTPSpath+subscriptionsinResend, saveactualsigningsecret, keepapps/tunnelrunning. Gateway doesn'trecover jobs/startsecondRunService. Do notforward8000untilM6. No new paid hosting or external tunnel account needed. Liveforwarding/account setup learnerpending.

Verification:81 tests passed on Python3.12.14, including17M5tests: owner/optin/strictapproval/recipientinjection, acceptancevsdelivery, dedup+restart, uncertainretry+20hblock, ineligiblegate, signedreply/manualreview/paidnonmutation, sender/thread/DMARCquarantine/noLLM, optionalGroqclassification, literalpromise/date/task, revieweddisputehold includingolduncertainretry, tamper/expiry/size, officialSvixvector, durable10/daycap+anonpermissions and gatewaypath/rawbytes. Previous64SQL/ML/Groq/OpenAIregressions passed. Mockprovider only, isolatedactualSQL. Real local Uvicorn HTTP/SSE + frontendDOM checked templateprogress/dryrun/history/ownerunlock/mocksend/verifiedincomingcallback/manualpaidreview/followuptask/unchanged431700AR. Pythoncompileall/JSsyntax passed. One existing upstreamStarlette/httpxdeprecationwarning. DeferredM4livemodel, liveResenddelivery/thread/DMARCpermission, actualVSCodeforwarding/SupabaseSQL005/userPython3.13.5 remainpending.

Next learner: merge/pull M5, runSQL004ifneeded+005, keepLLMfalse, createResendFreeownedinbox/key/managedsubdomain, helperpublic8001only, endpointsecret+env+restart, actualreceive/emailreply/review/task/dedup/restartchecks. Return todeferredM4LLMchecks afterwards. NextM6: ownerhosting/access/LLMdurablequotas/PIIhistoryprivacy/operatorauth beforepubliclink; visitor editingafterM6.

## Historical M4 checkpoint — implementation remains, learner checks deferred

M3 PR#4 merged f3acb263a4ce64d35e534d77136a8158eac3f6b5. User said "done next step please"; record normal setup/run reported, not independent proof of optional source-edit/retraining mastery. M4 is prepared on milestone-4-llm-drafting, learner/cloud/Groq Free checks pending. Read docs/MILESTONE_4.md first. Canonical repo only; preserve edits and user merge/pull workflow.

M4 keeps both models and overdue eligibility unchanged. Latest user explicitly requires a free-tier model and modular provider/model/API-key control, no extra costs. backend/language.py holds O2C tools/schemas/prompts/validation/rendering. backend/llm/config.py loads environment defaults/bounds/key mapping; providers.py implements shared StructuredRequest/StructuredResult and separate Groq Chat Completions/OpenAI Responses adapters; errors.py shared safe error. Default Groq openai/gpt-oss-20b, strict structured output, low reasoning, include_reasoning=false, fixed https://api.groq.com/openai/v1/chat/completions endpoint. Provider reasoning is ignored, never evidence. Portable wire schema omits length keywords; full local Pydantic checks remain. No SDK dependency.

Opt-in COLLECTIONS_LLM_ENABLED=true plus private GROQ_API_KEY in existing ignored.env. LLM_PROVIDER=groq, LLM_MODEL=openai/gpt-oss-20b, LLM_FREE_ONLY=true; configurable caps LLM_MAX_CALLS_PER_RUN=4, LLM_MAX_CALLS_PER_PROCESS=20, LLM_MAX_OUTPUT_TOKENS=2048, LLM_TIMEOUT_SECONDS=30. Strict booleans/numeric bounds fail closed. Default disabled means no API calls; preserve Supabase.env. Restart after settings edits, terminal variables take precedence. Key names selected by provider only; no key cross-use, no arbitrary base URL or browser configuration. Free-only allows Groq gpt-oss20b/120b and qwen/qwen3.8-27b (reviewed2026-10-17), blocks OpenAI/unknown models before any request. This is routing policy, NOT account billing-tier verification; owner must verify Groq Free/no paid upgrade. Health explicitly account_billing_tier_verified=false. Same Groq model can cost on a paid account. No automatic provider failover, retry, upgrade or paid fallback. Quota429 gives visible template/manual review. Local counters reset on restart, not durable public quotas. Need M6 access/per-visitor/daily controls before public live model endpoints.

Optional OpenAI Responses adapter remains for future owner control, requires provider=openai, matching model/key and LLM_FREE_ONLY=false explicitly; no activation for current zero-cost POC. Both adapters share normalized audit/usage, no raw error bodies/keys/reasoning. Keys repr-hidden. HTTP endpoints fixed/no redirects. No real key obtained or live provider request made by assistant. Groq official billing/structured/reasoning/rate documentation checked2026-10-17; account access/free tier/model quality/latency unverified.

Draft workflow first builds existing Python templates; policy-ineligible/disputed/pre-due/monitor rows skip provider. If enabled, call once per eligible draft subject to caps. Structured Facts must exactly match saved invoice_id,amount,currency,due_date,as_of_date; strict opening/request/closing bounds. Numeric/date/currency/payment-route and selected unsupported policy/payment-claim prose guards. Python builds subject,greeting,fact block,signature, LLM supplies short nonfinancial phrasing. Keyword guards are not semantic correctness proof: human review always. No actual send. Valid generation_mode=llm_assisted_validated_facts; failed/config/missingkey/refused/incomplete/invalid/capped output retains template_fallback_no_llm_approval with redacted reason/review_required. Disabled template_no_llm never claims generation. No fallback to fake provider success.

Persist row.draft_audit: status,tool,provider,requested/returned model,prompt/validator versions,facts,input/output hashes,response ID,usage,duration,API-attempt flag when known. No raw provider error bodies/keys. context/result.drafting stores mode/counts/config. Six stages stay; enabled eligible tools add llm_draft started/completed or warning events, each with committed result snapshot.4eligible calls →21events instead13, approval adds1. Warnings do not stop run; actual database failure still stops. Disabled13events. Workflow_version M4, renderer supports oldM2/M3/M4; never rewrite history.

SQL004 is additive backend-only ca_language_health + ca_record_reply_example(uuid,text,text,jsonb). No new tables/action constraints/data deletion. Health/start initialization require readiness, preventing paid run before required schema. Reply RPC locks completed run, verifies invoice, dedupes example_id in row.reply_reviews, atomically appends event+result. No changes to balance, eligible, dispute, contacted or payment fields. Same run/invoice/example reopens review; per-process reply_lock avoids concurrent duplicate calls. Provider call and DB write cannot be one distributed transaction: a failed write after paid response can charge again on retry; do not claim exactly-once billing.

Fixtures/replies.json has5synthetic cases: promise,paidclaim,dispute,documents,injection. Browser selects fixed example, no visitor data editor/arbitrary reply endpoint. GET /api/reply-examples returns inputs without expected test labels. POST /api/runs/{UUID}/invoices/{id}/classify-example accepts only example_id, requires completed run. Unknown404, extra fields422. Returned strict intent+literal evidence+optional promise fields; date future/literalISO,amountliteral2decimalpositive≤balance, promise fields only for promise intent. These support extraction, not prove intent correctness. Always review_required/simulated_input, invoice_payment_updated=false. Disabled/provider-invalid/capped =>manual_review,classificationnull. Actual email/webhooks/promises/followup scheduling remain M5; a claim paid is not reconciliation. Reviews persist as result row map and reply_classification event; repeat after enabling still returns old review, use new run to re-evaluate.

New API health includes language.enabled/key_configured/provider/model/caps/counter without key, plus existing models/source. New.sql readiness errors actionable503. UI LLM/TEMPLATE/FALLBACK badges, tool evidence, fixed sample reply display. Runtime requirements unchanged. Tests autouse fixture forces API off/empty Groq+OpenAI keys and safe settings even with learner.env, injected httpx mocks only.64 local tests passed on Python3.12.14, including Groq payload/normalized usage, separate keys/config/model overrides, free-only/invalid settings blocking before any request, quota/no retry/no failover, refusal/truncation/invalid JSON/local length/fact rejection and OpenAI regressions. Real local Uvicorn HTTP/SSE/DOM with mocked Groq passed live progress/LLM labels/reply review/approval/saved history/legacy rendering; previous template checks remain. No live provider or learnerPython3.13.5/cloudSQL004 proof. Existing Starlette/httpx warning remains. Full SQL/training tests optional deps as before.

Next learner checks: merge/pull M4, SQL004, template run, privately confirm Groq Free/configure key+enable, successful live draft/usage evidence, paid example leaves invoice unchanged, duplicate does not call again, restart/history. Do not mark live success from mocks or a fallback badge. Optional M3 exercises remain unconfirmed.

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
