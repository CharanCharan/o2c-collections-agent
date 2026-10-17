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
  highOnly: false, queueStage: "all", events: [], eventIds: new Set(), stageStatus: {}, source: null, approvalId: null,
};
let mailEnabled = false;
let publicMode = false;
let ownerLoggedIn = false;
let ownerRecipient = "";
let emailState = null;
let emailRun = null;
let emailRefreshBusy = false;
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
  const token = document.getElementById('email-owner-token')?.value || '';
  const headers = {...(token ? {'X-Collections-Owner':token} : {}), ...(options.headers || {})};
  const response = await fetch(path, {cache: "no-store", ...options, headers});
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || `Request failed (${response.status})`);
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
  $("filter-btn").disabled = state.queueStage === "pre_due";
  const rows = state.invoices.filter(row => (!state.highOnly || (row.level === 'high' && row.eligible)) &&
    (state.queueStage === 'all' || (state.queueStage === 'pre_due' ? row.lifecycle === 'pre_due' : row.days > 0)));
  if (rows.length && !rows.some(row => row.id === state.selectedId)) state.selectedId = rows[0].id;
  $("queue-sub").textContent = `${rows.length} invoices shown · recovery and prevention ranked separately`;
  $("queue").innerHTML = rows.length ? rows.map((row) => `
    <tr tabindex="0" data-id="${escapeHTML(row.id)}" aria-label="Inspect ${escapeHTML(row.customer)}"
        class="${row.id === state.selectedId ? "selected" : ""}">
      <td><div class="cust">${escapeHTML(row.customer)}</div><div class="subline">${escapeHTML(row.id)} · ${escapeHTML(row.segment)} · ${escapeHTML(stageLabel(row))}</div></td>
      <td class="amount">${money(row.amount)}</td>
      <td><div>${dateLabel(row.due)}</div><div class="subline">${escapeHTML(timingLabel(row))}</div></td>
      <td><span class="tag ${row.score === null ? "state" : row.level}">${row.score === null ? (row.days === 0 ? "Not overdue" : "Awaiting rules") : `${row.score}/100 · ${row.level}`}</span></td>
      <td>${row.prediction?.status === 'scored' ? `<strong>${(100 * probability(row.prediction)).toFixed(1)}%</strong><div class="subline">${isPreDue(row.prediction) ? "Becomes overdue" : "Unpaid in 30 days"}</div>` : '<span class="subline">No matching prediction</span>'}</td>
      <td><span class="tag ${row.dispute ? "warn" : row.contacted ? "done" : "state"}">${escapeHTML(row.action)}</span></td>
    </tr>`).join("") : '<tr><td colspan="6" class="empty-state">Start a run to load invoices, or change the queue filter.</td></tr>';
  $("queue").querySelectorAll("tr[data-id]").forEach((row) => {
    const select = () => {state.selectedId = row.dataset.id; renderQueue(); renderDetail();};
    row.addEventListener("click", select);
    row.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {event.preventDefault(); select();}
    });
  });
}

function renderDetail() {
  const row = state.invoices.find((r) => r.id === state.selectedId);
  if (!row) {
    $("detail").innerHTML = '<div class="panel-title">Invoice detail</div><p class="explain">Start a run, then select an invoice to inspect its data, policy score and draft.</p>';
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
  const canApprove = state.status === "completed" && row.eligible && row.draft && !row.contacted;
  $("detail").innerHTML = `
    <div class="detail-top"><div><div class="detail-name">${escapeHTML(row.customer)}</div><div class="detail-id">${escapeHTML(row.id)} · ${escapeHTML(row.segment)}</div></div>
      <span class="tag ${row.score === null ? "state" : row.level}">${row.score ?? "—"}/100</span></div>
    <div class="detail-grid">
      <div class="detail-metric"><label>Open balance</label><strong>${money(row.amount)}</strong></div>
      <div class="detail-metric"><label>Timing</label><strong>${escapeHTML(timingLabel(row))}</strong></div>
      <div class="detail-metric"><label>Due date</label><strong>${dateLabel(row.due)}</strong></div>
      <div class="detail-metric"><label>Suggested action</label><strong>${escapeHTML(row.action)}</strong></div>
    </div>
    <div class="explain"><b>Why this action?</b><ul>${row.reasons.length ? row.reasons.map((reason) => `<li>${escapeHTML(reason)}</li>`).join("") : "<li>Waiting for policy assessment.</li>"}</ul>
      <span>Rule score measures urgency. It is not a predicted probability.</span></div>
    ${mlDetails}
    <div class="draft"><div class="draft-head">Reminder <span>${row.draft ? (row.draft.generation_mode === "llm_assisted_validated_facts" ? "LLM · REVIEW REQUIRED" : row.draft.generation_mode === "template_fallback_no_llm_approval" ? "FALLBACK TEMPLATE · REVIEW" : "TEMPLATE · NO LLM") : "NO DRAFT"}</span></div>
      ${row.draft ? `<div class="draft-subject">${escapeHTML(row.draft.subject)}</div><pre class="draft-body">${escapeHTML(row.draft.body)}</pre>` : `<div class="draft-body">${row.dispute ? "Reminders paused for an active dispute." : row.days === 0 ? "Pre-due risk is for preventive review. Reminder drafting/approval currently remains in the overdue workflow." : "Drafts are prepared for eligible invoices with urgency scores of at least 35."}</div>`}
    </div>
    ${row.draft_audit ? `<details class="explain"><summary>Draft validation and tool evidence</summary><pre>${escapeHTML(JSON.stringify(row.draft_audit, null, 2))}</pre></details>` : ''}
    <div class="detail-actions"><button class="secondary" id="record-btn" ${canApprove ? "" : "disabled"}>${row.contacted ? "Dry run already recorded" : "Approve & record dry run"}</button></div>
    <p class="panel-sub">This saves an approval in Supabase. Use the separate controlled email panel to send to your configured test inbox.</p>
    <div class="explain"><b>Review a synthetic reply example</b><p>No email was received. This only tests classification; payment and dispute status stay unchanged.</p>
      <select id="reply-example"><option value="promise">Promise to pay</option><option value="paid">Customer claims paid</option><option value="dispute">Dispute</option><option value="documents">Request documents</option><option value="injection">Untrusted instructions</option></select>
      <button class="secondary" id="classify-reply" ${state.status === 'completed' ? '' : 'disabled'}>Classify example</button>
      <pre id="reply-output">${escapeHTML(JSON.stringify(row.reply_reviews || {}, null, 2))}</pre></div>`;
  $("classify-reply").onclick = async () => {
    const button = $("classify-reply"); button.disabled = true;
    try {
      const response = await api(`/api/runs/${state.currentRun}/invoices/${encodeURIComponent(row.id)}/classify-example`, {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({example_id: $("reply-example").value})});
      applySnapshot(response.run.result);
      for (const event of response.run.events) if (!state.eventIds.has(event.event_id)) addEvent(event);
      toast(response.recorded ? 'Example review saved; no payment status changed.' : 'Saved review reopened; no duplicate call.');
    } catch (error) {showError(error.message); button.disabled = false;}
  };
  $("record-btn").onclick = () => {state.approvalId = row.id; $("modal").classList.add("show");};
  renderMail();
}

function renderFlow() {
  let completed = 0;
  const visibleStages = state.legacyRun ? stages.filter(([id]) => id !== "predict") : stages;
  $("flow").innerHTML = visibleStages.map(([id, name, desc], i) => {
    const status = state.stageStatus[id];
    if (status === "completed") completed++;
    const cls = status === "completed" ? "complete" : status === "started" ? "active" : status === "failed" ? "failed" : "";
    const symbol = status === "completed" ? "✓" : status === "failed" ? "!" : i + 1;
    return `<div class="step ${cls}"><div class="step-icon">${symbol}</div><div><div class="step-name">${name}</div><div class="step-desc">${desc}</div></div><div class="step-meta">${status || "Waiting"}</div></div>`;
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
    banner("COMPLETE", "Run saved in Supabase · review drafts and inspect step outputs");
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
  emailState = null; emailRun = null;
  if ($("email-activity")) $("email-activity").textContent = "Complete a run to inspect email activity.";
  state.source?.close();
  Object.assign(state, {invoices: [], selectedId: null, currentRun: null, status: "idle", legacyRun: false,
    highOnly: false, queueStage: "all", events: [], eventIds: new Set(), stageStatus: {}, source: null, approvalId: null});
  $("modal").classList.remove("show");
  $("feed").innerHTML = "";
  $("event-count").textContent = "0 events";
  $("error-box").hidden = true;
  $("filter-btn").textContent = "All invoices ▾";
  $("inspect-run").hidden = true;
  for (const id of ["metric-open", "metric-past-due", "metric-ninety", "metric-high", "metric-eligible"]) $(id).textContent = "—";
  for (const id of ["open-note", "past-due-note", "ninety-note", "eligible-note"]) $(id).textContent = "Calculated after loading data";
  $("as-of").textContent = "Start to load the demo snapshot";
  $("last-run").textContent = "No active run";
  $("queue-stage").value = "all"; $("preventive-caption").textContent = "Start to inspect the preventive review queue.";
  renderModel(null); renderQueue(); renderDetail(); renderFlow();
}

async function startRun() {
  if (state.status === "running") return;
  clearRun();
  state.status = "running";
  $("start-run").disabled = true;
  banner("STARTING", "Requesting a Python collections run…");
  try {
    const run = await api("/api/runs", {method: "POST"});
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
    $("saved-runs").innerHTML = '<option value="">Choose a saved run…</option>' + data.runs.map((run) =>
      `<option value="${escapeHTML(run.run_id)}">${escapeHTML(run.run_id.slice(0, 8))} · ${escapeHTML(run.status)} · ${escapeHTML(new Date(run.created_at).toLocaleString())}</option>`).join("");
    if (data.runs.some((run) => run.run_id === previous)) $("saved-runs").value = previous;
  } catch (error) {
    $("saved-runs").innerHTML = '<option value="">Saved history unavailable</option>';
  }
}

async function openSavedRun() {
  if (state.status === "running") {toast("Let the current run finish first."); return;}
  const id = $("saved-runs").value;
  if (!id) {toast("Choose a saved run first."); return;}
  try {
    const run = await api(`/api/runs/${id}`);
    if (["queued", "running"].includes(run.status)) {toast("That run is still active. Refresh history after it finishes."); return;}
    clearRun(); state.currentRun = run.run_id; state.status = run.status;
    state.legacyRun = !["M3", "M4", "M5", "M6"].includes(run.result.workflow_version);
    for (const event of run.events) handleEvent(event);
    state.status = run.status;
    applySnapshot(run.result);
    banner(run.status.toUpperCase(), `Opened saved run ${id.slice(0, 8)} from Supabase`);
    $("last-run").textContent = `Saved run ${id.slice(0, 8)}`;
    $("inspect-run").href = `/api/runs/${id}`;
    $("inspect-run").hidden = false;
  } catch (error) {showError(error.message);}
}

$("open-saved-run").onclick = openSavedRun;
$("refresh-runs").onclick = refreshSavedRuns;
$("start-run").onclick = startRun;
$("queue-stage").onchange = () => {state.queueStage = $("queue-stage").value; state.highOnly = false; $("filter-btn").textContent = "All urgency levels ▾"; renderQueue(); renderDetail();};
$("filter-btn").onclick = () => {state.highOnly = !state.highOnly; $("filter-btn").textContent = state.highOnly ? "High urgency ×" : "All invoices ▾"; renderQueue();};
$("reset-link").onclick = (event) => {
  event.preventDefault();
  if (state.status === "running") {toast("Let the active run finish before resetting the page."); return;}
  clearRun(); banner("READY", "Start a run to process the demo dataset");
};
$("cancel-send").onclick = () => $("modal").classList.remove("show");
$("modal").onclick = (event) => {if (event.target.id === "modal") $("modal").classList.remove("show");};
document.addEventListener("keydown", (event) => {if (event.key === "Escape") $("modal").classList.remove("show");});
$("confirm-send").onclick = async () => {
  $("confirm-send").disabled = true;
  try {
    const response = await api(`/api/runs/${state.currentRun}/invoices/${encodeURIComponent(state.approvalId)}/dry-run`, {method:"POST"});
    applySnapshot(response.run.result);
    for (const event of response.run.events) addEvent(event);
    $("modal").classList.remove("show");
    toast(response.recorded ? "Approval recorded by Python. No email was sent." : response.message);
  } catch (error) {showError(error.message);}
  finally {$("confirm-send").disabled = false;}
};

function applyEmailActivity(response) {
  emailState = response.mail; emailRun = response.run.run_id;
  if (state.currentRun !== emailRun) return;
  for (const event of response.run.events) if (!state.eventIds.has(event.event_id)) addEvent(event);
  renderMail();
}

async function refreshEmail() {
  if (!state.currentRun || state.status !== 'completed' || emailRefreshBusy || (publicMode && !ownerLoggedIn)) return;
  emailRefreshBusy = true;
  const id = state.currentRun;
  try {
    const response = await api(`/api/runs/${id}/email`);
    if (state.currentRun === id && (emailRun !== id || JSON.stringify(emailState) !== JSON.stringify(response.mail))) applyEmailActivity(response);
  } catch (error) { if (mailEnabled) $("email-activity").textContent = error.message; }
  finally { emailRefreshBusy = false; }
}

function renderMail() {
  const panel = $("email-activity");
  if (publicMode && !ownerLoggedIn) {panel.textContent = "Private email activity is available to the project owner. You can inspect this browser’s collection runs above."; return;}
  if (!state.currentRun || state.status !== 'completed') {panel.textContent = 'Complete a run to inspect email activity.'; return;}
  const row = state.invoices.find(r => r.id === state.selectedId);
  if (!row) return;
  const saved = emailRun === state.currentRun ? emailState : null;
  const messages = (saved?.messages || []).filter(m => m.invoice_id === row.id);
  const mail = messages[0];
  const replies = (saved?.replies || []).filter(r => messages.some(m => m.id === r.mail_id));
  const followups = (saved?.followups || []).filter(f => replies.some(r => r.id === f.reply_id));
  const events = (saved?.delivery_events || []).filter(e => messages.some(m => m.id === e.mail_id));
  panel.innerHTML = `<div class="panel-title">Controlled email · ${escapeHTML(row.id)}</div>
    <p class="explain">${mail ? `Resend acceptance: <b>${escapeHTML(mail.state)}</b>. ${mail.state === 'accepted' ? 'Acceptance does not confirm delivery.' : 'Inspect Resend before manually retrying the same intent.'}` : 'No email send intent recorded.'}</p>
    <button class="secondary" id="live-email-send" ${mailEnabled && ownerRecipient && row.eligible && row.draft && mail?.state !== 'accepted' ? '' : 'disabled'}>${mail ? 'Retry same approved email' : 'Review & send test email'}</button>
    <button class="secondary" id="email-refresh">Refresh email activity</button>
    <p class="explain">${ownerRecipient ? `Test inbox: ${escapeHTML(ownerRecipient)}` : 'Unlock owner access above to send.'} All messages are labelled synthetic demos.</p>
    <details class="explain"><summary>Send and verified delivery evidence</summary><pre>${escapeHTML(JSON.stringify({messages,delivery_events:events},null,2))}</pre></details>
    ${replies.map(reply => `<div class="draft"><b>Received reply · ${escapeHTML(reply.review.status)}</b><p class="explain">Thread verified: ${reply.review.thread_verified}. Human review required. No payment state changed.</p><pre>${escapeHTML(reply.review.text)}</pre>
      <details><summary>Classification and receipt evidence</summary><pre>${escapeHTML(JSON.stringify(reply.review,null,2))}</pre></details>
      ${reply.resolution ? `<p>Review saved: ${escapeHTML(reply.resolution.intent)}</p>` : `<form class="reply-resolution" data-reply="${escapeHTML(reply.id)}">
        <label>Reviewed intent <select name="intent">${['promise_to_pay','payment_claim','dispute','request_info','other'].map(intent => `<option ${intent === (reply.review.classification?.intent || 'other') ? 'selected' : ''}>${intent}</option>`).join('')}</select></label>
        <p><label>Promise date (literal YYYY-MM-DD) <input name="promise_date" value="${escapeHTML(reply.review.classification?.promise_date || '')}"></label></p>
        <p><label>Promise amount (optional exact two decimals) <input name="promise_amount" value="${escapeHTML(reply.review.classification?.promise_amount || '')}"></label></p>
        <p><label>Exact supporting quote <textarea name="evidence_quote" maxlength="500">${escapeHTML(reply.review.classification?.evidence_quote || '')}</textarea></label></p>
        <button class="secondary" ${ownerRecipient ? '' : 'disabled'}>Confirm review & schedule follow-up task</button></form>`}</div>`).join('')}
    <p class="explain">Follow-ups are saved AR work tasks, not automatically sent emails. Promise checks fall on the day after the promised date; other reviews on tomorrow's UTC date.</p>
    <pre>${escapeHTML(JSON.stringify(followups,null,2))}</pre>`;
  $("email-refresh").onclick = refreshEmail;
  $("live-email-send").onclick = async () => {
    if (!window.confirm(`I reviewed ${row.id}'s displayed draft. Send this synthetic demo only to ${ownerRecipient}?`)) return;
    $("live-email-send").disabled = true;
    try {
      applyEmailActivity(await api(`/api/runs/${state.currentRun}/invoices/${encodeURIComponent(row.id)}/send-email`, {
        method:'POST',headers:{'Content-Type':'application/json','X-Collections-Owner':$("email-owner-token").value},body:JSON.stringify({confirm_reviewed:true})}));
      toast('Email outcome saved. Inspect acceptance and delivery evidence.');
    } catch(error) {showError(error.message); renderMail();}
  };
  for (const form of panel.querySelectorAll('.reply-resolution')) form.onsubmit = async event => {
    event.preventDefault();
    if (!window.confirm('Confirm human review and save one follow-up task? No invoice payment state will change.')) return;
    const body = {intent:form.elements.intent.value,promise_date:form.elements.promise_date.value || null,
      promise_amount:form.elements.promise_amount.value || null,evidence_quote:form.elements.evidence_quote.value};
    form.querySelector('button').disabled = true;
    try {applyEmailActivity(await api(`/api/runs/${state.currentRun}/replies/${form.dataset.reply}/resolve`, {
      method:'POST',headers:{'Content-Type':'application/json','X-Collections-Owner':$("email-owner-token").value},body:JSON.stringify(body)}));}
    catch(error) {showError(error.message); form.querySelector('button').disabled = false;}
  };
}
$("email-unlock").onclick = async () => {
  try {
    if (publicMode) {
      await api('/api/operator/login',{method:'POST'});
      ownerLoggedIn = true;
      await refreshSavedRuns();
      if (!mailEnabled) {$("email-target").textContent = 'Owner history unlocked. Live email is disabled.'; renderMail(); return;}
    }
    const config = await api('/api/email/owner-config' ,{headers:{'X-Collections-Owner':$("email-owner-token").value}});
    ownerRecipient = config.recipient; $("email-target").textContent = `Only ${config.recipient} can receive this demo. Sender: ${config.sender}`;
    renderMail(); await refreshEmail();
  } catch(error) {ownerRecipient = ''; $("email-target").textContent = error.message; renderMail();}
};
$("email-logout").onclick = async () => {
  $("email-owner-token").value = ''; ownerRecipient = ''; ownerLoggedIn = false;
  if (publicMode) await api('/api/operator/logout',{method:'POST'});
  clearRun(); await refreshSavedRuns();
  $("email-target").textContent = 'Owner access closed.';
};
$("email-owner-token").oninput = () => {ownerRecipient = ''; $("email-target").textContent = ''; renderMail();};
setInterval(refreshEmail,5000);

clearRun();
api("/api/health").then((health) => {
  publicMode = Boolean(health.public_demo?.enabled);
  $("demo-access-note").textContent = publicMode ? 'Public demo · synthetic invoices · this browser gets 3 runs and 8 LLM attempts per UTC day. Shared daily caps also apply; templates remain available when LLM quota is used.' : 'Local learning mode · keep this instance private.';
  const language = health.language;
  mailEnabled = Boolean(health.email?.ready);
  $("email-mode").textContent = mailEnabled ? "Live email configured. Owner approval sends only to the server-configured test inbox. Ten reservations per UTC day." : (health.email?.configuration_error || "Live email disabled. See M5 setup.");
  $("backend-label").textContent = language ? (language.configuration_error ? "Supabase · LLM configuration blocked" : language.enabled ? (language.key_configured ? `Supabase · ${language.provider} · ${language.model}` : "Supabase · API key missing") : "Supabase · templates only") : "Supabase + Python connected";
  $("start-run").disabled = false;
  banner("READY", "Start a run to process the demo dataset");
  refreshSavedRuns();
}).catch((error) => {
  $("backend-label").textContent = "Backend unavailable";
  banner("OFFLINE", "Check Supabase setup and the FastAPI server");
  showError(`${error.message}. See docs/MILESTONE_6.md for cloud/SQL006 setup; docs/MILESTONE_5.md for email and docs/MILESTONE_2.md for the database.`);
});
