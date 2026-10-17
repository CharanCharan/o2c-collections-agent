/* Explicit simulation date and durable due-check presentation. */
'use strict';
let followupReady=false;
let demoClock=null;
let dueJob=null;
let clockBusy=false;
let dueRequestId=null;
const dueActive=()=>dueJob?.status==='running';
const followupMail=c=>(c?.followups||[]).find(x=>x.event_key===c?.workflow?.followup?.event_key);
const followupDraft=c=>c?.workflow?.followup?.draft;

function updatePromiseCount() {
  const badge=$('promise-count');if(!badge)return;
  let due=0;
  if(demoClock)for(const c of visitorCases) {
    const w=c.workflow || {},p=w.promise || w.scenario?.prior_promise || {};
    const date=p.promise_date || p.date;
    if(date && date<demoClock.demo_date && w.reconciliation?.financial_state!=='fully_matched')due++;
  }
  badge.textContent=dueActive()?'Processing':dueJob?.status==='interrupted'?'Paused':`${due} due`;
}

function renderFollowupControls() {
  const panel=$('followup-controls');if(!panel)return;
  updatePromiseCount();
  if(!followupReady){panel.innerHTML='<b>Promise-to-pay management</b><p class="panel-sub">Apply sql/012_promise_followups.sql to enable the simulation date and promise processing. Current AR remains available.</p>';return;}
  if(!demoClock)return;
  const busy=clockBusy||dueActive()||dueJob?.status==='interrupted'||caseActionBusy||['waiting_for_portfolio','running'].includes(agentJob?.status);
  const signature=JSON.stringify([demoClock,dueJob,busy]);
  if(panel.dataset.signature===signature)return;
  panel.dataset.signature=signature;
  const previous=$('demo-date');const editing=previous && document.activeElement===previous;
  const editedDate=editing?previous.value:null;
  const max=new Date(demoClock.base_date+'T00:00:00Z');max.setUTCDate(max.getUTCDate()+365);
  panel.innerHTML=`<div><b>Promise-to-pay management · simulation date ${escapeHTML(demoClock.demo_date)}</b><p class="panel-sub">Review customers who promised payment. Advance the simulation date to test missed promises, then process due promises under each invoice’s saved mode. Source aging and real service timestamps stay unchanged.</p></div>
    <div class="clock-actions"><label for="demo-date">Simulation date</label><input type="date" id="demo-date" min="${demoClock.demo_date}" max="${max.toISOString().slice(0,10)}" value="${demoClock.demo_date}" ${busy?'disabled':''}>
    <button class="secondary" id="advance-demo-date" ${busy?'disabled':''}>Set simulation date</button><button class="secondary" id="advance-seven-days" ${busy?'disabled':''}>Advance simulation by 7 days</button>
    <button class="primary" id="check-followups" ${busy?'disabled':''}>${dueActive()?'Processing promises…':'Process due promises'}</button>
    ${dueJob?.status==='interrupted'?'<button class="secondary" id="resume-due-check">Continue promise processing</button>':''}</div>
    <p class="panel-sub" id="due-check-status">${dueJob?`${escapeHTML(dueJob.status)} · ${dueJob.progress?.processed||0}/${dueJob.case_ids.length} due cases checked · review date ${escapeHTML(dueJob.as_of_date)}`:'No promise review has run yet. This does not send email until the case mode and policy allow it.'}</p>`;
  if(editing && !busy){$('demo-date').value=editedDate;$('demo-date').focus();}
  const advance=async value=>{
    clockBusy=true;renderFollowupControls();
    try{demoClock=await api('/api/demo-clock',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({demo_date:value})});await refreshCases(false);toast('Simulation date saved. Click Process due promises to process promises.');}
    catch(error){showError(error.message);}
    finally{clockBusy=false;renderFollowupControls();}
  };
  $('advance-demo-date').onclick=()=>advance($('demo-date').value);
  $('advance-seven-days').onclick=()=>{const d=new Date(demoClock.demo_date+'T00:00:00Z');d.setUTCDate(d.getUTCDate()+7);advance(d.toISOString().slice(0,10));};
  $('check-followups').onclick=async()=>{
    clockBusy=true;dueRequestId ||= crypto.randomUUID();renderFollowupControls();
    try{const result=await api('/api/followup-checks',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({request_id:dueRequestId})});dueJob=result.job;dueRequestId=null;$('start-run').disabled=dueActive();}
    catch(error){showError(error.message);}
    finally{clockBusy=false;renderFollowupControls();}
  };
  if($('resume-due-check'))$('resume-due-check').onclick=async()=>{
    try{dueJob=(await api(`/api/followup-checks/${dueJob.id}/resume`,{method:'POST'})).job;renderFollowupControls();}
    catch(error){showError(error.message);}
  };
}

async function initFollowups(health) {
  followupReady=Boolean(health.followups?.ready);
  if(followupReady){demoClock=await api('/api/demo-clock');dueJob=(await api('/api/followup-checks')).job;}
  renderFollowupControls();
}

