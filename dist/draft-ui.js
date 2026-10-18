/* Explicit, saved AI draft generation. Opening the editor never calls a model. */
'use strict';
const aiDraftEditors = new Map();
const aiDraftBusy = new Set();
let aiDraftReady = false;
let aiDraftConfigured = false;

function caseDraftSignature(c) {
  return JSON.stringify([c?.snapshot.invoice.draft, c?.snapshot.invoice.draft_audit, c?.workflow?.followup?.draft]);
}

function initAIDrafting(health) {
  aiDraftReady = Boolean(health.ai_draft?.ready);
  aiDraftConfigured = Boolean(health.language?.enabled && health.language?.key_configured && !health.language?.configuration_error);
}

function aiDraftEditor(id) {
  if (!aiDraftEditors.has(id)) aiDraftEditors.set(id, {open:false, text:'', message:'', requestId:null});
  return aiDraftEditors.get(id);
}

function aiDraftBlockReason(row, c) {
  if (!aiDraftReady) return 'Draft with AI needs database migration SQL015.';
  if (!aiDraftConfigured) return 'Enable and configure the LLM on the server to generate an AI draft.';
  if (!casesLoaded || caseLoadError) return 'Wait for saved cases to load.';
  if (!c && state.status !== 'completed') return 'Run collections first to prepare this reminder.';
  const saved = c?.snapshot.invoice || row, w = c?.workflow;
  if (!saved?.draft || !saved.eligible || saved.dispute) return 'AI drafting is available for eligible overdue reminders.';
  if (c?.outbound) return 'An email send is already recorded. Its content stays unchanged.';
  if (c && c.collection_status !== 'awaiting_outreach') return 'Review the customer response or case hold before further outreach.';
  if (c?.messages.some(m => m.channel === 'simulated_customer_reply')) return 'This case has a customer reply; its existing reminder stays unchanged.';
  if (w?.processing || w?.followup || (w && !['awaiting_approval','ready_for_outreach','quota_wait'].includes(w.status))) return 'Wait for invoice processing or review its current action.';
  if (w?.pending && w.pending.tool !== 'send_email') return 'Review the current case action first.';
  if (c?.draft_generation?.status === 'reserved' && Date.now() - Date.parse(c.draft_generation.created_at) < 300000) return 'A draft request is in progress. Refresh to check its saved result.';
  if (aiDraftBusy.has(row.id) || sendBusy) return 'Wait for the current draft or send action to finish.';
  return '';
}

function aiDraftPanel(row) {
  const editor = aiDraftEditor(row.id);
  const saved = visitorCases.find(c => c.invoice_id === row.id)?.draft_generation;
  return `<section class="ai-draft-editor" id="ai-draft-editor" ${editor.open?'':'hidden'} aria-label="Customize reminder with AI">
    <label for="ai-draft-instructions">Customize the reminder <span>(optional)</span></label>
    <textarea id="ai-draft-instructions" maxlength="600" rows="3" placeholder="Make it warmer and shorter. Ask for an expected payment date." aria-describedby="ai-draft-help">${escapeHTML(editor.text)}</textarea>
    <p id="ai-draft-help">Tone, brevity and wording only. Invoice facts stay fixed. Generate saves a draft; Send reminder is separate. Existing model limits apply.</p>
    <div class="ai-draft-actions"><button class="primary" id="generate-ai-draft">Generate draft</button><button class="secondary" id="cancel-ai-draft">Cancel</button></div>
    </section><p class="explain ai-draft-result" id="ai-draft-result" role="status" aria-live="polite">${escapeHTML(editor.message || saved?.reason || '')}</p>`;
}

function bindAIDrafting(row) {
  $('ai-draft-toggle').onclick = () => {
    const editor = aiDraftEditor(row.id); editor.open = !editor.open;
    $('ai-draft-editor').hidden = !editor.open;
    $('ai-draft-toggle').setAttribute('aria-expanded', String(editor.open));
    if (editor.open) $('ai-draft-instructions').focus();
  };
  $('ai-draft-instructions').oninput = event => {
    const editor = aiDraftEditor(row.id);
    editor.text = event.target.value; editor.requestId = null;
  };
  $('cancel-ai-draft').onclick = () => {
    aiDraftEditor(row.id).open = false; $('ai-draft-editor').hidden = true;
    $('ai-draft-toggle').setAttribute('aria-expanded','false'); $('ai-draft-toggle').focus();
  };
  $('generate-ai-draft').onclick = generateAIDraft;
  renderAIDraftState();
}

function renderAIDraftState() {
  const button = $('ai-draft-toggle'); if (!button) return;
  const row = state.invoices.find(r => r.id === state.selectedId); if (!row) return;
  const c = visitorCases.find(x => x.invoice_id === row.id);
  const reason = aiDraftBlockReason(row,c), busy = aiDraftBusy.has(row.id);
  button.disabled = Boolean(reason);
  button.title = reason || 'Generate a new AI reminder draft for review';
  button.textContent = busy ? 'Drafting…' : (c?.snapshot.invoice || row).draft?.generation_mode === 'llm_assisted_validated_facts' ? 'Redraft with AI' : 'Draft with AI';
  button.setAttribute('aria-expanded',String(aiDraftEditor(row.id).open));
  if ($('generate-ai-draft')) {
    $('generate-ai-draft').disabled = Boolean(reason);
    $('generate-ai-draft').textContent = busy ? 'Generating…' : 'Generate draft';
    $('ai-draft-instructions').disabled = busy;
    $('cancel-ai-draft').disabled = busy;
  }
}

async function generateAIDraft() {
  const row = state.invoices.find(r => r.id === state.selectedId); if (!row) return;
  let c = visitorCases.find(x => x.invoice_id === row.id);
  const reason = aiDraftBlockReason(row,c); if (reason) {toast(reason); return;}
  const editor = aiDraftEditor(row.id);
  editor.requestId ||= crypto.randomUUID();
  aiDraftBusy.add(row.id); editor.message = 'Generating a checked draft. Your current draft stays saved until generation succeeds.';
  $('ai-draft-result').textContent = editor.message; renderSendState();
  try {
    if (!c) {
      const opened = await api('/api/cases',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({run_id:state.currentRun,invoice_id:row.id})});
      c = opened.case; mergeExecutionCases([c]);
    }
    const response = await api(`/api/cases/${c.id}/draft`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({request_id:editor.requestId,instructions:editor.text})});
    mergeExecutionCases([response.case]);
    editor.message = response.generated ? 'AI draft saved. Review the updated reminder, then click Send reminder.' : `${response.reason || 'Generation did not complete.'} Existing draft kept.`;
    editor.requestId = null;
    if (response.generated) editor.open = false;
  } catch (error) {
    // Keep the request id for a safe retry after an unknown network outcome.
    if (error.status && error.status < 500) {
      editor.requestId = null;
      editor.message = `${error.message} Draft was not updated. Review the current case before trying again.`;
    } else {
      editor.message = `${error.message} Generation outcome could not be confirmed. Refresh or retry to check this request; no automatic repeat call.`;
    }
  } finally {
    aiDraftBusy.delete(row.id);
    renderQueue();
    if (state.selectedId === row.id) {renderDetail(); renderCase();}
  }
}
