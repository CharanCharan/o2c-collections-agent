/* UI only: Python produces all invoice results. This file renders them. */
"use strict";

const stages = [
  ["ingest", "Load receivables", "Read a fresh JSON snapshot"],
  ["validate", "Validate invoice data", "Check IDs, amounts, dates and history"],
  ["assess", "Assess collection urgency", "Apply documented rules; pause disputes"],
  ["prioritize", "Prioritize accounts", "Rank eligible balances by urgency"],
  ["draft", "Prepare reminder templates", "Prepare factual drafts for review"],
];
const state = {
  invoices: [], selectedId: null, currentRun: null, status: "idle",
  highOnly: false, events: [], eventIds: new Set(), stageStatus: {}, source: null, approvalId: null,
};
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
  const response = await fetch(path, {cache: "no-store", ...options});
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
  renderQueue();
  renderDetail();
}

function renderQueue() {
  const rows = state.invoices.filter((row) => !state.highOnly || (row.level === "high" && row.eligible));
  $("queue-sub").textContent = `${rows.length} invoices shown · results from this Python run`;
  $("queue").innerHTML = rows.length ? rows.map((row) => `
    <tr tabindex="0" data-id="${escapeHTML(row.id)}" aria-label="Inspect ${escapeHTML(row.customer)}"
        class="${row.id === state.selectedId ? "selected" : ""}">
      <td><div class="cust">${escapeHTML(row.customer)}</div><div class="subline">${escapeHTML(row.id)} · ${escapeHTML(row.segment)}</div></td>
      <td class="amount">${money(row.amount)}</td>
      <td><div>${dateLabel(row.due)}</div><div class="subline">${row.days} days overdue</div></td>
      <td><span class="tag ${row.score === null ? "state" : row.level}">${row.score === null ? "Awaiting rules" : `${row.score}/100 · ${row.level}`}</span></td>
      <td><span class="tag ${row.dispute ? "warn" : row.contacted ? "done" : "state"}">${escapeHTML(row.action)}</span></td>
    </tr>`).join("") : '<tr><td colspan="5" class="empty-state">Start a run to load invoices, or change the queue filter.</td></tr>';
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
  const canApprove = state.status === "completed" && row.eligible && row.draft && !row.contacted;
  $("detail").innerHTML = `
    <div class="detail-top"><div><div class="detail-name">${escapeHTML(row.customer)}</div><div class="detail-id">${escapeHTML(row.id)} · ${escapeHTML(row.segment)}</div></div>
      <span class="tag ${row.score === null ? "state" : row.level}">${row.score ?? "—"}/100</span></div>
    <div class="detail-grid">
      <div class="detail-metric"><label>Open balance</label><strong>${money(row.amount)}</strong></div>
      <div class="detail-metric"><label>Days overdue</label><strong>${row.days} days</strong></div>
      <div class="detail-metric"><label>Due date</label><strong>${dateLabel(row.due)}</strong></div>
      <div class="detail-metric"><label>Suggested action</label><strong>${escapeHTML(row.action)}</strong></div>
    </div>
    <div class="explain"><b>Why this action?</b><ul>${row.reasons.length ? row.reasons.map((reason) => `<li>${escapeHTML(reason)}</li>`).join("") : "<li>Waiting for policy assessment.</li>"}</ul>
      <span>Rule score measures urgency. It is not a predicted probability.</span></div>
    <div class="draft"><div class="draft-head">Reminder <span>${row.draft ? "TEMPLATE · REVIEW REQUIRED" : "NO DRAFT"}</span></div>
      ${row.draft ? `<div class="draft-subject">${escapeHTML(row.draft.subject)}</div><pre class="draft-body">${escapeHTML(row.draft.body)}</pre>` : `<div class="draft-body">${row.dispute ? "Reminders paused for an active dispute." : "Drafts are prepared for eligible invoices with urgency scores of at least 35."}</div>`}
    </div>
    <div class="detail-actions"><button class="secondary" id="record-btn" ${canApprove ? "" : "disabled"}>${row.contacted ? "Dry run already recorded" : "Approve & record dry run"}</button></div>
    <p class="panel-sub">This records an approval in Python memory. Email sending arrives in Milestone 5.</p>`;
  $("record-btn").onclick = () => {state.approvalId = row.id; $("modal").classList.add("show");};
}

function renderFlow() {
  let completed = 0;
  $("flow").innerHTML = stages.map(([id, name, desc], i) => {
    const status = state.stageStatus[id];
    if (status === "completed") completed++;
    const cls = status === "completed" ? "complete" : status === "started" ? "active" : status === "failed" ? "failed" : "";
    const symbol = status === "completed" ? "✓" : status === "failed" ? "!" : i + 1;
    return `<div class="step ${cls}"><div class="step-icon">${symbol}</div><div><div class="step-name">${name}</div><div class="step-desc">${desc}</div></div><div class="step-meta">${status || "Waiting"}</div></div>`;
  }).join("");
  $("progress-bar").style.width = `${completed / stages.length * 100}%`;
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
  item.innerHTML = `<div class="event-icon">${event.status === "failed" ? "!" : event.status === "started" ? "↗" : "✓"}</div>
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
    banner("COMPLETE", "Run completed · review drafts and inspect step outputs");
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
  state.source?.close();
  Object.assign(state, {invoices: [], selectedId: null, currentRun: null, status: "idle",
    highOnly: false, events: [], eventIds: new Set(), stageStatus: {}, source: null, approvalId: null});
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
  renderQueue(); renderDetail(); renderFlow();
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
        if (current.status === "completed" || current.status === "failed" || current.status === "cancelled") {source.close(); return;}
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

$("start-run").onclick = startRun;
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

clearRun();
api("/api/health").then(() => {
  $("backend-label").textContent = "Python connected";
  $("start-run").disabled = false;
  banner("READY", "Start a run to process the demo dataset");
}).catch(() => {
  $("backend-label").textContent = "Backend unavailable";
  banner("OFFLINE", "Open this page through the FastAPI server");
  showError("Start Uvicorn from the project folder and open http://localhost:8000. The old python -m http.server command serves only static files.");
});
