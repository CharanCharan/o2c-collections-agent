/* Case workflow presentation. Decisions and durable checkpoints live in Python. */
'use strict';
let workflowReady = false;
let agentJob = null;
let pendingMode = null;
let workflowPollBusy = false;
let caseActionBusy = false;
let scenarioSummaries = [];
let outcomeFilter = null;
let executionStream=null;
let liveExecution=null;
let invoiceStream=null;
let invoiceStreamId=null;
function stopInvoiceStream(){invoiceStream?.close();invoiceStream=null;invoiceStreamId=null;}
function watchInvoiceExecution(c) {
  if(!$('invoice-dialog')?.open || !c)return;
  if(invoiceStreamId===c.id)return;
  stopInvoiceStream();invoiceStreamId=c.id;
  const source=new EventSource(`/api/cases/${c.id}/events`);invoiceStream=source;
  source.addEventListener('case-update',message=>{
    if(source!==invoiceStream || state.selectedId!==c.invoice_id)return;
    try {
      const data=JSON.parse(message.data),old=JSON.stringify(visitorCases.find(x=>x.id===c.id));
      const draft=JSON.stringify(followupDraft(visitorCases.find(x=>x.id===c.id)));
      mergeExecutionCases([data.case]);
      if(old!==JSON.stringify(visitorCases.find(x=>x.id===c.id))){
        renderQueue();
        if(draft!==JSON.stringify(followupDraft(data.case)))renderDetail();else{renderCase();renderSendState();}
      }
    }catch(error){showError('Could not display invoice activity: '+error.message);}
  });
}


function mergeAgentJob(job) {
  if(agentJob?.run_id===job?.run_id && agentJob.updated_at && job.updated_at && job.updated_at<agentJob.updated_at)return;
  agentJob=job;
}
function stopExecutionStream(){executionStream?.close();executionStream=null;}
function mergeExecutionCases(incoming) {
  for(const c of incoming){const old=visitorCases.find(x=>x.id===c.id);if(!old || String(c.updated_at)>=String(old.updated_at))visitorCases=[c,...visitorCases.filter(x=>x.id!==c.id)];}
}
function showJobState() {
  if(!agentJob)return;
  const active=['running','waiting_for_portfolio'].includes(agentJob.status);
  $('start-run').disabled=active||dueActive()||state.status==='running';
  if(!active)banner(agentJob.status==='completed'?(agentJob.progress?.failed?'REVIEW REQUIRED':'PROCESSING FINISHED'):'RECOVERY REQUIRED',agentJob.status==='completed'?(agentJob.progress?.failed?`${agentJob.progress.processed}/${agentJob.progress.total} invoices processed; ${agentJob.progress.failed} need review. See Run overview.`:'Case actions saved. Waiting/review states remain open.'):'Open Run overview for the saved reason and recovery action.');
}
function connectExecutionStream(runId) {
  stopExecutionStream();
  const source=new EventSource(`/api/runs/${runId}/agent/events`);executionStream=source;
  source.addEventListener('execution',message=>{
    if(source!==executionStream)return;
    try {
      const data=JSON.parse(message.data);
      if(data.job)mergeAgentJob(data.job);
      const oldSelected=JSON.stringify(visitorCases.find(c=>c.invoice_id===state.selectedId));
      const oldDraft=JSON.stringify(followupDraft(visitorCases.find(c=>c.invoice_id===state.selectedId)));
      if(data.cases)mergeExecutionCases(data.cases);
      if(data.case){mergeExecutionCases([data.case]);const a=data.case.workflow?.activity?.at(-1);if(a)liveExecution={invoice_id:data.case.invoice_id,...a};}
      renderQueue();renderFlow();
      const changedDraft=oldDraft!==JSON.stringify(followupDraft(visitorCases.find(c=>c.invoice_id===state.selectedId)));
      if(changedDraft)renderDetail();else{if(oldSelected!==JSON.stringify(visitorCases.find(c=>c.invoice_id===state.selectedId)))renderCase();renderSendState();}
      showJobState();
      if(!['running','waiting_for_portfolio'].includes(agentJob?.status))stopExecutionStream();
    }catch(error){showError('Could not display invoice execution: '+error.message);}
  });
  source.onerror=()=>{if(source===executionStream && !['running','waiting_for_portfolio'].includes(agentJob?.status))stopExecutionStream();};
}

const workflowLabels = {
  quota_wait:'Waiting for mail quota',processing:'Processing case',ready_for_outreach:'Reminder ready to send',awaiting_approval:'Action ready for approval',
  awaiting_outreach:'Reminder ready to send',manual_review_required:'Human review needed',promise_review_required:'Payment promise needs review',dispute_hold_review_required:'Dispute — collections paused',
  awaiting_delivery:'Awaiting delivery',awaiting_response:'Awaiting customer reply',promise_recorded:'Promise recorded',
  followup_due:'Promise follow-up due',demo_payment_matched:'Payment matched · demo',demo_partial_payment:'Partial payment · demo',
  documents_ready:'Documents ready',contact_required:'Contact needed',delivery_exception:'Prior delivery issue · simulated',
  delivery_unknown:'Send outcome unknown',preventive_review:'Not due — preventive assessment only',monitoring:'No reminder — below policy threshold',
};

const activityLabels={load:'Load invoice',interpret:'Interpret customer reply',choose:'Select collection action',approval:'Request approval',authorization:'Authorize action',execute:'Complete action',plan_followup:'Prepare promise follow-up',finish:'Save outcome',supersede:'Update after customer reply'};
const actionLabels={record_promise:'Record payment promise',send_email:'Send reminder',send_followup_email:'Send follow-up'};

function invoiceContinuation(c) {
  const w=c?.workflow;if(!w)return false;
  const latest=c.messages.findLast(m=>m.channel==='simulated_customer_reply');
  const unfinished=w.processing || ['pending_review','model_attempt_reserved'].includes(latest?.review?.status);
  const busy=caseActionBusy||sendBusy||dueActive()||state.status==='running'||['running','waiting_for_portfolio'].includes(agentJob?.status);
  return Boolean(unfinished && !w.pending && !busy);
}

function invoiceCaseHeader(c) {
  const row=state.invoices.find(r=>r.id===state.selectedId);if(!row)return '';
  const w=c?.workflow,pending=w?.pending,send=$('send-draft');
  let title='Review this invoice',explanation=rowView(row).next,action='';
  const busy=caseActionBusy||sendBusy||Boolean(c?.workflow?.processing)||Boolean(caseLoadError);
  const issue=agentJob?.progress?.report?.invoices?.[row.id]?.error;
  if(issue && rowView(row).status==='processing_error' && !invoiceContinuation(c)) {
    title='Recover invoice processing';explanation=issue.message+' Open Run overview for the diagnostic and Retry failed invoices action.';
  } else if(invoiceContinuation(c)) {
    title='Continue interrupted invoice processing';explanation='Continue this invoice from its last saved step. This does not restart the portfolio.';
    action='<button class="primary" id="resume-case-action">Continue invoice processing</button>';
  } else if(pending?.tool==='record_promise') {
    title='Record payment promise';explanation='Review the customer reply and proposed payment date, then approve saving this promise.';
    action=`<button class="primary" id="approve-case-action" ${busy?'disabled':''}>Record payment promise</button><button class="secondary" id="decline-case-action" ${busy?'disabled':''}>Leave for review</button>`;
  } else if(['send_email','send_followup_email'].includes(pending?.tool) || (send && !send.disabled)) {
    title=send?.textContent || actionLabels[pending?.tool];
    explanation='Review the saved email below. This button approves and sends that email to the project test inbox, then continues this invoice’s workflow.';
    action=`<button class="primary" id="invoice-next-action" ${busy||!send||send.disabled?'disabled':''}>${escapeHTML(title)}</button>`;
    if(send?.disabled && !mailEnabled)explanation='A reminder is prepared, but email is disabled or not configured on the server.';
  } else if(w?.processing || busy) {
    title='Processing in progress';explanation='The active operation is processing saved case actions. Activity below updates from the backend.';
  } else if(!w && !c) {
    title='Run collections to prepare this invoice';explanation='Return to the queue and choose Run collections. Opening this invoice does not start processing.';
  } else if(['awaiting_response','awaiting_delivery','promise_recorded'].includes(rowView(row).status)) {
    title=rowView(row).label;explanation=rowView(row).next+'. No approval is pending. Simulate a customer reply on the right to test the next response.';
  } else if(rowView(row).status==='dispute_hold_review_required') {
    title='Review dispute evidence';explanation='Collections are paused. Inspect the supporting evidence on the right before deciding how to resolve the dispute. No automatic chase is allowed.';
    action='<button class="secondary" id="review-invoice-evidence">View supporting evidence</button>';
  }
  return `${c?`<div class="case-reference"><span>Collection case</span><code title="${escapeHTML(c.id)}">#${escapeHTML(c.id.slice(0,8))}</code><span class="saved-indicator">Saved</span></div>`:''}
    <div class="invoice-next-step"><div class="eyebrow">Next step · ${escapeHTML(row.id)}</div><h3>${escapeHTML(title)}</h3><p>${escapeHTML(explanation)}</p><div class="next-step-actions">${action}</div></div>`;
}

function refreshInvoiceCaseHeader(c) {
  const panel=$('invoice-case-controls');if(!panel)return;
  panel.innerHTML=invoiceCaseHeader(c);panel.hidden=false;
  watchInvoiceExecution(c);
  if($('invoice-next-action'))$('invoice-next-action').onclick=()=>{if(!$('send-draft').disabled)$('send-draft').click();};
  if($('review-invoice-evidence'))$('review-invoice-evidence').onclick=()=>{
    const evidence=$('case-conversation').querySelector('.case-outcome');
    if(evidence){evidence.tabIndex=-1;evidence.focus();evidence.scrollIntoView?.({block:'start',behavior:'smooth'});}
  };
  if(c)bindWorkflowExtras(c);
  if($('resume-case-action'))$('resume-case-action').onclick=async()=>{
    caseActionBusy=true;renderCase();renderSendState();
    try{saveCase(await api(`/api/cases/${c.id}/resume`,{method:'POST'}));}
    catch(error){showError(error.message);await refreshCases(false);}
    finally{caseActionBusy=false;renderDetail();}
  };
}

function rowView(row) {
  const c=visitorCases.find(c=>c.invoice_id===row.id),w=c?.workflow;
  let status=w?.status || c?.collection_status || (row.dispute?'dispute_hold_review_required':row.lifecycle==='pre_due'?'preventive_review':'monitoring');
  let next=w?.next_action || (c?.outbound ? 'Wait for delivery or customer reply' : row.action);
  const completed=(w?.activity || []).filter(a=>a.status==='completed' && ['execute','interpret'].includes(a.node));
  let latest=completed.at(-1) || null;
  const currentOutbound=followupMail(c)||c?.outbound;
  if(currentOutbound) {
    const issue=currentOutbound.events.findLast(e=>['email.bounced','email.failed','email.complained','email.suppressed'].includes(e.type));
    const delivered=currentOutbound.events.findLast(e=>e.type==='email.delivered');
    const e=issue || delivered;
    if(e && (!latest || new Date(e.received_at)>new Date(latest.timestamp))) latest={message:e.type.replace('email.','Email '),timestamp:e.received_at};
    if(!latest) latest={message:currentOutbound.state==='accepted'?'Email accepted by Resend':'Email outcome unknown',timestamp:currentOutbound.created_at};
    if(!w || ['awaiting_delivery','awaiting_outreach','awaiting_response'].includes(status)) {
      status=issue?'delivery_unknown':delivered?'awaiting_response':currentOutbound.state==='accepted'?'awaiting_delivery':'delivery_unknown';
      next=issue?'Review delivery issue':delivered?'Wait for customer response':'Await verified delivery';
    }
  }
  if(!latest && c?.messages.at(-1)?.channel==='simulated_customer_reply') latest={message:'Simulated customer reply saved',timestamp:c.messages.at(-1).created_at};
  let label=workflowLabels[status] || caseLabels[status] || status;
  if(status==='awaiting_approval')label=w?.pending?.tool==='record_promise'?'Payment promise ready to record':w?.pending?.tool==='send_followup_email'?'Follow-up ready to send':'Reminder ready to send';
  if(status==='monitoring') {
    label=Number(row.amount)<=0?'No outstanding balance':row.days===0?'Not overdue — no reminder scheduled':'No reminder — below policy threshold';
    next=Number(row.amount)<=0?'No collection action needed':row.days===0?'Review when due':'Review if urgency increases';
  }
  if(status==='preventive_review')next='Review payment risk; pre-due email is not enabled';
  if(status==='promise_recorded')label='Payment promised — '+(w?.promise?.promise_date || 'date saved');
  if(status==='dispute_hold_review_required')label='Dispute — collections paused';
  if(!w && !c?.outbound && !row.dispute && !['pre_due','due_today'].includes(row.lifecycle)){label='Ready for agent review';next='Run collections to assess and prepare actions';}
  const failure=agentJob?.progress?.report?.invoices?.[row.id]?.error;
  if(failure && (!w || w.processing)){status='processing_error';label='Processing needs review';next='Open Run overview to review the issue and retry failed invoices';}
  return {c,w,status,label,
    next:next || 'Review invoice',latest:latest?.message || (row.draft?'Reminder draft prepared':'No collection action recorded'),timestamp:latest?.timestamp};
}

function renderWorkflowSummary() {
  const panel=$('workflow-summary');if(!panel)return;
  const job=agentJob, report=job?.progress?.report;
  const entries=Object.entries(report?.invoices || {}).filter(([,v])=>v.completed);
  const rows=state.invoices.map(row=>({row,...rowView(row)}));
  const groups=[];
  const card=(label,ids,detail='')=>{
    const index=groups.push({label,ids})-1;
    return `<button class="result-card" data-result="${index}" ${ids.length?'':'disabled'}><strong>${ids.length}</strong><span>${escapeHTML(label)}</span>${detail?`<small>${escapeHTML(detail)}</small>`:''}</button>`;
  };
  const selected=(test)=>entries.filter(([,v])=>test(v.result)).map(([id])=>id);
  const current=(test)=>rows.filter(test).map(v=>v.row.id);
  const running=['running','waiting_for_portfolio'].includes(job?.status);
  const failed=job?.progress?.failed || 0;
  const failures=Object.entries(report?.invoices || {}).filter(([,v])=>v.error);
  const title=!job?'No collections run selected':job.status==='completed'?(failed?`Processing finished — ${failed} invoice${failed===1?'':'s'} need review`:'Run completed'):job.status==='interrupted'?'Processing stopped — recovery required':job.status==='analysis_failed'?'Portfolio analysis failed': 'Run in progress';
  $('portfolio-count').textContent=!job?'Ready':running?'Processing':job.status==='completed'?(failed?`${failed} need review`:'Completed'):'Needs recovery';
  updatePromiseCount();
  const mails=entries.flatMap(([,v])=>[...v.result.initial_mail_ids,...v.result.followup_mail_ids]);
  const accepted=new Set(mails);
  const outcomes=visitorCases.flatMap(c=>[c.outbound,...(c.followups||[])]).filter(m=>m && accepted.has(m.id));
  const delivered=outcomes.filter(m=>m.events.some(e=>e.type==='email.delivered') && !m.events.some(e=>['email.bounced','email.failed','email.complained','email.suppressed'].includes(e.type))).length;
  const issues=outcomes.filter(m=>m.events.some(e=>['email.bounced','email.failed','email.complained','email.suppressed'].includes(e.type))).length;
  const reminders=selected(v=>v.initial_mail_ids.length>0),followups=selected(v=>v.followup_mail_ids.length>0);
  const countByLabel=new Map();for(const v of rows){const g=countByLabel.get(v.label)||[];g.push(v.row.id);countByLabel.set(v.label,g);}
  const attention=current(v=>Boolean(v.w?.pending)||['manual_review_required','contact_required','delivery_exception','delivery_unknown','quota_wait','dispute_hold_review_required','reconciliation_required','documents_ready','document_review_required','promise_review_required','reply_received_review_required','followup_due','processing_error'].includes(v.status));
  panel.innerHTML=`<b>${escapeHTML(title)}</b>
    ${job?`<p class="panel-sub">Run #${escapeHTML(job.run_id.slice(0,8))} · ${job.mode==='autopilot'?'Automatic processing':'Review &amp; approve'} · ${escapeHTML(new Date(job.created_at || job.updated_at || Date.now()).toLocaleString())}</p>`:''}
    ${report?`<h3>Results during this run</h3><p class="panel-sub">${job.progress.processed || 0}/${job.progress.total || 0} invoices successfully processed${failed?`; ${failed} need recovery`:''}. Completed processing does not mean invoices are paid.${report.legacy_partial?' Earlier processing predates result tracking; figures are partial.':''}</p>
      <div class="outcome-counts">${card('Invoices reviewed',entries.map(([id])=>id))}${card('Invoices with processing issues',failures.map(([id])=>id))}${card('Invoices sent reminders',reminders,'Submitted to demo inbox')}${card('Invoices sent follow-ups',followups,'Submitted to demo inbox')}${card('Payment promises recorded',selected(v=>v.promise_recorded))}${card('Disputed invoices on hold',selected(v=>v.dispute_on_hold),money(entries.filter(([,v])=>v.result.dispute_on_hold).reduce((n,[id])=>n+Number(state.invoices.find(r=>r.id===id)?.amount || 0),0))+' source exposure; includes existing disputes')}${card('New dispute holds',selected(v=>v.new_dispute_hold))}</div>
      <p class="panel-sub">Delivery updates for these ${mails.length} submitted emails: ${delivered} confirmed delivered · ${issues} with delivery issues · ${outcomes.filter(m=>!m.events.some(e=>['email.delivered','email.bounced','email.failed','email.complained','email.suppressed'].includes(e.type))).length} awaiting confirmation. Delivery is not payment.</p>`:
      `<p class="panel-sub">${job?'This older run has no saved outcome report. Current statuses below cannot establish what it accomplished.':'Run collections to save a per-invoice result report.'}</p>`}
    ${failures.length?`<details class="run-diagnostics"><summary>Review ${failures.length} processing issue(s)</summary>${failures.map(([id,v])=>`<p><b>${escapeHTML(id)}</b>: ${escapeHTML(v.error.message)}<br><small>${escapeHTML(v.error.code)} · ${escapeHTML(v.error.phase)}${v.error.operation?' · '+escapeHTML(v.error.operation):''} · reference ${escapeHTML(v.error.error_id)}</small></p>`).join('')}</details>`:''}
    ${job?.status==='interrupted'?`<p class="explain">${escapeHTML(job.progress?.failure?.message || job.progress?.error || 'This older run has no detailed failure record. A server restart or processing failure left it unfinished. Recover saved work to continue.')}</p>${job.progress?.failure?`<details><summary>Recovery diagnostic</summary><pre>${escapeHTML(JSON.stringify(job.progress.failure,null,2))}</pre></details>`:''}`:''}
    <h3>Needs your action now</h3><div class="outcome-counts">${card('Reminders ready to send',current(v=>v.w?.pending?.tool==='send_email'))}${card('Follow-ups ready to send',current(v=>v.w?.pending?.tool==='send_followup_email'))}${card('Payment promises ready to record',current(v=>v.w?.pending?.tool==='record_promise'))}${card('Invoices needing attention',attention,'Includes approvals and exceptions')}</div>
    <h3>Waiting on customers or delivery now</h3><div class="outcome-counts">${card('Waiting for customer reply',current(v=>v.status==='awaiting_response'))}${card('Customers with recorded payment promises',current(v=>v.status==='promise_recorded'))}${card('Awaiting email delivery confirmation',current(v=>v.status==='awaiting_delivery'))}</div>
    <details class="current-statuses"><summary>Current invoice statuses · ${rows.length} invoices</summary><p class="panel-sub">Live case state for the displayed portfolio snapshot. Includes prior work and replies after the run; not additional run achievements.</p><div class="outcome-counts">${[...countByLabel].map(([label,ids])=>card(label,ids)).join('')}</div></details>
    <p class="panel-sub">Click a count to filter the queue. Source AR is unchanged. Customer replies and payment evidence are simulated.</p>
    ${job?.status==='interrupted'||(job?.status==='completed' && failed)?`<button class="secondary" id="resume-job">${failed?'Retry failed invoices':'Recover unfinished processing'}</button>`:''}`;
  for(const button of panel.querySelectorAll('[data-result]'))button.onclick=()=>{
    outcomeFilter=groups[Number(button.dataset.result)];state.highOnly=false;$('filter-btn').textContent='All urgency';
    renderQueue();renderDetail();$('portfolio-menu').open=false;$('queue-scroll').focus();
  };
  if($('resume-job'))$('resume-job').onclick=()=>launchCaseAgent(job.run_id,job.mode);
}

function renderCaseExecution() {
  const panel=$('case-agent-activity');if(!panel)return;
  const row=state.invoices.find(r=>r.id===state.selectedId),c=visitorCases.find(c=>c.invoice_id===row?.id),w=c?.workflow;
  const changed=panel.dataset.invoice!==row?.id,scrollLeft=changed?0:(panel.querySelector('.case-trace')?.scrollLeft || 0);panel.dataset.invoice=row?.id || '';
  panel.innerHTML=`<div class="activity-head"><span class="activity-title">Invoice processing · ${escapeHTML(row?.id || 'select an invoice')}</span>${w?`<span class="tag state">${w.mode==='limited'?'Review &amp; approve':'Automatic processing'}</span>`:''}</div>
    <p class="panel-sub">Saved backend actions for this invoice only. These are separate from portfolio preparation.</p>
    ${w?`<p class="explain">${escapeHTML(rowView(row).label)} · ${escapeHTML(rowView(row).next)}</p>${w.processing?`<p class="invoice-live-step">Current step: ${escapeHTML(activityLabels[w.activity?.at(-1)?.node] || 'Loading invoice')} · ${w.activity?.at(-1)?.status==='started'?'In progress':'Recorded'}</p>`:''}
      <div class="case-trace" tabindex="0" role="list" aria-label="Recorded invoice processing steps">${(w.activity||[]).slice(-40).map(a=>`<div class="case-trace-item" role="listitem"><b>${escapeHTML(activityLabels[a.node] || a.node)}</b><span class="trace-status">${a.status==='completed'?'Completed':a.status==='started'?'In progress':escapeHTML(a.status)}</span><div>${escapeHTML(a.message)}</div><small>${escapeHTML(new Date(a.timestamp).toLocaleString())}</small></div>`).join('') || '<p>No backend actions recorded yet.</p>'}</div>`:
      `<p class="explain">${c?'This saved case has no recorded LangGraph steps yet.':'This invoice has not been processed by the collection agent yet.'} Run collections to prepare actions; opening the invoice is read-only.</p>`}`;
  const trace=panel.querySelector('.case-trace');if(trace)trace.scrollLeft=scrollLeft;
}

function workflowExtras(c) {
  const w=c.workflow;if(!w)return '';
  const view=rowView(state.invoices.find(r=>r.id===c.invoice_id)||c.snapshot.invoice);
  return `<section class="case-outcome"><h3>${escapeHTML(view.label)}</h3><p><b>Next step:</b> ${escapeHTML(view.next)}</p>
    ${w.followup?`<p><b>Follow-up:</b> ${escapeHTML(w.followup.status)} · promised ${escapeHTML(w.followup.promise_date)} · checked on simulation date ${escapeHTML(w.followup.as_of_date)}. Original reminder stays in history.</p>`:''}
    ${w.promise?`<p>Promise date: <b>${escapeHTML(w.promise.promise_date)}</b>. Amount: ${escapeHTML(w.promise.promise_amount || 'not specified')}. Next review: ${escapeHTML(w.followup_date)} (simulation date).</p>`:''}
    ${w.reconciliation?`<p><b>Synthetic payment match:</b> ${escapeHTML(w.reconciliation.financial_state.replaceAll('_',' '))} · matched ${money(w.reconciliation.matched_amount)} · demo remaining ${money(w.reconciliation.remaining_amount)}. Source AR remains unchanged.</p>`:''}
    ${w.evidence?`<p>${w.evidence.difference_amount?'Evidence discrepancy: '+money(w.evidence.difference_amount)+'. ':''}${w.evidence.missing_documents?.length?'Missing evidence: '+escapeHTML(w.evidence.missing_documents.join(', '))+'. ':''}These are controlled synthetic documents; retrieving them does not send email.</p>
      ${(w.evidence.documents||[]).map(d=>`<details><summary>${escapeHTML(d.title)}</summary><pre>${escapeHTML(d.text)}</pre></details>`).join('')}
      <details><summary>Inspect tool evidence</summary><pre>${escapeHTML(JSON.stringify(w.evidence,null,2))}</pre></details>`:''}</section>`;
}

function bindWorkflowExtras(c) {
  const act=async approved=>{
    caseActionBusy=true;renderCase();renderSendState();
    try{saveCase(await api(`/api/cases/${c.id}/approve`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({event_key:c.workflow.pending.event_key,approved})}));}
    catch(error){showError(error.message);await refreshCases(false);}
    finally{caseActionBusy=false;renderCase();renderSendState();}
  };
  if($('approve-case-action'))$('approve-case-action').onclick=()=>act(true);
  if($('decline-case-action'))$('decline-case-action').onclick=()=>act(false);

}

async function launchCaseAgent(runId,mode) {
  agentJob={run_id:runId,mode,status:'running',progress:{processed:0,total:state.invoices.length}};
  $('start-run').disabled=true;banner('COLLECTIONS RUNNING','Portfolio prepared; processing saved collection actions.');renderWorkflowSummary();renderFlow();
  try{agentJob=(await api(`/api/runs/${runId}/agent`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mode})})).job;connectExecutionStream(runId);}
  catch(error){
    try{agentJob=await api(`/api/runs/${runId}/agent`);}catch(readError){agentJob.status='interrupted';}
    showError(error.message);$('start-run').disabled=['running','waiting_for_portfolio'].includes(agentJob.status);renderWorkflowSummary();
  }
}

async function pollWorkflow() {
  if(workflowPollBusy)return;
  const active=['waiting_for_portfolio','running'].includes(agentJob?.status);
  const checkingDue=dueActive();
  const mailPending=visitorCases.some(c=>[c.outbound,...(c.followups||[])].some(out=>out && !out.events.some(e=>['email.delivered','email.bounced','email.complained','email.failed','email.suppressed'].includes(e.type))));
  if(!active && !checkingDue && !caseActionBusy && !mailPending && !$('invoice-dialog')?.open)return;
  workflowPollBusy=true;
  try {
    if(active && executionStream?.readyState!==1)mergeAgentJob(await api(`/api/runs/${agentJob.run_id}/agent`));
    if(checkingDue)dueJob=await api(`/api/followup-checks/${dueJob.id}`);
    await refreshCases(false);
    if(checkingDue && !dueActive()){ $('start-run').disabled=active;banner('FOLLOW-UP CHECK FINISHED','Saved promises and payment evidence checked; review states remain open.'); }
    renderFollowupControls();renderFlow();renderSendState();
    if(active && !['waiting_for_portfolio','running'].includes(agentJob.status)) {
      $('start-run').disabled=dueActive();
      banner(agentJob.status==='completed'?(agentJob.progress?.failed?'REVIEW REQUIRED':'PROCESSING FINISHED'):'RECOVERY REQUIRED',agentJob.status==='completed'?(agentJob.progress?.failed?`${agentJob.progress.processed}/${agentJob.progress.total} invoices processed; ${agentJob.progress.failed} need review. See Run overview.`:'Case actions saved. Waiting/review states remain open.'):'Open Run overview for the saved reason and recovery action.');
    }
  } catch(error){showError(error.message);}
  finally{workflowPollBusy=false;}
}

function initWorkflowControls() {
  $('start-run').onclick=()=>{
    if(state.status==='running'||dueActive()||['waiting_for_portfolio','running'].includes(agentJob?.status))return;
    if(!workflowReady){showError('Apply sql/009_case_workflow.sql to enable the case agent. Current AR remains available.');return;}
    const dialog=$('agent-mode-dialog');if(dialog.showModal)dialog.showModal();else dialog.setAttribute('open','');
  };
  const close=()=>{const dialog=$('agent-mode-dialog');if(dialog.close)dialog.close();else dialog.removeAttribute('open');};
  $('mode-limited').onclick=()=>{close();startRun('limited');};
  $('mode-autopilot').onclick=()=>{close();startRun('autopilot');};
  $('mode-cancel').onclick=close;
  setInterval(pollWorkflow,1500);
}
