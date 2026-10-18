/* Two Markdown pages plus a read-only invoice scenario launcher. */
'use strict';
let guidePage=0;
let guidePages=null;
let guideLoading=null;
let languageStatus=null;

function renderGuideInline(value) {
  const icon='<a class="guide-inbox-image" href="/assets/demo-email-inbox.png" target="_blank" rel="noopener noreferrer" aria-label="View demo inbox screenshot (opens in a new tab)" title="View demo inbox screenshot (opens in a new tab)"><svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="8" cy="8" r="1.5"/><path d="m4 17 5-5 4 4 3-3 5 5"/></svg></a>';
  return escapeHTML(value).replaceAll('[Inbox screenshot](/assets/demo-email-inbox.png)',icon);
}

function renderGuideMarkdown(markdown) {
  const lines=markdown.trim().split('\n'),output=[];
  const cells=line=>line.trim().replace(/^\|/,'').replace(/\|$/,'').split('|').map(cell=>renderGuideInline(cell.trim()));
  for(let i=0;i<lines.length;i++) {
    const line=lines[i].trim();if(!line)continue;
    if(/^\|/.test(line) && /^\|[\s:|\-]+$/.test(lines[i+1]?.trim() || '')) {
      const headers=cells(line);i+=2;const rows=[];
      for(;i<lines.length && /^\|/.test(lines[i].trim());i++)rows.push(cells(lines[i]));
      i--;output.push(`<div class="guide-table-wrap"><table><thead><tr>${headers.map(h=>`<th scope="col">${h}</th>`).join('')}</tr></thead><tbody>${rows.map(row=>`<tr>${row.map(c=>`<td>${c}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`);
    } else if(/^#{1,3} /.test(line))output.push(`<h3>${escapeHTML(line.replace(/^#{1,3} /,''))}</h3>`);
    else output.push(`<p>${escapeHTML(line)}</p>`);
  }
  return output.join('');
}
function languageModeLabel(language) {
  if(!language)return 'LLM calls: checking backend configuration…';
  if(!language.enabled)return 'LLM calls disabled · templates and manual reply review';
  if(language.configuration_error)return 'LLM calls blocked by configuration · templates/manual review';
  if(!language.key_configured)return 'LLM calls unavailable · API key missing';
  return `LLM calls enabled · ${language.provider} / ${language.model} · drafting and reply interpretation`;
}
function updateLanguageLabels(language) {
  languageStatus=language;
  for(const id of ['llm-mode-summary','guide-llm-status'])if($(id))$(id).textContent=languageModeLabel(language);
}
function llmCallLabel(audit,success=false) {
  if(audit?.api_attempted===false)return 'No LLM API call for this action';
  if(audit?.api_attempted===true) {
    const model=audit.returned_model || audit.model || audit.requested_model;
    return `${success?'LLM API call completed':'LLM API call attempted · fallback or review required'}${model?' · '+model:''}`;
  }
  return 'LLM call evidence is not recorded for this saved action';
}
function showGuidePage(page) {
  guidePage=Math.max(0,Math.min(2,page));
  $('guide-page-count').textContent=`Page ${guidePage+1} of 3`;
  for(let i=0;i<3;i++){$(`guide-tab-${i}`).setAttribute('aria-selected',String(i===guidePage));$(`guide-tab-${i}`).tabIndex=i===guidePage?0:-1;}
  $('guide-content').setAttribute('aria-labelledby',`guide-tab-${guidePage}`);
  $('guide-content').innerHTML=guidePage===2?renderScenarioGuide():guidePages?renderGuideMarkdown(guidePages[guidePage]):'<p>Loading the workflow guide…</p>';
  $('guide-content').scrollTop=0;
  $('guide-prev').disabled=guidePage===0;$('guide-next').disabled=guidePage===2;
  if(guidePage===2)bindScenarioGuide();
}
async function openWorkflowGuide() {
  const dialog=$('workflow-guide');
  showGuidePage(0);updateLanguageLabels(languageStatus);
  if(!dialog.open){if(dialog.showModal)dialog.showModal();else dialog.setAttribute('open','');}
  document.body.classList.add('workflow-guide-open');$('guide-tab-0').focus();
  if(!guidePages) {
    guideLoading ||= fetch('/assets/HOW_IT_WORKS.md',{cache:'no-store'}).then(response=>{if(!response.ok)throw Error('Guide unavailable');return response.text();}).then(markdown=>{const pages=markdown.split(/\n---\s*\n/);if(pages.length!==2)throw Error('The guide must have two pages');guidePages=pages;}).finally(()=>{guideLoading=null;});
    try{await guideLoading;showGuidePage(guidePage);}
    catch(error){$('guide-content').innerHTML='<p>The guide could not load. Try again or open the Markdown source below.</p>';}
  }
}
function closeWorkflowGuide(){const dialog=$('workflow-guide');if(!dialog.open)return;if(dialog.close)dialog.close();else{dialog.removeAttribute('open');restoreGuideFocus();}}
function restoreGuideFocus(){if($('workflow-guide').open)return;document.body.classList.remove('workflow-guide-open');if(!$('invoice-dialog').open)$('open-workflow-guide').focus({preventScroll:true});}
function initWorkflowGuide() {
  $('open-workflow-guide').onclick=openWorkflowGuide;$('close-workflow-guide').onclick=closeWorkflowGuide;
  $('guide-prev').onclick=()=>showGuidePage(guidePage-1);$('guide-next').onclick=()=>showGuidePage(guidePage+1);
  for(let i=0;i<3;i++)$(`guide-tab-${i}`).onclick=()=>showGuidePage(i);
  $('guide-tabs').onkeydown=event=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(event.key)){event.preventDefault();showGuidePage(event.key==='Home'?0:event.key==='End'?2:(guidePage+(event.key==='ArrowLeft'?2:1))%3);$(`guide-tab-${guidePage}`).focus();}};
  $('workflow-guide').addEventListener('close',restoreGuideFocus);
  $('workflow-guide').addEventListener('click',event=>{const bounds=$('workflow-guide').getBoundingClientRect();if(event.target===$('workflow-guide') && (event.clientX<bounds.left||event.clientX>bounds.right||event.clientY<bounds.top||event.clientY>bounds.bottom))closeWorkflowGuide();});
  document.addEventListener('keydown',event=>{if(event.key==='Escape' && $('workflow-guide').open){event.preventDefault();closeWorkflowGuide();}});
}


// Descriptions explain seeded evidence; outcomes still come from the backend.
const scenarioWalkthroughs={
 'INV-10601':['Future payment promise','Offer a dated payment commitment.','Send the suggested reply; approve Record payment promise if requested. Then inspect the saved promise and check-after date.'],
 'INV-10602':['Missed payment promise','A synthetic prior promise is already overdue.','Open Payment promises in the header and Process due promises. Review the follow-up under this case’s saved approval mode.'],
 'INV-10603':['Ambiguous payment promise','“Sometime soon” gives no reliable payment date.','Send the suggested reply and inspect the clarification/manual-review result; no firm promise should be invented.'],
 'INV-10604':['Price dispute','The seeded purchase order price is lower than the invoice price.','Send the dispute reply. Inspect the price comparison and the reminder hold; no credit note is automatically issued.'],
 'INV-10605':['Quantity dispute','Seeded delivery evidence shows fewer units received than billed.','Send the dispute reply and inspect the quantity comparison and collection hold.'],
 'INV-10606':['Missing delivery evidence','The scenario deliberately has no proof of delivery.','Send the reply and inspect missing-document evidence and the review hold.'],
 'INV-10607':['Payment claim · full match','A posted synthetic payment matches this invoice in full.','Send the payment claim and inspect the matched evidence and Demo remaining. Source AR stays unchanged.'],
 'INV-10608':['Payment claim · partial match','The synthetic ledger contains a partial payment of USD 5,000.','Send the payment claim and inspect the matched amount and remaining demo balance. Source AR stays unchanged.'],
 'INV-10609':['Payment claim · no match','The seeded payment belongs to a different invoice.','Send the claim and inspect the reconciliation exception. A customer claim alone is not payment proof.'],
 'INV-10610':['Invoice copy requested','A synthetic invoice document is available.','Send the document request and inspect retrieved evidence. Documents are presented for review, not automatically emailed.'],
 'INV-10611':['Purchase order requested','A synthetic purchase order is available.','Send the document request and inspect the supporting PO evidence.'],
 'INV-10612':['Proof of delivery requested','A synthetic delivery receipt is available.','Send the document request and inspect the retrieved delivery evidence.'],
 'INV-10613':['Missing customer contact','This scenario has no verified customer contact.','Inspect the contact-required state. Trying a reply does not repair the contact or authorize email.'],
 'INV-10614':['Prior email bounced','The scenario includes a simulated historical bounce, not a new Resend event.','Inspect the delivery exception and review hold. A suggested reply does not clear the delivery restriction.'],
 'INV-10615':['Prior delivery uncertain','A simulated earlier delivery has an unknown outcome.','Inspect the delivery uncertainty. Do not assume delivery succeeded or send a duplicate reminder.']
};
function invoiceScenario(row,current) {
 const summary=scenarioSummaries.find(s=>s.invoice_id===row.id);
 const saved=current?.workflow?.scenario;
 const described=scenarioWalkthroughs[row.id];
 return {title:summary?.label || saved?.label || described?.[0] || 'Explore customer responses',
  explanation:described?.[1] || (Number(row.amount)<=0?'This invoice has no outstanding balance. Explore reply classification without creating a new debt.':row.dispute?'This invoice already has a dispute. Test a customer response while the review hold remains.':['pre_due','due_today'].includes(row.lifecycle)?'Review preventive or due-date risk and explore simulated customer replies before overdue recovery.':'Test a payment promise, payment claim, dispute or document request on this invoice.'),
  action:described?.[2] || 'Choose a reply category, insert the suggested text, then click Send simulated reply. Inspect current status, next step and invoice activity.',
  reply:row.id==='INV-10601'?genericReply('promise',row,current):saved?.suggested_reply || summary?.suggested_reply || ''};
}
function scenarioNextStep(row,current) {
 if(!current)return 'First choose Run collections from the queue to create this browser’s saved cases. You can prepare a reply below now; it remains unsent.';
 const w=current.workflow || {};
 if(w.pending?.tool==='record_promise')return 'A payment promise awaits approval. Review the proposed date and choose Record payment promise above the email.';
 if(w.promise)return 'A promise is already recorded. Review its saved date; use Payment promises to advance the simulation date and Process due promises.';
 if(w.reconciliation?.financial_state==='fully_matched')return 'Payment evidence is already fully matched in the demo. Inspect that evidence and Demo remaining; source AR is unchanged.';
 if(w.processing)return 'The agent is processing this case. Watch invoice activity for the saved result.';
 return `Current state: ${rowView(row).label}. ${rowView(row).next}.`;
}
function renderScenarioGuide() {
 const rows=[...state.invoices].sort((a,b)=>Number(Boolean(scenarioWalkthroughs[b.id]))-Number(Boolean(scenarioWalkthroughs[a.id])) || a.id.localeCompare(b.id));
 return '<h3>Try a scenario</h3><p>Choose an invoice to open its suggested test. Opening is read-only; you decide when to send a simulated reply or approve an action. Existing case history is preserved.</p>'+(!rows.length?'<p>Receivables are loading or unavailable. Reopen this tab after the portfolio loads.</p>':`<div class="guide-table-wrap"><table class="scenario-table"><thead><tr><th>Invoice</th><th>Scenario and suggested test</th><th>Explore</th></tr></thead><tbody>${rows.map(row=>{const current=visitorCases.find(c=>c.invoice_id===row.id),s=invoiceScenario(row,current);return `<tr><td><b>${escapeHTML(row.id)}</b><br>${escapeHTML(row.customer)}</td><td><b>${escapeHTML(s.title)}</b><p>${escapeHTML(s.explanation)}</p><p>${escapeHTML(s.action)}</p><small>${escapeHTML(scenarioNextStep(row,current))}</small></td><td><button class="secondary scenario-open" data-invoice="${escapeHTML(row.id)}">Open scenario</button></td></tr>`;}).join('')}</tbody></table></div>`);
}
function bindScenarioGuide() {
 for(const button of $('guide-content').querySelectorAll('.scenario-open'))button.onclick=()=>{
  closeWorkflowGuide();openInvoiceWorkspace(button.dataset.invoice);
  $('case-reply-text')?.focus({preventScroll:true});
  toast('Scenario opened. Choose a suggested reply, then send it when ready.');
 };
}
function genericReply(category,row,current) {
 const base=demoClock?.demo_date || current?.snapshot?.as_of_date || new Date().toISOString().slice(0,10);
 const date=new Date(base+'T00:00:00Z');date.setUTCDate(date.getUTCDate()+7);
 return {promise:`We will pay invoice ${row.id} on ${date.toISOString().slice(0,10)}.`,
  paid:`We believe invoice ${row.id} has already been paid. Please check your payment records.`,
  dispute:`We dispute the amount on invoice ${row.id}. Please review the agreed price before sending further reminders.`,
  documents:`Please send a copy of invoice ${row.id}.`,
  other:`Please ask the collections team to contact us to discuss invoice ${row.id}.`}[category];
}
function mountSuggestedReplies(row,current) {
 if(!row)return;
 const form=$('case-reply-form'),preview=$('reply-preview');const host=form || preview;if(!host)return;
 const s=invoiceScenario(row,current),key=current?.id || 'invoice:'+row.id;
 const picker=document.createElement('div');picker.className='suggested-replies';
 picker.innerHTML=`<label for="suggested-reply-category">Suggested customer response</label><select id="suggested-reply-category">${s.reply?'<option value="scenario">This invoice’s scenario</option>':''}<option value="promise">Promise to pay</option><option value="paid">Claims already paid</option><option value="dispute">Dispute invoice</option><option value="documents">Request invoice copy</option><option value="other">Other / human review</option></select><button type="button" class="secondary" id="use-suggested-reply">Use suggested reply</button><small>Inserts editable text only. Click Send simulated reply separately to process it.</small>`;
 host.prepend(picker);
 $('use-suggested-reply').onclick=()=>{
  const category=$('suggested-reply-category').value;
  const text=category==='scenario'?s.reply:genericReply(category,row,current);
  $('case-reply-text').value=text;replyDrafts.set(key,text);$('case-reply-text').focus();
 };
 const value=replyDrafts.get(key) ?? replyDrafts.get('invoice:'+row.id);
 if(value!==undefined)$('case-reply-text').value=value;
 $('case-reply-text').oninput=()=>replyDrafts.set(key,$('case-reply-text').value);
}

function draftGenerationExplanation(audit,isFollowup=false) {
 if(isFollowup)return 'Follow-up reminders use a deterministic template built from the saved promise and remaining balance. No LLM drafting call is made.';
 if(audit?.status==='template_only')return 'This saved draft was generated while the LLM was disabled. Enabling the LLM affects new drafts; it does not rewrite existing case history.';
 if(audit?.reason)return 'Template reason: '+audit.reason;
 return 'No successful LLM drafting call is recorded for this saved template. Inspect draft validation and tool evidence for available details.';
}
