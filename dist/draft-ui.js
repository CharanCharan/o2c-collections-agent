/* Explicit, saved AI draft generation. Opening the editor never calls a model. */
'use strict';
const aiDraftEditors = new Map();
const aiDraftBusy = new Set();
const manualDraftEditors = new Map();
const manualDraftBusy = new Set();
let aiDraftReady = false;
let aiDraftConfigured = false;
let manualDraftReady = false;

function caseDraftSignature(c) {
  return JSON.stringify([c?.snapshot.invoice.draft, c?.snapshot.invoice.draft_audit, c?.workflow?.followup?.draft]);
}

function initAIDrafting(health) {
  aiDraftReady = Boolean(health.ai_draft?.ready);
  aiDraftConfigured = Boolean(health.language?.enabled && health.language?.key_configured && !health.language?.configuration_error);
  manualDraftReady = Boolean(health.draft_edit?.ready);
}

function aiDraftEditor(id) {
  if (!aiDraftEditors.has(id)) aiDraftEditors.set(id, {open:false, text:'', message:'', requestId:null});
  return aiDraftEditors.get(id);
}

function savedDraftBlockReason(row, c) {
  if (!casesLoaded || caseLoadError) return 'Wait for saved cases to load.';
  if (!c && state.status !== 'completed') return 'Run collections first to prepare this reminder.';
  const saved = c?.snapshot.invoice || row, w = c?.workflow;
  if (!saved?.draft || !saved.eligible || saved.dispute) return 'Draft changes are available for eligible overdue reminders.';
  if (c?.outbound) return 'An email send is already recorded. Its content stays unchanged.';
  if (c && c.collection_status !== 'awaiting_outreach') return 'Review the customer response or case hold before further outreach.';
  if (c?.messages.some(m => m.channel === 'simulated_customer_reply')) return 'This case has a customer reply; its existing reminder stays unchanged.';
  if (w?.processing || w?.followup || (w && !['awaiting_approval','ready_for_outreach','quota_wait'].includes(w.status))) return 'Wait for invoice processing or review its current action.';
  if (w?.pending && w.pending.tool !== 'send_email') return 'Review the current case action first.';
  if (c?.draft_generation?.status === 'reserved' && Date.now() - Date.parse(c.draft_generation.created_at) < 300000) return 'A draft request is in progress. Refresh to check its saved result.';
  if (aiDraftBusy.has(row.id) || manualDraftBusy.has(row.id) || sendBusy) return 'Wait for the current draft or send action to finish.';
  return '';
}

function aiDraftBlockReason(row,c) {
  if (!aiDraftReady) return 'Draft with AI needs database migration SQL015.';
  if (!aiDraftConfigured) return 'Enable and configure the LLM on the server to generate an AI draft.';
  if (manualDraftEditors.get(row.id)?.open) return 'Save or cancel your manual edits before asking AI to revise the saved draft.';
  return savedDraftBlockReason(row,c);
}

function aiDraftPanel(row) {
  const editor = aiDraftEditor(row.id);
  const saved = visitorCases.find(c => c.invoice_id === row.id)?.draft_generation;
  return `<section class="ai-draft-editor" id="ai-draft-editor" ${editor.open?'':'hidden'} aria-label="Customize reminder with AI">
    <label for="ai-draft-instructions">Customize the reminder <span>(optional)</span></label>
    <textarea id="ai-draft-instructions" maxlength="600" rows="3" placeholder="Mention our earlier conversation with Priya and ask for the purchase-order reference. Make it warmer." aria-describedby="ai-draft-help">${escapeHTML(editor.text)}</textarea>
    <p id="ai-draft-help">AI revises the current saved draft using your requested changes and additional context. Invoice facts stay fixed. Review added context before sending. Existing model limits apply.</p>
    <div class="ai-draft-actions"><button class="primary" id="generate-ai-draft">Generate draft</button><button class="secondary" id="cancel-ai-draft">Cancel</button></div>
    </section><p class="explain ai-draft-result" id="ai-draft-result" role="status" aria-live="polite">${escapeHTML(editor.message || (saved?.audit?.tool!=='edit_reminder'?saved?.reason:'') || '')}</p>`;
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
  button.textContent = busy ? 'Drafting…' : ['llm_assisted_validated_facts','human_edited'].includes((c?.snapshot.invoice || row).draft?.generation_mode) ? 'Redraft with AI' : 'Draft with AI';
  button.setAttribute('aria-expanded',String(aiDraftEditor(row.id).open));
  if ($('generate-ai-draft')) {
    $('generate-ai-draft').disabled = Boolean(reason);
    $('generate-ai-draft').textContent = busy ? 'Generating…' : 'Generate draft';
    $('ai-draft-instructions').disabled = busy;
    $('cancel-ai-draft').disabled = busy;
  }
  renderManualDraftState(row,c);
}

function draftModeLabel(draft) {
  if (!draft) return 'NO DRAFT';
  if (draft.generation_mode==='human_edited') return 'HUMAN EDITED · REVIEW';
  if (draft.generation_mode==='llm_assisted_validated_facts') return draft.context_review_required?'AI REVISED · REVIEW CONTEXT':'LLM · FACTS CHECKED';
  return draft.generation_mode==='template_fallback_no_llm_approval'?'FALLBACK TEMPLATE · REVIEW':'TEMPLATE · NO LLM';
}

function manualDraftPanel(row) {
  const e=manualDraftEditors.get(row.id);
  const saved=visitorCases.find(c=>c.invoice_id===row.id)?.draft_generation;
  return `<section class="ai-draft-editor" id="manual-draft-editor" ${e?.open?'':'hidden'} aria-label="Edit saved reminder">
    <label for="manual-draft-subject">Subject</label><input id="manual-draft-subject" maxlength="200" value="${escapeHTML(e?.subject || '')}">
    <label for="manual-draft-body">Message</label><textarea id="manual-draft-body" maxlength="4000" rows="12">${escapeHTML(e?.body || '')}</textarea>
    <p>Keep the invoice facts sentence unchanged and the invoice ID in the subject. Sender and recipient stay fixed. Saving makes no LLM call and sends no email.</p>
    <div class="ai-draft-actions"><button class="primary" id="save-manual-draft">Save changes</button><button class="secondary" id="cancel-manual-draft">Cancel</button></div>
    </section><p class="explain" id="manual-draft-result" role="status" aria-live="polite">${escapeHTML(e?.message || (saved?.audit?.tool==='edit_reminder'?saved.reason:'') || '')}</p>`;
}

function bindManualDraft(row) {
  $('edit-draft').onclick=()=>{
    const c=visitorCases.find(x=>x.invoice_id===row.id),draft=(c?.snapshot.invoice||row).draft;
    aiDraftEditor(row.id).open=false;
    aiDraftEditor(row.id).message='';
    manualDraftEditors.set(row.id,{open:true,subject:draft.subject,body:draft.body,expected:JSON.parse(JSON.stringify(draft)),requestId:null,message:''});
    renderDetail();$('manual-draft-subject').focus();
  };
  for(const [id,key] of [['manual-draft-subject','subject'],['manual-draft-body','body']])$(id).oninput=event=>{
    const e=manualDraftEditors.get(row.id);e[key]=event.target.value;e.requestId=null;
  };
  $('cancel-manual-draft').onclick=()=>{manualDraftEditors.get(row.id).open=false;renderDetail();$('edit-draft').focus();};
  $('save-manual-draft').onclick=saveManualDraft;
}

function renderManualDraftState(row,c) {
  const button=$('edit-draft');if(!button)return;
  const reason=!manualDraftReady?'Apply SQL017 to enable Edit draft.':savedDraftBlockReason(row,c);
  const e=manualDraftEditors.get(row.id),busy=manualDraftBusy.has(row.id);
  button.disabled=Boolean(reason)||Boolean(e?.open);button.title=reason || 'Edit the subject and message without a model call';
  button.setAttribute('aria-expanded',String(Boolean(e?.open)));
  if($('save-manual-draft')){
    $('save-manual-draft').disabled=Boolean(reason);$('save-manual-draft').textContent=busy?'Saving…':'Save changes';
    $('cancel-manual-draft').disabled=busy;
    $('manual-draft-subject').disabled=busy;$('manual-draft-body').disabled=busy;
  }
}

async function saveManualDraft() {
  const row=state.invoices.find(r=>r.id===state.selectedId),e=manualDraftEditors.get(row?.id);if(!e?.open||manualDraftBusy.has(row.id))return;
  let c=visitorCases.find(x=>x.invoice_id===row.id);
  const reason=savedDraftBlockReason(row,c);if(reason){e.message=reason;$('manual-draft-result').textContent=reason;return;}
  e.requestId ||= crypto.randomUUID();manualDraftBusy.add(row.id);e.message='Saving your changes…';renderSendState();
  try{
    if(!c){const opened=await api('/api/cases',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({run_id:state.currentRun,invoice_id:row.id})});c=opened.case;mergeExecutionCases([c]);}
    const response=await api(`/api/cases/${c.id}/draft/edit`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({request_id:e.requestId,expected_draft:e.expected,subject:e.subject,body:e.body})});
    mergeExecutionCases([response.case]);e.open=false;e.requestId=null;e.message='Human-edited draft saved. Review it, then click Send reminder.';aiDraftEditor(row.id).message='';
  }catch(error){
    if(error.status && error.status<500){e.requestId=null;e.message=`${error.message} Changes were not saved. If another action changed the draft, cancel and reopen Edit draft.`;}
    else e.message=`${error.message} Save outcome unknown. Retry checks this same edit request.`;
  }finally{manualDraftBusy.delete(row.id);renderQueue();if(state.selectedId===row.id){renderDetail();renderCase();}}
}

async function generateAIDraft() {
  const row = state.invoices.find(r => r.id === state.selectedId); if (!row) return;
  let c = visitorCases.find(x => x.invoice_id === row.id);
  const reason = aiDraftBlockReason(row,c); if (reason) {toast(reason); return;}
  const editor = aiDraftEditor(row.id);
  if (manualDraftEditors.has(row.id)) manualDraftEditors.get(row.id).message='';
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
