/* UI only: Python produces all invoice results. This file renders them. */
"use strict";

const stages = [
  ["ingest", "Load receivables", "Read a fresh Supabase snapshot"],
  ["validate", "Validate invoice data", "Check IDs, amounts, dates and history"],
  ["assess", "Assess collection urgency", "Apply documented rules; pause disputes"],
  ["predict", "Predict payment risk", "Apply trained model; inspect evidence"],
  ["prioritize", "Prioritize accounts", "Rank eligible balance × predicted risk"],
  ["draft", "Draft and check reminders", "LLM phrasing or labelled template fallback"],
];
const riskFeatureLabels = {
  days_overdue_capped: "Invoice aging", late_rate: "Previous late payments",
  broken_promises_capped: "Broken payment promises", log_balance: "Balance size", no_history: "No prior history",
};
const state = {
  invoices: [], selectedId: null, currentRun: null, status: "idle", legacyRun: false,
  highOnly: false, queueStage: "overdue", events: [], eventIds: new Set(), stageStatus: {}, source: null,
};
let visitorCases = [];
let sendBusy = false;
let caseLoadError = '';
let casesLoaded = false;
let pendingCaseReply = null;
const caseLabels = {
  awaiting_outreach: 'Ready for outreach',
  awaiting_response: 'Awaiting customer response',
  reply_received_review_required: 'Reply saved · processing incomplete; review required',
  dispute_hold_review_required: 'Dispute — collections paused',
  reconciliation_required: 'Payment claim · reconciliation required',
  promise_review_required: 'Promise proposed · review required',
  document_review_required: 'Document request · review required',
  manual_review_required: 'Human review needed',
};
let mailEnabled = false;
let publicMode = false;
const $ = (id) => document.getElementById(id);
const escapeHTML = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
}[c]));
const money = (amount) => new Intl.NumberFormat("en-US", {
  style: "currency", currency: "USD", maximumFractionDigits: 2,
}).format(Number(amount || 0));
const dateLabel = (iso) => new Date(`${iso}T00:00:00`).toLocaleDateString("en-US", {
  month: "short", day: "numeric", year: "numeric",
});

async function api(path, options = {}) {
  const headers = options.headers || {};
  const response = await fetch(path, {cache: "no-store", ...options, headers});
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {const error=new Error(data.detail || `Request failed (${response.status})`);error.status=response.status;throw error;}
  return data;
}

function banner(label, message) {
  $("state-label").textContent = label;
  $("run-caption").textContent = message;
}

function toast(message) {
  $("toast").textContent = message;
  $("toast").classList.add("show");
  setTimeout(() => $("toast").classList.remove("show"), 3500);
}

function showError(message) {
  $("error-box").textContent = message;
  $("error-box").hidden = false;
}

function applySnapshot(snapshot) {
  if (!snapshot) return;
  state.invoices = snapshot.invoices || [];
  if (!state.invoices.some((row) => row.id === state.selectedId)) {
    state.selectedId = state.invoices[0]?.id || null;
  }
  const s = snapshot.summary;
  $("as-of").textContent = snapshot.as_of_date ? `Snapshot · ${snapshot.as_of_date} · USD` : "Waiting for validated data";
  $("metric-open").textContent = money(s.open_balance);
  $("open-note").textContent = `${s.open_invoice_count} open invoices · ${s.customer_count} customers`;
  $("metric-past-due").textContent = money(s.past_due_balance);
  $("past-due-note").textContent = `${s.past_due_percent}% of open balance`;
  $("metric-ninety").textContent = money(s.ninety_plus_balance);
  $("ninety-note").textContent = `${s.ninety_plus_count} invoices at least 90 days overdue`;
  $("metric-high").textContent = s.high_urgency_count;
  $("metric-eligible").textContent = money(s.eligible_balance);
  $("eligible-note").textContent = `${s.eligible_count} eligible invoices · ${s.disputed_count} disputed`;
  $("preventive-caption").textContent = s.pre_due_count === undefined ? 'Older snapshot: no pre-due review stage.' : `${s.pre_due_count} not-yet-due invoices · ${money(s.pre_due_balance)} · ${s.preventive_review_count} at the seven-day review checkpoint`;
  renderModel(snapshot.models, snapshot.model);
  renderQueue();
  renderDetail();
}

function renderModel(models, legacyModel) {
  const element = $("model-evidence");
  const cards = models && Object.keys(models).length ? Object.entries(models) : legacyModel ? [['overdue', legacyModel]] : [];
  if (!cards.length) {
    element.innerHTML = '<summary>Payment-risk model evidence</summary><p>No trained prediction in this snapshot. Older M2 runs retain their original rule-based results.</p>';
    return;
  }
  element.innerHTML = `<summary>Model evidence · ${cards.length} model(s) · separate synthetic holdouts</summary>
    <p>Before due: predict becoming overdue. After due: predict remaining unpaid for another 30 days. These are different targets; neither is independent proof of the other. Scores are not combined.</p>` + cards.map(([stage, model]) => {
    const test = model.evaluation.splits.test, m = test.logistic, baseline = test.constant_baseline;
    return `<section><h3>${stage === 'pre_due' ? 'Prevention · scored seven days before due' : 'Recovery · scored after due'} · ${test.rows} invoices</h3>
    <p><b>Target:</b> ${escapeHTML(model.target)}. <b>${escapeHTML(model.limitation)}</b></p>
    <table><thead><tr><th>Later-date holdout · ${escapeHTML(test.snapshot_start)} to ${escapeHTML(test.snapshot_end)}</th><th>Constant baseline</th><th>Logistic model</th></tr></thead>
    <tbody><tr><td>ROC AUC · higher is better</td><td>${baseline.roc_auc.toFixed(3)}</td><td>${m.roc_auc.toFixed(3)}</td></tr>
    <tr><td>Average precision · higher is better</td><td>${baseline.average_precision.toFixed(3)}</td><td>${m.average_precision.toFixed(3)}</td></tr>
    <tr><td>Brier error · lower is better</td><td>${baseline.brier.toFixed(3)}</td><td>${m.brier.toFixed(3)}</td></tr></tbody></table>
    <p>Calibration is imperfect; synthetic metrics do not establish real customer accuracy. Snapshot history is assumed known at scoring time.</p>
    <p>Version: ${escapeHTML(model.model_version)}<br>Artifact SHA-256: ${escapeHTML(model.artifact_sha256)}<br>Training source SHA-256: ${escapeHTML(model.training_data.sha256)}</p>
    <details><summary>Calibration bins · predicted versus observed outcome</summary><pre>${escapeHTML(JSON.stringify(m.calibration_bins, null, 2))}</pre></details></section>`;
  }).join('');
}

const probability = p => p?.probability_overdue ?? p?.probability_unpaid_30d;
const isPreDue = p => p?.risk_type === 'pre_due_overdue';
const stageLabel = row => row.lifecycle === 'pre_due' ? 'Prevention' : row.lifecycle === 'due_today' ? 'Due today' : row.lifecycle === 'settled' ? 'No balance' : 'Recovery';
const timingLabel = row => row.days > 0 ? `${row.days} days overdue` : row.days_to_due > 0 ? `Due in ${row.days_to_due} days` : 'Due today';

function renderQueue() {
  $("filter-btn").disabled = !outcomeFilter && state.queueStage === "pre_due";
  $("preventive-caption").hidden=Boolean(outcomeFilter) || state.queueStage!=="pre_due";
  const rows = state.invoices.filter(row => (!outcomeFilter || outcomeFilter.ids.includes(row.id)) && (!state.highOnly || (row.level === 'high' && row.eligible)) &&
    (outcomeFilter || (state.queueStage === 'pre_due' ? ['pre_due','due_today'].includes(row.lifecycle) : row.days > 0)));
  if (!rows.length) state.selectedId = null;
  else if (!rows.some(row => row.id === state.selectedId)) state.selectedId = rows[0].id;
  $("queue-sub").textContent = `${rows.length} shown${outcomeFilter ? ' · '+outcomeFilter.label : ''} · totals above: full portfolio`;
  $("stage-overdue").setAttribute('aria-pressed', String(!outcomeFilter && state.queueStage === 'overdue'));
  $("stage-preventive").setAttribute('aria-pressed', String(!outcomeFilter && state.queueStage === 'pre_due'));
  $("overdue-count").textContent = state.invoices.filter(r => r.days > 0).length;
  $("preventive-count").textContent = state.invoices.filter(r => ['pre_due','due_today'].includes(r.lifecycle)).length;
  $("filter-btn").setAttribute('aria-pressed', String(state.highOnly));
  $("queue").innerHTML = rows.length ? rows.map((row) => {
    const v=rowView(row);
    return `<tr tabindex="-1" data-id="${escapeHTML(row.id)}" aria-label="Open invoice ${escapeHTML(row.id)} for ${escapeHTML(row.customer)}" aria-haspopup="dialog" aria-controls="invoice-dialog" class="${row.id===state.selectedId?'selected':''}">
      <td><div class="cust">${escapeHTML(row.customer)}</div><div class="subline">${escapeHTML(row.id)}</div><button class="invoice-open" type="button" aria-haspopup="dialog" aria-controls="invoice-dialog" aria-label="Open invoice ${escapeHTML(row.id)} for ${escapeHTML(row.customer)}">Open invoice <span aria-hidden="true">›</span></button></td>
      <td class="amount">${money(row.amount)}${v.w?.reconciliation?`<div class="subline">Demo remaining ${money(v.w.reconciliation.remaining_amount)}</div>`:''}</td>
      <td>${dateLabel(row.due)}<div class="subline">${escapeHTML(timingLabel(row))}</div></td>
      <td><span class="tag ${row.score == null ? 'state' : row.level}">${row.score == null ? (row.days === 0 ? 'Not overdue' : 'Awaiting rules') : `${row.score}/100 · ${escapeHTML(row.level)}`}</span></td>
      <td>${row.prediction?.status==='scored'?`<strong>${(100*probability(row.prediction)).toFixed(1)}%</strong><div class="subline">${isPreDue(row.prediction)?'Becomes overdue':'Unpaid in 30 days'}</div>`:'<span class="subline">No matching prediction</span>'}</td>
      <td><span class="tag ${v.status.includes('dispute')?'warn':'state'}">${escapeHTML(v.label)}</span></td>
      <td>${escapeHTML(v.latest)}${v.timestamp?`<div class="subline">${escapeHTML(new Date(v.timestamp).toLocaleTimeString())}</div>`:''}</td><td>${escapeHTML(v.next)}</td>
    </tr>`;
  }).join('') : `<tr><td colspan="8" class="empty-state">${state.invoices.length?'No invoices match this filter.':'Waiting for invoice data.'}</td></tr>`;
  $('clear-outcome-filter').hidden=!outcomeFilter;
  renderWorkflowSummary();renderCaseExecution();
  $("queue").querySelectorAll("tr[data-id]").forEach((row) => {
    const select = () => openInvoiceWorkspace(row.dataset.id);
    row.addEventListener("click", select);
    row.addEventListener("keydown", (event) => {
      if (event.target === row && (event.key === "Enter" || event.key === " ")) {event.preventDefault(); select();}
    });
  });
}

function renderDetail() {
  renderCase();
  const row = state.invoices.find((r) => r.id === state.selectedId);
  if (!row) {
    $("detail").innerHTML = '<div class="panel-title">Invoice detail</div><p class="explain">Select an invoice from the current queue to inspect its data and reminder.</p>';
    return;
  }
  const prediction = row.prediction;
  const mlDetails = prediction?.status === 'scored' ? `
    <div class="explain"><b>${isPreDue(prediction) ? 'Predicted overdue risk' : 'Predicted non-settlement risk'}: ${(100 * probability(prediction)).toFixed(1)}%</b>
      <p>${isPreDue(prediction) ? 'Not fully paid by the end of due date' : 'Outstanding balance remains on'} ${escapeHTML(prediction.horizon_date)} · scored as of ${escapeHTML(prediction.scored_as_of)}.</p>
      <ul>${[...prediction.contributions].sort((a,b) => Math.abs(b.log_odds_contribution) - Math.abs(a.log_odds_contribution)).slice(0,3).map(c => `<li>${escapeHTML(riskFeatureLabels[c.feature] || c.feature)}: ${escapeHTML(c.direction)} estimated risk versus the typical training invoice.</li>`).join('')}</ul>
      ${prediction.warnings.map(w => `<p>${escapeHTML(w)}</p>`).join('')}
      <p>Synthetic-trained estimate; not confidence in an agent action. Contributions are model associations, not causes.</p>
      <p>Ranking index: ${row.priority_index ? money(row.priority_index) : 'Awaiting ranking'} = balance × predicted risk; ranked only within this invoice stage, not a cash forecast. Disputes stay paused.</p>
      <details><summary>Inspect model inputs and version</summary><pre>${escapeHTML(JSON.stringify(prediction, null, 2))}</pre></details></div>`
    : `<p class="explain">${escapeHTML(prediction?.reason || 'No trained risk prediction in this historical snapshot.')}</p>`;
  updateInvoiceDialogTitle(row);
  const currentCase = visitorCases.find(c => c.invoice_id === row.id);
  const draftRow = currentCase?.snapshot.invoice || row;
  const draft = followupDraft(currentCase) || draftRow.draft;
  $("detail").innerHTML = `
    <section class="invoice-case-controls" id="invoice-case-controls" aria-label="Selected invoice processing" hidden></section>
    <div class="detail-top"><div><div class="detail-name">${escapeHTML(row.customer)}</div><div class="detail-id">${escapeHTML(row.id)} · ${escapeHTML(row.segment)}</div></div>
      <span class="tag ${row.score === null ? "state" : row.level}">${row.score ?? "—"}/100</span></div>
    <div class="detail-grid">
      <div class="detail-metric"><label>Open balance</label><strong>${money(row.amount)}</strong></div>
      <div class="detail-metric"><label>Timing</label><strong>${escapeHTML(timingLabel(row))}</strong></div>
      <div class="detail-metric"><label>Due date</label><strong>${dateLabel(row.due)}</strong></div>
      <div class="detail-metric"><label>Next step</label><strong id="detail-next-action">${escapeHTML(rowView(row).next)}</strong></div>
    </div>
    <div class="draft"><div class="draft-head">${followupDraft(currentCase)?'Follow-up reminder':'Reminder'} <span>${draft ? (draft.generation_mode === "llm_assisted_validated_facts" ? "LLM · REVIEW REQUIRED" : draft.generation_mode === "template_fallback_no_llm_approval" ? "FALLBACK TEMPLATE · REVIEW" : "TEMPLATE · NO LLM") : "NO DRAFT"}</span><button class="secondary" id="send-draft" disabled>Send reminder</button></div>
      ${draft ? `<div class="draft-subject">${escapeHTML(draft.subject)}</div><pre class="draft-body">${escapeHTML(draft.body)}</pre>` : `<div class="draft-body">${row.dispute ? "Reminders paused for an active dispute." : row.days === 0 ? "Pre-due risk is for preventive review. Reminder drafting/approval currently remains in the overdue workflow." : "Run collections to prepare reminders for eligible invoices with urgency scores of at least 35."}</div>`}
    </div>
    <p class="explain" id="draft-email-status"></p>
    ${currentCase ? `<p class="panel-sub">Draft saved with case snapshot ${escapeHTML(currentCase.snapshot.as_of_date)} · run ${escapeHTML(currentCase.run_id.slice(0,8))}. Sending uses this displayed draft.</p>` : ''}
    ${draftRow.draft_audit ? `<details class="explain"><summary>Draft validation and tool evidence</summary><pre>${escapeHTML(JSON.stringify(draftRow.draft_audit, null, 2))}</pre></details>` : ''}
    <details class="explain"><summary>Why this action and risk evidence</summary>
    <div class="explain"><b>Why this action?</b><ul>${row.reasons.length ? row.reasons.map((reason) => `<li>${escapeHTML(reason)}</li>`).join("") : "<li>Waiting for policy assessment.</li>"}</ul>
      <span>Rule score measures urgency. It is not a predicted probability.</span></div>
    ${mlDetails}
    </details>
    `;
  $("send-draft").onclick = sendDraft;
  renderSendState();
}

function renderFlow() {
  let completed = 0;
  const visibleStages = state.legacyRun ? stages.filter(([id]) => id !== "predict") : stages;
  $("flow").innerHTML = visibleStages.map(([id, name, desc], i) => {
    const status = state.stageStatus[id];
    if (status === "completed") completed++;
    const cls = status === "completed" ? "complete" : status === "started" ? "active" : status === "failed" ? "failed" : "";
    const symbol = status === "completed" ? "✓" : status === "failed" ? "!" : i + 1;
    return `<div class="step ${cls}" role="listitem"><div class="step-icon">${symbol}</div><div><div class="step-name">${name}</div><div class="step-desc">${desc}</div></div><div class="step-meta">${status || "Waiting"}</div></div>`;
  }).join("");
  $("progress-bar").style.width = `${completed / visibleStages.length * 100}%`;
}

function addEvent(event) {
  if (state.eventIds.has(event.event_id)) return;
  state.eventIds.add(event.event_id);
  state.events.push(event);
  $("event-count").textContent = `${state.events.length} events`;
  const item = document.createElement("div");
  item.className = "event";
  const facts = {run_id: event.run_id, event_id: event.event_id, stage: event.stage,
    status: event.status, duration_ms: event.duration_ms, result: event.result, error: event.error};
  item.innerHTML = `<div class="event-icon">${["failed", "warning"].includes(event.status) ? "!" : event.status === "started" ? "↗" : "✓"}</div>
    <div class="event-text"><b>${escapeHTML(event.stage)} · ${escapeHTML(event.status)}</b><div>${escapeHTML(event.message)}</div>
      <details><summary>Inspect output</summary><pre>${escapeHTML(JSON.stringify(facts, null, 2))}</pre></details></div>
    <div class="event-time">${new Date(event.timestamp).toLocaleTimeString([], {hour:"2-digit", minute:"2-digit", second:"2-digit"})}</div>`;
  $("feed").append(item);
  $("feed").scrollTop = $("feed").scrollHeight;
}

function handleEvent(event) {
  addEvent(event);
  if (stages.some(([id]) => id === event.stage)) state.stageStatus[event.stage] = event.status;
  if (event.snapshot) applySnapshot(event.snapshot);
  if (event.stage === "run" && event.status === "completed") {
    state.status = "completed";
    applySnapshot(event.result);
    state.source?.close();
    $("start-run").disabled = false;
    if(pendingMode){pendingMode=null;$('start-run').disabled=true;banner('COLLECTIONS RUNNING','Portfolio prepared; processing saved collection actions.');}
    else banner("COMPLETE", "Run saved in Supabase · review drafts and inspect step outputs");
    refreshSavedRuns();
    $("last-run").textContent = `Run ${state.currentRun.slice(0, 8)} · ${event.result.summary.draft_count} drafts`;
  } else if (event.status === "failed") {
    state.status = "failed";
    state.source?.close();
    $("start-run").disabled = false;
    banner("FAILED", `Stopped at ${event.stage}`);
    showError(event.error?.detail || event.message);
    renderDetail();
  } else if (state.status === "running") {
    banner("RUNNING", event.message);
  }
  renderFlow();
}

function clearRun() {
  outcomeFilter=null;
  pendingMode=null;
  state.source?.close();
  const selectedStage = state.queueStage;
  Object.assign(state, {invoices: [], selectedId: null, currentRun: null, status: "idle", legacyRun: false,
    highOnly: false, queueStage: selectedStage, events: [], eventIds: new Set(), stageStatus: {}, source: null});
  $("feed").innerHTML = "";
  $("event-count").textContent = "0 events";
  $("error-box").hidden = true;
  $("filter-btn").textContent = "All urgency";
  $("inspect-run").hidden = true;
  for (const id of ["metric-open", "metric-past-due", "metric-ninety", "metric-high", "metric-eligible"]) $(id).textContent = "—";
  for (const id of ["open-note", "past-due-note", "ninety-note", "eligible-note"]) $(id).textContent = "Calculated after loading data";
  $("as-of").textContent = "Load current receivables";
  $("last-run").textContent = "No active run";
  $("preventive-caption").textContent = "Prevention is scored seven days before due.";
  renderModel(null); renderQueue(); renderDetail(); renderFlow();
}

async function startRun(mode) {
  if (state.status === "running" || dueActive() || ["waiting_for_portfolio","running"].includes(agentJob?.status)) return;
  clearRun();
  pendingMode=mode;
  $("preview-caption").hidden = true;
  state.status = "running";
  $("start-run").disabled = true;
  banner("STARTING", "Starting collections analysis…");
  try {
    const run = await api("/api/runs", {method: "POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({mode})});
    agentJob={run_id:run.run_id,mode,status:"waiting_for_portfolio",progress:{}};
    state.currentRun = run.run_id;
    $("last-run").textContent = `Run ${run.run_id.slice(0, 8)} · backend execution`;
    $("inspect-run").href = `/api/runs/${run.run_id}`;
    $("inspect-run").hidden = false;
    let failures = 0;
    const source = new EventSource(run.events_url);
    state.source = source;
    source.addEventListener("connection-error", (message) => {
      if (state.source !== source) return;
      source.close(); state.status = "interrupted"; $("start-run").disabled = false;
      banner("DISCONNECTED", "Database connection interrupted; check the backend terminal.");
      showError(JSON.parse(message.data).message);
    });
    source.addEventListener("update", (message) => {
      if (state.source !== source) return;
      failures = 0;
      try {handleEvent(JSON.parse(message.data));}
      catch (error) {source.close(); state.status = "interrupted"; $("start-run").disabled = false; banner("INTERRUPTED", "Could not display a backend event"); showError(error.message);}
    });
    source.onerror = async () => {
      if (state.source !== source || state.status !== "running") return;
      failures++;
      try {
        const current = await api(`/api/runs/${run.run_id}`);
        if (state.source !== source) return;
        for (const event of current.events) if (!state.eventIds.has(event.event_id)) handleEvent(event);
        if (["completed", "failed", "cancelled", "interrupted"].includes(current.status)) {
          source.close(); state.status = current.status;
          if (current.status === "interrupted") banner("INTERRUPTED", "Previous process stopped; start a new run.");
          return;
        }
        banner("RECONNECTING", "Connection interrupted; reconnecting to the same run…");
        if (failures < 3) return; // EventSource replays using Last-Event-ID.
      } catch (error) {
        if (state.source !== source) return;
        showError(`Lost the Python connection: ${error.message}`);
      }
      source.close(); state.status = "interrupted"; $("start-run").disabled = false;
      banner("INTERRUPTED", "Check the server terminal; you can inspect the run JSON or start a new run.");
    };
  } catch (error) {
    state.status = "failed"; $("start-run").disabled = false;
    banner("FAILED", "Could not start the backend run"); showError(error.message);
  }
}

async function refreshSavedRuns() {
  try {
    const data = await api("/api/runs");
    const previous = $("saved-runs").value;
    $("saved-runs").innerHTML = `<option value="">${data.runs.length ? 'Choose a previous run…' : 'No previous runs in this browser'}</option>` + data.runs.map((run) =>
      `<option value="${escapeHTML(run.run_id)}">${escapeHTML(run.run_id.slice(0, 8))} · ${escapeHTML(run.status)} · ${escapeHTML(new Date(run.created_at).toLocaleString())}</option>`).join("");
    if (data.runs.some((run) => run.run_id === previous)) $("saved-runs").value = previous;
  } catch (error) {
    $("saved-runs").innerHTML = '<option value="">Saved history unavailable</option>';
  }
}

async function openSavedRun() {
  if (state.status === "running" || dueActive() || ["waiting_for_portfolio","running"].includes(agentJob?.status)) {toast("Let the current run finish first."); return;}
  const id = $("saved-runs").value;
  if (!id) {toast("Choose a saved run first."); return;}
  try {
    const run = await api(`/api/runs/${id}`);
    if (["queued", "running"].includes(run.status)) {toast("That run is still active. Refresh history after it finishes."); return;}
    clearRun(); $("preview-caption").hidden = true; state.currentRun = run.run_id; state.status = run.status;
    state.legacyRun = !["M3", "M4", "M5", "M6"].includes(run.result.workflow_version);
    for (const event of run.events) handleEvent(event);
    state.status = run.status;
    agentJob=null;
    if(workflowReady){try{agentJob=await api(`/api/runs/${id}/agent`);}catch(error){if(error.status!==404)showError('Run statistics unavailable: '+error.message);}}
    applySnapshot(run.result);
    banner(run.status.toUpperCase(), `Opened saved run ${id.slice(0, 8)} from Supabase`);
    $("last-run").textContent = `Saved run ${id.slice(0, 8)}`;
    $("previous-runs").open = false;
    $("inspect-run").href = `/api/runs/${id}`;
    $("inspect-run").hidden = false;
  } catch (error) {showError(error.message);}
}

$("open-saved-run").onclick = openSavedRun;
$("refresh-runs").onclick = refreshSavedRuns;
initWorkflowControls();

initInvoiceWorkspace();
$('clear-outcome-filter').onclick=()=>{outcomeFilter=null;renderQueue();renderDetail();};
for (const [id,stage] of [['stage-overdue','overdue'],['stage-preventive','pre_due']]) {
  $(id).onclick = () => {
    state.queueStage = stage; state.highOnly = false; outcomeFilter=null;
    $("filter-btn").textContent = 'All urgency';
    renderQueue(); renderDetail();
  };
}
$("filter-btn").onclick = () => {
  state.highOnly = !state.highOnly;
  $("filter-btn").textContent = state.highOnly ? 'High urgency only' : 'All urgency';
  renderQueue(); renderDetail();
};
for(const menu of document.querySelectorAll('.header-menu')) {
  menu.addEventListener('toggle',()=>{if(menu.open)for(const other of document.querySelectorAll('.header-menu'))if(other!==menu)other.open=false;});
}
document.addEventListener('click',event=>{for(const menu of document.querySelectorAll('.header-menu'))if(!menu.contains(event.target))menu.open=false;});
document.addEventListener('keydown',event=>{if(event.key==='Escape')for(const menu of document.querySelectorAll('.header-menu'))if(menu.open){menu.open=false;menu.querySelector('summary').focus();}});
$("reset-link").onclick = (event) => {
  event.preventDefault();
  if (state.status === "running" || dueActive() || ["waiting_for_portfolio","running"].includes(agentJob?.status)) {toast("Let the active run finish before resetting the page."); return;}
  clearRun(); loadPreview();
};
async function loadPreview() {
  try {
    const preview = await api('/api/portfolio');
    if (state.status === 'idle' && !state.currentRun) {
      applySnapshot(preview.portfolio); $("preview-caption").hidden = false;
      banner('READY', 'Current portfolio loaded. Run collections to prepare a collection run.');
    }
  } catch(error) {showError(error.message);}
}

async function refreshCases(repaint = true) {
  const oldCase=visitorCases.find(c=>c.invoice_id===state.selectedId);
  const composer=$('case-reply-text');const draftText=composer?.value;const focused=document.activeElement===composer;
  try {
    visitorCases = (await api('/api/cases')).cases;
    casesLoaded = true; caseLoadError = '';
  } catch(error) {caseLoadError = error.message;}
  renderQueue();
  if (repaint) renderDetail(); else {
    const newCase=visitorCases.find(c=>c.invoice_id===state.selectedId);
    if(JSON.stringify(oldCase)!==JSON.stringify(newCase)) {
      if(JSON.stringify(oldCase?.workflow?.followup?.draft)!==JSON.stringify(newCase?.workflow?.followup?.draft))renderDetail();else renderCase();
      if(draftText && state.selectedId===oldCase?.invoice_id && $('case-reply-text')){$('case-reply-text').value=draftText;if(focused)$('case-reply-text').focus();}
    }
    renderSendState();
  }
}

function saveCase(response) {
  visitorCases = [response.case, ...visitorCases.filter(c => c.id !== response.case.id)];
  renderQueue(); renderCase(); renderSendState();
}

function renderCase() {
  const panel = $('case-conversation');
  if (!panel) return;
  const row = state.invoices.find(r => r.id === state.selectedId);
  const current = visitorCases.find(c => c.invoice_id === row?.id);
  if (caseLoadError) {
    panel.innerHTML = `<div class="panel-title">Customer conversation</div><p class="explain">${escapeHTML(caseLoadError)} Run sql/007_visitor_cases.sql and sql/008_case_email.sql for this milestone.</p><button class="secondary" id="case-reload">Reload cases</button>`;
    $('case-reload').onclick = refreshCases; return;
  }
  if (!current) {
    panel.innerHTML = `<div class="panel-title">Customer conversation</div><p class="explain">${!casesLoaded ? 'Loading saved cases…' : row ? 'Run collections from the queue to prepare this invoice’s reminder and enable customer replies. This browser’s cases survive reload.' : 'Select an invoice to see its saved conversation.'}</p>
      <button class="secondary" id="case-open" ${casesLoaded && row && state.status === 'completed' && agentJob?.status !== 'running' ? '' : 'disabled'} ${state.status !== 'completed' ? 'hidden' : ''}>Enable customer replies</button>
      <p class="explain">Opening a case saves an unsent draft copy. It does not deliver email. Use Send reminder beside the draft for a real Resend send to the project test inbox.</p>`;
    $('case-open').onclick = async () => {
      const button = $('case-open'); button.disabled = true;
      try {saveCase(await api('/api/cases',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({run_id:state.currentRun,invoice_id:row.id})}));}
      catch(error) {showError(error.message); button.disabled = false;}
    };
    return;
  }
  const historyOpen=$('message-history')?.open || false;
  renderCaseExecution();
  panel.innerHTML = `<div class="panel-title">Simulate customer reply</div>
    <p class="explain">Act as the customer and test how collections responds. This form records a simulated reply; it does not send or receive an email.</p>
    <form id="case-reply-form"><label for="case-reply-text">Act as the customer · simulated reply</label><textarea id="case-reply-text" maxlength="4000" required placeholder="Example: We believe this invoice was already paid. Please check your records."></textarea>
      <button class="secondary" type="submit" ${caseActionBusy?'disabled':''}>${caseActionBusy?'Agent is processing…':'Send simulated reply'}</button></form>
    <p><span class="tag state">${escapeHTML(rowView(row).label)}</span></p>
    ${workflowExtras(current)}
    <details class="conversation-history" id="message-history" ${historyOpen?'open':''}><summary>Message history · ${current.messages.length+(current.followups||[]).length}</summary>
    ${(current.followups||[]).map(out=>`<article class="case-message followup-history"><b>Follow-up email · real Resend</b><p>${escapeHTML(out.subject)}</p><pre>${escapeHTML(out.body)}</pre><p>${escapeHTML(outboundLabel(out))}</p></article>`).join('')}
    ${current.messages.map(m => `<article class="case-message"><b>${m.channel === 'draft_preview' ? (current.outbound ? 'Reminder copy · real email status beside draft' : 'Unsent reminder copy · no email sent') : 'Simulated customer reply · entered on website'}</b><pre>${escapeHTML(m.text)}</pre>
      ${m.review ? `<p class="explain">${m.review.status === 'classified_for_review' ? `LLM classification: ${escapeHTML(m.review.classification.intent)}. The graph policy determines which actions require approval.` : m.review.status === 'pending_review' ? 'Saved before classification. Processing did not finish; manual review is required. Retrying this same message will not repeat a model call.' : 'LLM disabled, unavailable, capped or output rejected. Original text saved for manual review.'}</p>
        <details><summary>Classification evidence</summary><pre>${escapeHTML(JSON.stringify(m.review,null,2))}</pre></details>` : ''}</article>`).join('')}
    </details>
    <p class="panel-sub">Saved case snapshot ${escapeHTML(current.snapshot.as_of_date)}. Source AR stays unchanged. Classification uses the configured model; unavailable models require review.</p>`;
  if(replyDrafts.has(current.id))$('case-reply-text').value=replyDrafts.get(current.id);
  $('case-reply-text').oninput=()=>{replyDrafts.set(current.id,$('case-reply-text').value);};
  $('case-reply-form').onsubmit = async event => {
    event.preventDefault();
    const text = $('case-reply-text').value.trim();
    if (!text) return;
    if (!pendingCaseReply || pendingCaseReply.caseId !== current.id || pendingCaseReply.text !== text) {
      pendingCaseReply = {caseId:current.id,text,request_id:crypto.randomUUID()};
    }
    const pending = pendingCaseReply;
    caseActionBusy=true;
    const button = event.currentTarget.querySelector('button[type="submit"]'); button.disabled = true;
    let replyFailed=false;
    button.textContent = 'Saving and checking reply…';
    renderSendState();
    try {
      const response = await api(`/api/cases/${current.id}/replies`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({request_id:pending.request_id,text})});
      pendingCaseReply = null; replyDrafts.delete(current.id); saveCase(response);
      toast(response.recorded ? 'Reply and review status saved. Invoice balance unchanged.' : 'Saved reply reopened; no duplicate model call.');
    } catch(error) {replyFailed=true;showError(error.message);await refreshCases(false);}
    finally{caseActionBusy=false;renderCase();renderSendState();if(replyFailed && $('case-reply-text'))$('case-reply-text').value=text;}
  };
  const suggested=current.workflow?.scenario?.suggested_reply || scenarioSummaries.find(s=>s.invoice_id===current.invoice_id)?.suggested_reply;
  if(suggested){const b=document.createElement('button');b.className='secondary';b.type='button';b.textContent='Use this scenario’s suggested reply';b.onclick=()=>{$('case-reply-text').value=suggested;replyDrafts.set(current.id,suggested);$('case-reply-text').focus();};$('case-reply-form').prepend(b);}
  bindWorkflowExtras(current);
}

function outboundLabel(outbound) {
  if (!outbound) return 'No email sent. Destination: project test inbox.';
  const events = outbound.events || [];
  const issue = events.findLast(e => ['email.bounced','email.complained','email.failed','email.suppressed'].includes(e.type));
  if (issue) return `Delivery issue: ${issue.type.replace('email.','')}. Check Resend before further action.`;
  if (events.some(e => e.type === 'email.delivered')) return 'Delivered · verified Resend webhook · project test inbox.';
  if (outbound.state === 'accepted') return 'Accepted by Resend · waiting for delivery confirmation · project test inbox.';
  return 'Send outcome is unknown. Check Resend or retry the same email safely; no automatic retry.';
}

function renderSendState() {
  const button = $('send-draft');
  if (!button) return;
  const row = state.invoices.find(r => r.id === state.selectedId);
  const c = visitorCases.find(c => c.invoice_id === row?.id);
  const draftRow = c?.snapshot.invoice || row;
  const follow=c?.workflow?.followup;
  if(follow) {
    const pending=c.workflow.pending?.tool==='send_followup_email';
    const out=followupMail(c);
    button.disabled=sendBusy||!mailEnabled||!(pending||['quota_wait','unknown','review_required'].includes(follow.status));
    button.textContent=sendBusy?'Sending follow-up…':follow.status==='accepted'?'Follow-up sent':follow.status==='superseded'?'Follow-up superseded':follow.status==='declined'?'Follow-up declined':follow.status==='review_required'?'Retry reviewed follow-up':follow.status==='unknown'?'Retry same follow-up':follow.status==='quota_wait'?'Retry follow-up after quota reset':'Send follow-up';
    $('draft-email-status').textContent=outboundLabel(out);
    if($('detail-next-action') && row)$('detail-next-action').textContent=rowView(row).next;
    refreshInvoiceCaseHeader(c);
    return;
  }
  const held = c && !['awaiting_outreach','awaiting_response'].includes(c.collection_status);
  const graphBlocked=c?.workflow && !c.workflow.pending && !c.outbound && c.workflow.status !== 'quota_wait';
  button.disabled = Boolean(graphBlocked) || sendBusy || !mailEnabled || !casesLoaded || Boolean(caseLoadError) || !(c || state.status === 'completed') || !draftRow?.draft || !draftRow.eligible || draftRow.dispute || held || c?.outbound?.state === 'accepted';
  button.textContent = sendBusy ? 'Sending…' : c?.outbound?.state === 'accepted' ? 'Email sent' : c?.outbound ? 'Retry same email' : c?.workflow?.status === 'quota_wait' ? 'Retry email after quota reset' : 'Send reminder';
  if($('detail-next-action') && row)$('detail-next-action').textContent=rowView(row).next;
  $('draft-email-status').textContent = held && !c.outbound ? 'Reminder paused: review this case before further outreach.' : !mailEnabled ? 'Email is disabled or not configured on the server.' : outboundLabel(c?.outbound);
  refreshInvoiceCaseHeader(c);
}

async function sendDraft() {
  const row = state.invoices.find(r => r.id === state.selectedId);
  if (sendBusy) return;
  sendBusy = true;
  const button = $('send-draft'); button.disabled = true; button.textContent = 'Sending…';
  try {
    let c = visitorCases.find(c => c.invoice_id === row.id);
    if (!c) {
      const opened = await api('/api/cases',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({run_id:state.currentRun,invoice_id:row.id})});
      c = opened.case;
      visitorCases = [c,...visitorCases.filter(x => x.id !== c.id)];
      if (!opened.recorded) {renderDetail(); toast('Existing case restored. Review its displayed draft, then click Send reminder.'); return;}
    }
    const follow=Boolean(c.workflow?.followup);
    const response = await api(`/api/cases/${c.id}/${follow?'followup-email':'send-email'}`,{method:'POST'});
    saveCase(response); renderDetail();
    toast(outboundLabel(followupMail(response.case)||response.case.outbound));
  } catch(error) {
    showError(error.message); await refreshCases(false);
  } finally {sendBusy = false; renderSendState();}
}


clearRun();
api("/api/health").then(async (health) => {
  publicMode = Boolean(health.public_demo?.enabled);
  workflowReady=Boolean(health.workflow?.ready);
  await initFollowups(health);
  $('demo-access-note').textContent = publicMode
    ? (health.public_demo.daily_run_limit_enabled === false
      ? 'Public demo · no daily Start limit. Model and real email allowances remain bounded; templates remain available when model quota is used.'
      : 'Public demo · daily Start limits still active. Apply sql/011_unlimited_demo_starts.sql to remove them. Model and email allowances remain bounded.')
    : 'Local learning mode · keep this instance private.';
  const language = health.language;
  mailEnabled = Boolean(health.email?.ready);
  $("backend-label").textContent = language ? (language.configuration_error ? "Supabase · LLM configuration blocked" : language.enabled ? (language.key_configured ? `Supabase · ${language.provider} · ${language.model}` : "Supabase · API key missing") : "Supabase · templates only") : "Supabase + Python connected";
  const preview = await api('/api/portfolio');
  if (state.status === 'idle' && !state.currentRun) {applySnapshot(preview.portfolio); $("preview-caption").hidden = false;}
  $("start-run").disabled = false;
  banner("READY", "Current portfolio loaded. Run collections to prepare and save a collection run.");
  refreshSavedRuns();
  await refreshCases();
  if(workflowReady){
    scenarioSummaries=(await api('/api/scenarios')).scenarios;
    agentJob=(await api('/api/agent-jobs')).job;
    $('clear-outcome-filter').hidden=!outcomeFilter;
  renderWorkflowSummary();renderCaseExecution();
  }
  renderFollowupControls();
  $('start-run').disabled=dueActive()||['waiting_for_portfolio','running'].includes(agentJob?.status);
}).catch((error) => {
  $("backend-label").textContent = "Backend unavailable";
  banner("OFFLINE", "Check Supabase setup and the FastAPI server");
  showError(`${error.message}. See docs/MILESTONE_6.md for cloud/SQL006 setup; docs/MILESTONE_5.md for email and docs/MILESTONE_2.md for the database.`);
});
