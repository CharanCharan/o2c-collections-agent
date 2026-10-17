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

function renderFollowupControls() {
  const panel=$('followup-controls');if(!panel)return;
  if(!followupReady){panel.innerHTML='<b>Promise follow-ups</b><p class="panel-sub">Apply sql/012_promise_followups.sql to enable the demo clock and due checks. Current AR remains available.</p>';return;}
  if(!demoClock)return;
  const busy=clockBusy||dueActive()||dueJob?.status==='interrupted'||caseActionBusy||['waiting_for_portfolio','running'].includes(agentJob?.status);
  const signature=JSON.stringify([demoClock,dueJob,busy]);
  if(panel.dataset.signature===signature)return;
  panel.dataset.signature=signature;
  const previous=$('demo-date');const editing=previous && document.activeElement===previous;
  const editedDate=editing?previous.value:null;
  const max=new Date(demoClock.base_date+'T00:00:00Z');max.setUTCDate(max.getUTCDate()+365);
  panel.innerHTML=`<div><b>Promise follow-ups · demo date ${escapeHTML(demoClock.demo_date)}</b><p class="panel-sub">Advance simulation time, then check saved promises and synthetic payment evidence. Source aging and ML keep the AR snapshot date. Real email timestamps and quotas use actual UTC time. No background scheduler.</p></div>
    <div class="clock-actions"><label for="demo-date">Demo date</label><input type="date" id="demo-date" min="${demoClock.demo_date}" max="${max.toISOString().slice(0,10)}" value="${demoClock.demo_date}" ${busy?'disabled':''}>
    <button class="secondary" id="advance-demo-date" ${busy?'disabled':''}>Save demo date</button><button class="secondary" id="advance-seven-days" ${busy?'disabled':''}>Advance 7 days</button>
    <button class="primary" id="check-followups" ${busy?'disabled':''}>${dueActive()?'Checking promises…':'Check due follow-ups'}</button>
    ${dueJob?.status==='interrupted'?'<button class="secondary" id="resume-due-check">Resume interrupted check</button>':''}</div>
    <p class="panel-sub" id="due-check-status">${dueJob?`${escapeHTML(dueJob.status)} · ${dueJob.progress?.processed||0}/${dueJob.case_ids.length} due cases checked · saved check date ${escapeHTML(dueJob.as_of_date)}`:'No due check run yet. This does not send email until the case mode and policy allow it.'}</p>`;
  if(editing && !busy){$('demo-date').value=editedDate;$('demo-date').focus();}
  const advance=async value=>{
    clockBusy=true;renderFollowupControls();
    try{demoClock=await api('/api/demo-clock',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({demo_date:value})});await refreshCases(false);toast('Demo date saved. Click Check due follow-ups to process promises.');}
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

function initTableNavigation() {
  const viewport=$('queue-scroll'),slider=$('table-position');
  const sync=()=>{
    const max=Math.max(0,viewport.scrollWidth-viewport.clientWidth);
    slider.disabled=!max;slider.value=max?Math.round(100*viewport.scrollLeft/max):0;
    $('table-scroll-left').disabled=viewport.scrollLeft<=0;
    $('table-scroll-right').disabled=viewport.scrollLeft>=max-1;
    $('table-scroll-hint').textContent=max?'Scroll sideways for all 8 columns →':'All 8 columns · scroll sideways if needed';
  };
  slider.oninput=()=>{viewport.scrollLeft=(viewport.scrollWidth-viewport.clientWidth)*Number(slider.value)/100;sync();};
  $('table-scroll-left').onclick=()=>{viewport.scrollLeft=Math.max(0,viewport.scrollLeft-Math.max(250,viewport.clientWidth*.7));sync();};
  $('table-scroll-right').onclick=()=>{viewport.scrollLeft=Math.min(viewport.scrollWidth-viewport.clientWidth,viewport.scrollLeft+Math.max(250,viewport.clientWidth*.7));sync();};
  viewport.addEventListener('scroll',sync);window.addEventListener('resize',sync);
  if(window.ResizeObserver)new ResizeObserver(sync).observe(viewport);
  sync();
}
