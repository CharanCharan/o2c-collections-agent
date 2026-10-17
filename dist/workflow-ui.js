/* Case workflow presentation. Decisions and durable checkpoints live in Python. */
'use strict';
let workflowReady = false;
let agentJob = null;
let pendingMode = null;
let workflowPollBusy = false;
let caseActionBusy = false;
let scenarioSummaries = [];
let outcomeFilter = null;
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
  const busy=caseActionBusy||dueActive()||state.status==='running'||['running','waiting_for_portfolio'].includes(agentJob?.status);
  return Boolean(unfinished && !w.pending && !busy);
}

function invoiceCaseHeader(c) {
  if(!c)return '';
  const continuation=invoiceContinuation(c);
  return `<div class="case-reference"><span>Collection case</span><code title="${escapeHTML(c.id)}">#${escapeHTML(c.id.slice(0,8))}</code><span class="saved-indicator">Saved</span></div>
    ${continuation?'<div class="invoice-continue"><p>Invoice processing did not finish. Continue from the last saved step.</p><button class="secondary" id="resume-case-action">Continue invoice processing</button></div>':''}`;
}

function refreshInvoiceCaseHeader(c) {
  const panel=$('invoice-case-controls');if(!panel)return;
  panel.innerHTML=invoiceCaseHeader(c);panel.hidden=!c;
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
  const title=!job?'No collections run selected':job.status==='completed'?'Run completed':job.status==='interrupted'?'Run interrupted — partial results':job.status==='analysis_failed'?'Portfolio analysis failed': 'Run in progress';
  $('portfolio-count').textContent=!job?'Ready':running?'Processing':job.status==='completed'?'Completed':'Interrupted';
  updatePromiseCount();
  const mails=entries.flatMap(([,v])=>[...v.result.initial_mail_ids,...v.result.followup_mail_ids]);
  const accepted=new Set(mails);
  const outcomes=visitorCases.flatMap(c=>[c.outbound,...(c.followups||[])]).filter(m=>m && accepted.has(m.id));
  const delivered=outcomes.filter(m=>m.events.some(e=>e.type==='email.delivered') && !m.events.some(e=>['email.bounced','email.failed','email.complained','email.suppressed'].includes(e.type))).length;
  const issues=outcomes.filter(m=>m.events.some(e=>['email.bounced','email.failed','email.complained','email.suppressed'].includes(e.type))).length;
  const reminders=selected(v=>v.initial_mail_ids.length>0),followups=selected(v=>v.followup_mail_ids.length>0);
  const countByLabel=new Map();for(const v of rows){const g=countByLabel.get(v.label)||[];g.push(v.row.id);countByLabel.set(v.label,g);}
  const attention=current(v=>Boolean(v.w?.pending)||['manual_review_required','contact_required','delivery_exception','delivery_unknown','quota_wait','dispute_hold_review_required','reconciliation_required','documents_ready','document_review_required','promise_review_required','reply_received_review_required','followup_due'].includes(v.status));
  panel.innerHTML=`<b>${escapeHTML(title)}</b>
    ${job?`<p class="panel-sub">Run #${escapeHTML(job.run_id.slice(0,8))} · ${job.mode==='autopilot'?'Automatic processing':'Review &amp; approve'} · ${escapeHTML(new Date(job.created_at || job.updated_at || Date.now()).toLocaleString())}</p>`:''}
    ${report?`<h3>Results during this run</h3><p class="panel-sub">${job.progress.processed || 0}/${job.progress.total || 0} invoices reviewed. Completed processing does not mean invoices are paid.${report.legacy_partial?' Earlier processing predates result tracking; figures are partial.':''}</p>
      <div class="outcome-counts">${card('Invoices reviewed',entries.map(([id])=>id))}${card('Invoices sent reminders',reminders,'Submitted to demo inbox')}${card('Invoices sent follow-ups',followups,'Submitted to demo inbox')}${card('Payment promises recorded',selected(v=>v.promise_recorded))}${card('Disputed invoices on hold',selected(v=>v.dispute_on_hold),money(entries.filter(([,v])=>v.result.dispute_on_hold).reduce((n,[id])=>n+Number(state.invoices.find(r=>r.id===id)?.amount || 0),0))+' source exposure; includes existing disputes')}${card('New dispute holds',selected(v=>v.new_dispute_hold))}</div>
      <p class="panel-sub">Delivery updates for these ${mails.length} submitted emails: ${delivered} confirmed delivered · ${issues} with delivery issues · ${outcomes.filter(m=>!m.events.some(e=>['email.delivered','email.bounced','email.failed','email.complained','email.suppressed'].includes(e.type))).length} awaiting confirmation. Delivery is not payment.</p>`:
      `<p class="panel-sub">${job?'This older run has no saved outcome report. Current statuses below cannot establish what it accomplished.':'Run collections to save a per-invoice result report.'}</p>`}
    <h3>Needs your action now</h3><div class="outcome-counts">${card('Reminders ready to send',current(v=>v.w?.pending?.tool==='send_email'))}${card('Follow-ups ready to send',current(v=>v.w?.pending?.tool==='send_followup_email'))}${card('Payment promises ready to record',current(v=>v.w?.pending?.tool==='record_promise'))}${card('Invoices needing attention',attention,'Includes approvals and exceptions')}</div>
    <h3>Waiting on customers or delivery now</h3><div class="outcome-counts">${card('Waiting for customer reply',current(v=>v.status==='awaiting_response'))}${card('Customers with recorded payment promises',current(v=>v.status==='promise_recorded'))}${card('Awaiting email delivery confirmation',current(v=>v.status==='awaiting_delivery'))}</div>
    <details class="current-statuses"><summary>Current invoice statuses · ${rows.length} invoices</summary><p class="panel-sub">Live case state for the displayed portfolio snapshot. Includes prior work and replies after the run; not additional run achievements.</p><div class="outcome-counts">${[...countByLabel].map(([label,ids])=>card(label,ids)).join('')}</div></details>
    <p class="panel-sub">Click a count to filter the queue. Source AR is unchanged. Customer replies and payment evidence are simulated.</p>
    ${job?.status==='interrupted'?'<button class="secondary" id="resume-job">Continue collections run</button>':''}`;
  for(const button of panel.querySelectorAll('[data-result]'))button.onclick=()=>{
    outcomeFilter=groups[Number(button.dataset.result)];state.highOnly=false;$('filter-btn').textContent='All urgency';
    renderQueue();renderDetail();$('portfolio-menu').open=false;$('queue-scroll').focus();
  };
  if($('resume-job'))$('resume-job').onclick=()=>launchCaseAgent(job.run_id,job.mode);
}

function renderCaseExecution() {
  const panel=$('case-agent-activity');if(!panel)return;
  const row=state.invoices.find(r=>r.id===state.selectedId);const c=visitorCases.find(c=>c.invoice_id===row?.id),w=c?.workflow;
  panel.innerHTML=`<div class="activity-head"><span class="activity-title">${w?'Invoice activity · '+escapeHTML(c.invoice_id):'Invoice activity'}</span>${w?`<span class="tag state">${w.mode==='limited'?'Review &amp; approve':'Automatic processing'}</span>`:''}</div>
    ${w?`<p class="explain">${escapeHTML(rowView(row).label)} · ${escapeHTML(w.next_action || '')}</p>
      <div class="case-trace">${(w.activity||[]).slice(-12).map(a=>`<div class="case-trace-item"><b>${escapeHTML(activityLabels[a.node] || a.node)} · ${a.status==='completed'?'Completed':a.status==='started'?'In progress':escapeHTML(a.status)}</b><div>${escapeHTML(a.message)}</div><small>${escapeHTML(new Date(a.timestamp).toLocaleTimeString())}</small></div>`).join('')}</div>`:
      '<p class="explain">Run collections to process this invoice. This panel shows recorded actions and outcomes.</p>'}`;
}

function workflowExtras(c) {
  const w=c.workflow;if(!w)return '';
  const view=rowView(state.invoices.find(r=>r.id===c.invoice_id)||c.snapshot.invoice);
  return `<section class="case-outcome"><h3>${escapeHTML(view.label)}</h3><p><b>Next step:</b> ${escapeHTML(view.next)}</p>
    ${w.pending && !['send_email','send_followup_email'].includes(w.pending.tool)?`<p>Prepared action: ${escapeHTML(actionLabels[w.pending.tool] || w.pending.tool.replaceAll('_',' '))}</p><button class="secondary" id="approve-case-action" ${caseActionBusy?'disabled':''}>${escapeHTML(actionLabels[w.pending.tool] || 'Approve action')}</button><button class="secondary" id="decline-case-action" ${caseActionBusy?'disabled':''}>Leave for review</button>`:''}
    ${['send_email','send_followup_email'].includes(w.pending?.tool)?'<p>Review the draft and use its Send button above to approve this action.</p>':''}

    ${w.followup?`<p><b>Follow-up:</b> ${escapeHTML(w.followup.status)} · promised ${escapeHTML(w.followup.promise_date)} · checked on simulation date ${escapeHTML(w.followup.as_of_date)}. Original reminder stays in history.</p>`:''}
    ${w.promise?`<p>Promise date: <b>${escapeHTML(w.promise.promise_date)}</b>. Amount: ${escapeHTML(w.promise.promise_amount || 'not specified')}. Next review: ${escapeHTML(w.followup_date)} (simulation date).</p>`:''}
    ${w.reconciliation?`<p><b>Synthetic payment match:</b> ${escapeHTML(w.reconciliation.financial_state.replaceAll('_',' '))} · matched ${money(w.reconciliation.matched_amount)} · demo remaining ${money(w.reconciliation.remaining_amount)}. Source AR remains unchanged.</p>`:''}
    ${w.evidence?`<p>${w.evidence.difference_amount?'Evidence discrepancy: '+money(w.evidence.difference_amount)+'. ':''}${w.evidence.missing_documents?.length?'Missing evidence: '+escapeHTML(w.evidence.missing_documents.join(', '))+'. ':''}These are controlled synthetic documents; retrieving them does not send email.</p>
      ${(w.evidence.documents||[]).map(d=>`<details><summary>${escapeHTML(d.title)}</summary><pre>${escapeHTML(d.text)}</pre></details>`).join('')}
      <details><summary>Inspect tool evidence</summary><pre>${escapeHTML(JSON.stringify(w.evidence,null,2))}</pre></details>`:''}</section>`;
}

function bindWorkflowExtras(c) {
  const act=async approved=>{
    caseActionBusy=true;renderCase();
    try{saveCase(await api(`/api/cases/${c.id}/approve`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({event_key:c.workflow.pending.event_key,approved})}));}
    catch(error){showError(error.message);await refreshCases(false);}
    finally{caseActionBusy=false;renderCase();renderSendState();}
  };
  if($('approve-case-action'))$('approve-case-action').onclick=()=>act(true);
  if($('decline-case-action'))$('decline-case-action').onclick=()=>act(false);

}

async function launchCaseAgent(runId,mode) {
  agentJob={run_id:runId,mode,status:'running',progress:{processed:0,total:state.invoices.length}};
  $('start-run').disabled=true;banner('COLLECTIONS RUNNING','Portfolio prepared; processing saved collection actions.');renderWorkflowSummary();
  try{agentJob=(await api(`/api/runs/${runId}/agent`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mode})})).job;}
  catch(error){agentJob.status='interrupted';showError(error.message);$('start-run').disabled=false;}
}

async function pollWorkflow() {
  if(workflowPollBusy)return;
  const active=['waiting_for_portfolio','running'].includes(agentJob?.status);
  const checkingDue=dueActive();
  const mailPending=visitorCases.some(c=>[c.outbound,...(c.followups||[])].some(out=>out && !out.events.some(e=>['email.delivered','email.bounced','email.complained','email.failed','email.suppressed'].includes(e.type))));
  if(!active && !checkingDue && !caseActionBusy && !mailPending)return;
  workflowPollBusy=true;
  try {
    if(active)agentJob=await api(`/api/runs/${agentJob.run_id}/agent`);
    if(checkingDue)dueJob=await api(`/api/followup-checks/${dueJob.id}`);
    await refreshCases(false);
    if(checkingDue && !dueActive()){ $('start-run').disabled=active;banner('FOLLOW-UP CHECK FINISHED','Saved promises and payment evidence checked; review states remain open.'); }
    renderFollowupControls();
    if(active && !['waiting_for_portfolio','running'].includes(agentJob.status)) {
      $('start-run').disabled=dueActive();
      banner(agentJob.status==='completed'?'PROCESSING FINISHED':'INTERRUPTED',agentJob.status==='completed'?'Case actions saved. Waiting/review states remain open.':'Continue collections run below.');
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
