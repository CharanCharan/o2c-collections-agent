/* Two-page, read-only workflow guide. Markdown is the editable source. */
'use strict';
let guidePage=0;
let guidePages=null;
let guideLoading=null;
let languageStatus=null;

function renderGuideMarkdown(markdown) {
  const lines=markdown.trim().split('\n'),output=[];
  const cells=line=>line.trim().replace(/^\|/,'').replace(/\|$/,'').split('|').map(cell=>escapeHTML(cell.trim()));
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
  guidePage=Math.max(0,Math.min(1,page));
  $('guide-page-count').textContent=`Page ${guidePage+1} of 2`;
  for(let i=0;i<2;i++){$(`guide-tab-${i}`).setAttribute('aria-selected',String(i===guidePage));$(`guide-tab-${i}`).tabIndex=i===guidePage?0:-1;}
  $('guide-content').setAttribute('aria-labelledby',`guide-tab-${guidePage}`);
  $('guide-content').innerHTML=guidePages?renderGuideMarkdown(guidePages[guidePage]):'<p>Loading the workflow guide…</p>';
  $('guide-content').scrollTop=0;
  $('guide-prev').disabled=guidePage===0;$('guide-next').disabled=guidePage===1;
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
function restoreGuideFocus(){if($('workflow-guide').open)return;document.body.classList.remove('workflow-guide-open');$('open-workflow-guide').focus({preventScroll:true});}
function initWorkflowGuide() {
  $('open-workflow-guide').onclick=openWorkflowGuide;$('close-workflow-guide').onclick=closeWorkflowGuide;
  $('guide-prev').onclick=()=>showGuidePage(guidePage-1);$('guide-next').onclick=()=>showGuidePage(guidePage+1);
  for(let i=0;i<2;i++)$(`guide-tab-${i}`).onclick=()=>showGuidePage(i);
  $('guide-tabs').onkeydown=event=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(event.key)){event.preventDefault();showGuidePage(event.key==='Home'?0:event.key==='End'?1:1-guidePage);$(`guide-tab-${guidePage}`).focus();}};
  $('workflow-guide').addEventListener('close',restoreGuideFocus);
  $('workflow-guide').addEventListener('click',event=>{const bounds=$('workflow-guide').getBoundingClientRect();if(event.target===$('workflow-guide') && (event.clientX<bounds.left||event.clientX>bounds.right||event.clientY<bounds.top||event.clientY>bounds.bottom))closeWorkflowGuide();});
  document.addEventListener('keydown',event=>{if(event.key==='Escape' && $('workflow-guide').open){event.preventDefault();closeWorkflowGuide();}});
}
