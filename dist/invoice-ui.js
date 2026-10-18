/* Invoice workspace dialog: selecting a row is read-only until an action is chosen. */
'use strict';
const replyDrafts=new Map();
let invoiceReturnId=null;

function updateInvoiceDialogTitle(row) {
  const title=$('invoice-dialog-title');if(title && row)title.textContent=`${row.customer} · ${row.id}`;
}

function openInvoiceWorkspace(invoiceId,showEvents=false) {
  const row=state.invoices.find(r=>r.id===invoiceId);if(!row)return;
  const changed=state.selectedId!==invoiceId;
  invoiceReturnId=invoiceId;state.selectedId=invoiceId;
  for(const menu of document.querySelectorAll('.header-menu'))menu.open=false;
  renderQueue(true);renderDetail();
  void refreshCases(false);
  const dialog=$('invoice-dialog');
  if(changed)for(const panel of dialog.querySelectorAll('.invoice-dialog-columns>.panel'))panel.scrollTop=0;
  if(!dialog.open){
    if(dialog.showModal)dialog.showModal();else dialog.setAttribute('open','');
    document.body.classList.add('invoice-workspace-open');
    $('close-invoice-dialog').focus();
  }
  watchInvoiceExecution(visitorCases.find(c=>c.invoice_id===invoiceId));
  if(showEvents){const activity=$('case-agent-activity');activity.tabIndex=-1;activity.focus();activity.scrollIntoView?.({block:'start'});}
}

function restoreQueueFocus() {
  if($('invoice-dialog').open)return;
  stopInvoiceStream();
  document.body.classList.remove('invoice-workspace-open');
  const row=[...$('queue').querySelectorAll('tr[data-id]')].find(r=>r.dataset.id===invoiceReturnId);
  (row?.querySelector('.invoice-open') || $('queue-scroll')).focus({preventScroll:true});
}

function closeInvoiceWorkspace() {
  const dialog=$('invoice-dialog');if(!dialog.open)return;
  if(dialog.close)dialog.close();else {dialog.removeAttribute('open');restoreQueueFocus();}
}

function initInvoiceWorkspace() {
  const dialog=$('invoice-dialog');
  $('close-invoice-dialog').onclick=closeInvoiceWorkspace;
  dialog.addEventListener('close',restoreQueueFocus);
  dialog.addEventListener('click',event=>{
    const bounds=dialog.getBoundingClientRect();
    if(event.target===dialog && (event.clientX<bounds.left || event.clientX>bounds.right || event.clientY<bounds.top || event.clientY>bounds.bottom))closeInvoiceWorkspace();
  });
  document.addEventListener('keydown',event=>{
    if(event.key==='Escape' && dialog.open){event.preventDefault();closeInvoiceWorkspace();}
  });
}
