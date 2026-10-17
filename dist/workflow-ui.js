/* Case workflow presentation. Decisions and durable checkpoints live in Python. */
'use strict';
let workflowReady = false;
let agentJob = null;
let pendingMode = null;
let workflowPollBusy = false;
let caseActionBusy = false;
let scenarioSummaries = [];
const workflowLabels = {
  quota_wait:'Waiting for mail quota',processing:'Processing case',ready_for_outreach:'Ready for outreach',awaiting_approval:'Awaiting approval',
  awaiting_delivery:'Awaiting delivery',awaiting_response:'Awaiting customer reply',promise_recorded:'Promise recorded',
  followup_due:'Promise follow-up due',demo_payment_matched:'Payment matched · demo',demo_partial_payment:'Partial payment · demo',
  documents_ready:'Documents ready',contact_required:'Contact needed',delivery_exception:'Prior delivery issue · simulated',
  delivery_unknown:'Send outcome unknown',preventive_review:'Preventive review',monitoring:'Monitoring',
};

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
  return {c,w,status,label:workflowLabels[status] || caseLabels[status] || status,
    next:next || 'Review invoice',latest:latest?.message || (state.status==='completed' && row.draft?'Draft prepared':'Read-only assessment'),timestamp:latest?.timestamp};
}

function renderWorkflowSummary() {
  const panel=$('workflow-summary');if(!panel)return;
  const rows=state.invoices.map(rowView),counts=new Map();
  for(const r of rows)counts.set(r.label,(counts.get(r.label)||0)+1);
  const saved=rows.filter(r=>r.w).length;
  let title=agentJob?.status==='waiting_for_portfolio'?'Portfolio analysis running':agentJob?.status==='running'?`Case agent running · ${agentJob.progress?.processed || 0}/${agentJob.progress?.total || state.invoices.length} processed`:
    agentJob?.status==='analysis_failed'?'Portfolio analysis stopped; start a new run':agentJob?.status==='interrupted'?'Case processing interrupted':saved?'Case outcomes · waiting and review states remain open':'Current portfolio · ready for agent processing';
  panel.innerHTML=`<b>${escapeHTML(title)}</b><div class="outcome-counts">${saved?[...counts].map(([label,n])=>`<span>${n} ${escapeHTML(label.toLowerCase())}</span>`).join(''):'Choose limited or autopilot mode when you start. Source balances remain separate from case outcomes.'}</div>
    ${agentJob?.status==='interrupted'?'<button class="secondary" id="resume-job">Resume saved case processing</button>':''}`;
  if($('resume-job'))$('resume-job').onclick=()=>launchCaseAgent(agentJob.run_id,agentJob.mode);
}

function renderCaseExecution() {
  const panel=$('case-agent-activity');if(!panel)return;
  const row=state.invoices.find(r=>r.id===state.selectedId);const c=visitorCases.find(c=>c.invoice_id===row?.id),w=c?.workflow;
  panel.innerHTML=`<div class="activity-head"><span class="activity-title">${w?'Case agent · '+escapeHTML(c.invoice_id):'Case agent'}</span>${w?`<span class="tag state">${escapeHTML(w.mode)}</span>`:''}</div>
    ${w?`<p class="explain">${escapeHTML(rowView(row).label)} · ${escapeHTML(w.next_action || '')}</p>
      <div class="case-trace">${(w.activity||[]).slice(-12).map(a=>`<div class="case-trace-item"><b>${escapeHTML(a.node)} · ${escapeHTML(a.status)}</b><div>${escapeHTML(a.message)}</div><small>${escapeHTML(new Date(a.timestamp).toLocaleTimeString())}</small></div>`).join('')}</div>`:
      '<p class="explain">Start the agent to run this invoice through the saved LangGraph workflow. This panel shows recorded actions, not private model reasoning.</p>'}`;
}

function workflowExtras(c) {
  const w=c.workflow;if(!w)return '';
  const view=rowView(state.invoices.find(r=>r.id===c.invoice_id)||c.snapshot.invoice);
  const unfinishedReply=c.messages.some(m=>m.channel==='simulated_customer_reply' && ['pending_review','model_attempt_reserved'].includes(m.review?.status));
  return `<section class="case-outcome"><h3>${escapeHTML(view.label)}</h3><p><b>Next action:</b> ${escapeHTML(view.next)}</p>
    ${w.pending && !['send_email','send_followup_email'].includes(w.pending.tool)?`<p>Prepared action: ${escapeHTML(w.pending.tool.replaceAll('_',' '))}</p><button class="secondary" id="approve-case-action" ${caseActionBusy?'disabled':''}>Approve action</button><button class="secondary" id="decline-case-action" ${caseActionBusy?'disabled':''}>Decline</button>`:''}
    ${['send_email','send_followup_email'].includes(w.pending?.tool)?'<p>Review the draft and use its Send button above to approve this action.</p>':''}
    ${(w.processing || unfinishedReply) && !caseActionBusy && agentJob?.status!=='running'?'<button class="secondary" id="resume-case-action">Resume saved processing</button>':''}
    ${w.followup?`<p><b>Follow-up:</b> ${escapeHTML(w.followup.status)} · promised ${escapeHTML(w.followup.promise_date)} · checked on demo date ${escapeHTML(w.followup.as_of_date)}. Original reminder stays in history.</p>`:''}
    ${w.promise?`<p>Promise date: <b>${escapeHTML(w.promise.promise_date)}</b>. Amount: ${escapeHTML(w.promise.promise_amount || 'not specified')}. Check after: ${escapeHTML(w.followup_date)} (demo date).</p>`:''}
    ${w.reconciliation?`<p><b>Synthetic payment match:</b> ${escapeHTML(w.reconciliation.financial_state.replaceAll('_',' '))} · matched ${money(w.reconciliation.matched_amount)} · demo remaining ${money(w.reconciliation.remaining_amount)}. Source AR remains unchanged.</p>`:''}
    ${w.evidence?`<p>${w.evidence.difference_amount?'Evidence discrepancy: '+money(w.evidence.difference_amount)+'. ':''}${w.evidence.missing_documents?.length?'Missing evidence: '+escapeHTML(w.evidence.missing_documents.join(', '))+'. ':''}These are controlled synthetic documents; retrieving them does not send email.</p>
      ${(w.evidence.documents||[]).map(d=>`<details><summary>${escapeHTML(d.title)}</summary><pre>${escapeHTML(d.text)}</pre></details>`).join('')}
      <details><summary>Inspect tool evidence</summary><pre>${escapeHTML(JSON.stringify(w.evidence,null,2))}</pre></details>`:''}</section>`;
}

function bindWorkflowExtras(c) {
  const act=async approved=>{
    caseActionBusy=true;renderCase();
    try{saveCase(await api(`/api/cases/${c.id}/approve`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({event_key:c.workflow.pending.event_key,approved})}));}
    catch(error){showError(error.message);}
    finally{caseActionBusy=false;renderCase();renderSendState();}
  };
  if($('approve-case-action'))$('approve-case-action').onclick=()=>act(true);
  if($('decline-case-action'))$('decline-case-action').onclick=()=>act(false);
  if($('resume-case-action'))$('resume-case-action').onclick=async()=>{
    caseActionBusy=true;
    try{saveCase(await api(`/api/cases/${c.id}/resume`,{method:'POST'}));}
    catch(error){showError(error.message);}
    finally{caseActionBusy=false;renderCase();}
  };
}

async function launchCaseAgent(runId,mode) {
  agentJob={run_id:runId,mode,status:'running',progress:{processed:0,total:state.invoices.length}};
  $('start-run').disabled=true;banner('AGENT RUNNING','Portfolio prepared; processing collection cases.');renderWorkflowSummary();
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
      banner(agentJob.status==='completed'?'PROCESSING FINISHED':'INTERRUPTED',agentJob.status==='completed'?'Case actions saved. Waiting/review states remain open.':'Resume saved case processing below.');
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
