"""LangGraph case agent: inspect -> interpret -> choose -> approve -> act.

One durable thread per browser-owned case, deterministic financial tools and a
bounded LLM only for untrusted reply interpretation. No chain-of-thought tracing.
"""
import asyncio
from collections import defaultdict
from datetime import date,timedelta
from decimal import Decimal
from typing import TypedDict
from uuid import uuid4

from fastapi import HTTPException
from langgraph.graph import StateGraph,START,END
from langgraph.types import interrupt,Command
from langsmith import tracing_context

from ..language import facts_for
from ..storage import StoreRequestError,StorageError
from .checkpoints import SupabaseSaver
from .reporting import case_snapshot, case_result
from .diagnostics import failure


class State(TypedDict,total=False):
    actor: str
    case_id: str
    event: str
    event_key: str
    mode: str
    allow_auto_send: bool
    review: dict | None
    proposal: dict
    approved: bool


class CaseAgent:
    def __init__(self,store,language,mail,cases):
        self.store,self.language,self.mail,self.cases=store,language,mail,cases
        self.locks=defaultdict(asyncio.Lock)
        self.job_locks=defaultdict(asyncio.Lock)
        g=StateGraph(State)
        for name in ['load','interpret','choose','approval','execute','plan_followup','finish']:
            g.add_node(name,getattr(self,name))
        g.add_edge(START,'load');g.add_edge('load','interpret');g.add_edge('interpret','choose')
        g.add_conditional_edges('choose',lambda s:'finish' if s['proposal']['tool']=='none' else 'approval' if s['proposal']['tool'] in {'send_email','send_followup_email','record_promise'} else 'execute',
            {'finish':'finish','approval':'approval','execute':'execute'})
        g.add_edge('approval','execute')
        g.add_conditional_edges('execute',lambda s:'plan_followup' if s['event']=='due' and s['proposal']['tool']=='check_due' else 'finish',{'plan_followup':'plan_followup','finish':'finish'})
        g.add_conditional_edges('plan_followup',lambda s:'approval' if s['proposal']['tool']=='send_followup_email' else 'finish',{'approval':'approval','finish':'finish'})
        g.add_edge('finish',END)
        self.graph=g.compile(checkpointer=SupabaseSaver(store))

    async def case(self,actor,case_id):
        c=await self.store.rpc('ca_case_get',{'p_session_key':actor,'p_case_id':case_id})
        if c is None:raise HTTPException(404,'Case not found in this browser session.')
        return c

    def config(self,case_id):
        return {'configurable':{'thread_id':case_id},'recursion_limit':16,'callbacks':[]}

    async def patch(self,s,patch,node,message,status='completed'):
        return await self.store.rpc('ca_workflow_patch',{'p_session_key':s['actor'],'p_case_id':s['case_id'],
            'p_patch':patch,'p_event_key':s['event_key']+':'+node+':'+status,'p_node':node,'p_status':status,'p_message':message})

    async def load(self,s):
        c=await self.case(s['actor'],s['case_id'])
        scenario=(c.get('workflow') or {}).get('scenario')
        if scenario is None:scenario=await self.store.rpc('ca_scenario',{'p_invoice_id':c['invoice_id']})
        if s['event']=='reply':
            follow=(c.get('workflow') or {}).get('followup') or {}
            if follow.get('status') in {'draft_ready','quota_wait','unknown','review_required'}:
                await self.patch(s,{'followup':{**follow,'status':'superseded'}},'supersede','New customer reply supersedes the unsent follow-up.')
        await self.patch(s,{'version':'langgraph-case-v1','mode':s['mode'],'scenario':scenario,
            'pending':None,'processing':True,'status':'processing','next_action':'Inspect case and evidence'},'load','Loaded saved case, policy and synthetic evidence.')
        return {}

    async def interpret(self,s):
        if s['event']!='reply':return {'review':None}
        c=await self.case(s['actor'],s['case_id'])
        message=next((m for m in c['messages'] if m['id']==s['event_key']),None)
        if message is None:raise HTTPException(404,'Reply not found in this case.')
        review=message['review']
        if review['status'] not in {'pending_review','model_attempt_reserved'}:return {'review':review}
        claimed=await self.store.rpc('ca_reply_claim',{'p_session_key':s['actor'],'p_case_id':s['case_id'],'p_request_id':s['event_key']})
        if claimed:
            await self.patch(s,{},'interpret','Interpreting the simulated customer reply.','started')
            facts=facts_for(c['snapshot']['invoice'],c['snapshot'])
            facts['as_of_date']=c['workflow'].get('demo_date',facts['as_of_date'])
            review=await self.language.classify(facts,message['text'])
            review.update({'input_channel':'simulated_customer_reply','financial_state_updated':False})
        else:
            review={'classification':None,'status':'manual_review','review_required':True,
                'reason':'An earlier model attempt was reserved but its result was not saved. No automatic repeat call.',
                'simulated_input':True,'invoice_payment_updated':False,'audit':{'api_attempted':False}}
        await self.store.rpc('ca_case_review',{'p_session_key':s['actor'],'p_case_id':s['case_id'],'p_request_id':s['event_key'],'p_review':review})
        await self.patch(s,{},'interpret','Reply interpretation saved; financial facts remain unchanged.')
        return {'review':review}

    async def choose(self,s):
        c=await self.case(s['actor'],s['case_id']);row=c['snapshot']['invoice'];w=c['workflow'];sc=w.get('scenario',{})
        proposal={'tool':'none','status':'manual_review_required','next_action':'Review case','message':'Case needs a human decision.'}
        if s['event']=='reply':
            review=s.get('review') or {};v=review.get('classification') or {};intent=v.get('intent')
            if c['collection_status']=='dispute_hold_review_required' or intent=='dispute':
                proposal={'tool':'inspect_dispute','status':'dispute_hold_review_required','next_action':'Investigate supporting evidence','message':'Dispute holds collection; retrieve controlled evidence.'}
            elif review.get('status')!='classified_for_review':
                proposal.update(next_action='Review the original reply',message='Model unavailable, capped or output unsupported. No action invented.')
            elif intent=='promise_to_pay':
                promised=v.get('promise_date');today=date.fromisoformat(w.get('demo_date',c['snapshot']['as_of_date']))
                if promised and today<date.fromisoformat(promised)<=today+timedelta(days=365):
                    proposal={'tool':'record_promise','status':'promise_review_required','next_action':'Record supported promise',
                        'promise':v,'message':'Literal future promise is supported by the reply; amounts stay bounded.'}
                else:proposal.update(next_action='Ask for a specific future payment date',message='Promise is ambiguous or outside the allowed window.')
            elif intent=='payment_claim':
                proposal={'tool':'reconcile','status':'reconciliation_required','next_action':'Match synthetic payment evidence','message':'A claim is not proof. Match invoice, currency and posted ledger evidence.'}
            elif intent=='request_info':
                proposal={'tool':'retrieve_documents','status':'document_review_required','next_action':'Retrieve available synthetic documents','message':'Retrieve only controlled documents belonging to this invoice.'}
        elif s['event']=='due':
            if row['dispute'] or c['collection_status']=='dispute_hold_review_required':
                proposal.update(status='dispute_hold_review_required',next_action='Review dispute evidence',message='Dispute hold prevents follow-up.')
                await self.patch(s,{'proposal':proposal,'status':proposal['status'],'next_action':proposal['next_action']},'choose',proposal['message'])
                return {'proposal':proposal}
            promise=w.get('promise') or sc.get('prior_promise')
            today=date.fromisoformat(w.get('demo_date',c['snapshot']['as_of_date']))
            if promise and today>date.fromisoformat(promise.get('promise_date') or promise['date']):
                proposal={'tool':'check_due','status':'followup_due','next_action':'Check payment evidence for expired promise','message':'Demo date passed the promise date; check payment evidence before follow-up.'}
            else:proposal={'tool':'none','status':c['collection_status'],'next_action':'Wait until the promised date passes','message':'No promise is overdue on the selected demo date.'}
        elif row['dispute']:
            proposal={'tool':'inspect_dispute','status':'dispute_hold_review_required','next_action':'Investigate dispute','message':'Source dispute blocks collection reminders.'}
        elif c['collection_status']!='awaiting_outreach' or len(c['messages'])>int(bool(row.get('draft'))):
            proposal={'tool':'none','status':c['collection_status'],'next_action':'Review existing conversation','message':'Existing response/contact history retained; no blanket resend.'}
        elif sc.get('missing_contact'):
            proposal={'tool':'none','status':'contact_required','next_action':'Confirm customer contact','message':'Synthetic scenario has no verified AR contact. No reminder sent.'}
        elif sc.get('prior_transport'):
            proposal={'tool':'none','status':'delivery_exception','next_action':'Review contact and prior delivery','message':'Synthetic prior '+sc['prior_transport']+' evidence found; this is not a live Resend event.'}
        elif sc.get('prior_promise'):
            proposal={'tool':'check_due','status':'followup_due','next_action':'Check missed-promise evidence','message':'Synthetic prior promise requires payment verification.'}
        elif row.get('draft') and row['eligible']:
            proposal={'tool':'send_email','status':'ready_for_outreach','next_action':'Send reminder','message':'Eligible overdue draft passed source/policy checks.'}
        elif row.get('lifecycle') in {'pre_due','due_today'}:
            proposal={'tool':'none','status':'preventive_review','next_action':'Review prevention risk','message':'Preventive risk assessed; pre-due sending is not enabled by the overdue mail policy.'}
        else:proposal={'tool':'none','status':'monitoring','next_action':'Monitor or review invoice','message':'No eligible reminder action for this invoice.'}
        await self.patch(s,{'proposal':proposal,'status':proposal['status'],'next_action':proposal['next_action']},'choose',proposal['message'])
        return {'proposal':proposal}

    async def approval(self,s):
        tool=s['proposal']['tool']
        needs=tool in {'send_email','send_followup_email','record_promise'} and (s['mode']=='limited' or (tool in {'send_email','send_followup_email'} and not s.get('allow_auto_send')))
        if not needs:
            await self.patch(s,{},'authorization','Autopilot policy allowed this bounded case action.')
            return {'approved':True}
        await self.patch(s,{'pending':{'event_key':s['event_key'],'tool':tool},'status':'awaiting_approval','processing':False,'next_action':s['proposal']['next_action']},'approval','Action prepared; waiting for your approval.')
        answer=interrupt({'event_key':s['event_key'],'tool':tool,'message':s['proposal']['next_action']})
        await self.patch(s,{},'authorization','User approved the pending action.' if answer is True else 'Pending action declined or superseded.')
        return {'approved':answer is True}

    def match(self,c):
        row=c['snapshot']['invoice'];balance=Decimal(row['amount']);seen=set();matched=[]
        for p in c['workflow'].get('scenario',{}).get('ledger',[]):
            if p.get('invoice_id')!=row['id'] or p.get('currency')!=c['snapshot']['currency'] or p.get('status')!='posted' or p.get('synthetic') is not True:continue
            if not p.get('reference') or p['reference'] in seen:continue
            value=Decimal(p['amount'])
            if not value.is_finite() or value<=0:continue
            seen.add(p['reference']);matched.append(p)
        amount=sum((Decimal(p['amount']) for p in matched),Decimal(0))
        if amount>balance:return {'matched_amount':'0.00','remaining_amount':str(balance),'financial_state':'review_overpayment','evidence':matched}
        return {'matched_amount':f'{amount:.2f}','remaining_amount':f'{balance-amount:.2f}',
            'financial_state':'fully_matched' if amount==balance and balance>0 else 'partially_matched' if amount>0 else 'unmatched','evidence':matched}

    async def execute(self,s):
        tool=s['proposal']['tool'];c=await self.case(s['actor'],s['case_id']);proposal=s['proposal']
        newest=next((m for m in reversed(c['messages']) if m['channel']=='simulated_customer_reply'),None)
        superseded=s['event']=='reply' and newest and newest['id']!=s['event_key']
        if (tool in {'send_email','send_followup_email','record_promise'} and not s.get('approved')) or superseded:
            patch={'status':'manual_review_required','pending':None,'next_action':'Review before any action'}
            if tool=='send_followup_email':patch['followup']={**c['workflow'].get('followup',{}),'status':'declined'}
            await self.patch(s,patch,'execute','Action declined or superseded. No side effect executed.')
            return {}
        if tool=='none':return {}
        await self.patch(s,{'processing':True},'execute','Running allowed tool: '+tool,'started')
        patch={'pending':None};result={'tool':tool,'synthetic_evidence':True}
        if tool=='send_email':
            if c.get('outbound') and c['outbound']['state']=='uncertain':
                patch.update(status='delivery_unknown',next_action='Review unknown send outcome; retry only explicitly')
                result['message']='Unknown prior outcome retained; graph replay did not retry email.'
            else:
                try:
                    sent=(await self.mail.send_case(s['actor'],s['case_id']))['case'];out=sent['outbound']
                    patch.update(status='awaiting_delivery' if out['state']=='accepted' else 'delivery_unknown',next_action='Await verified delivery' if out['state']=='accepted' else 'Review send outcome')
                    result.update(message='Resend accepted email; delivery is not confirmed.' if out['state']=='accepted' else 'Email outcome unknown; no automatic retry.',mail_id=out['id'],synthetic_evidence=False)
                except (HTTPException,StoreRequestError) as exc:
                    limited=(exc.status_code if isinstance(exc,HTTPException) else exc.status)==429
                    patch.update(status='quota_wait' if limited else 'manual_review_required',next_action='Retry manually after the UTC mail quota resets' if limited else 'Review email configuration/policy before sending')
                    result['message']='No email sent: '+str(exc.detail if isinstance(exc,HTTPException) else exc)
        elif tool=='send_followup_email':
            follow=dict(c['workflow']['followup'])
            try:
                sent=(await self.mail.send_followup(s['actor'],s['case_id'],s['event_key']))['case']
                out=next(x for x in sent['followups'] if x['event_key']==s['event_key'])
                follow['status']='accepted' if out['state']=='accepted' else 'unknown'
                patch.update(status='awaiting_delivery' if out['state']=='accepted' else 'delivery_unknown',next_action='Await follow-up delivery and customer response' if out['state']=='accepted' else 'Review follow-up outcome; retry only explicitly')
                result.update(message='Resend accepted follow-up; payment remains outstanding.' if out['state']=='accepted' else 'Follow-up outcome unknown; no automatic retry.',synthetic_evidence=False,mail_id=out['id'])
            except (HTTPException,StoreRequestError) as exc:
                limited=(exc.status_code if isinstance(exc,HTTPException) else exc.status)==429
                follow['status']='quota_wait' if limited else 'review_required'
                patch.update(status='quota_wait' if limited else 'manual_review_required',next_action='Retry follow-up explicitly after mail quota resets' if limited else 'Review follow-up configuration or case hold')
                result['message']='No follow-up sent: '+str(exc.detail if isinstance(exc,HTTPException) else exc)
            patch['followup']=follow
        elif tool=='record_promise':
            v=proposal['promise'];follow=(date.fromisoformat(v['promise_date'])+timedelta(days=1)).isoformat()
            patch.update(status='promise_recorded',collection_status='promise_recorded',promise=v,promise_event_key=s['event_key'],followup=None,followup_date=follow,next_action='Check demo payment on '+follow)
            result['message']='Supported promise recorded; check-after date saved. No unattended email scheduled.'
        elif tool in {'reconcile','check_due'}:
            match=self.match(c);full=match['financial_state']=='fully_matched'
            status='demo_payment_matched' if full else 'demo_partial_payment' if match['financial_state']=='partially_matched' else 'followup_due' if tool=='check_due' else 'reconciliation_required'
            patch.update(status=status,collection_status=status,reconciliation=match,next_action='Review posting to source AR' if full else 'Review remaining balance and follow-up' if tool=='check_due' or match['financial_state']=='partially_matched' else 'Request remittance or unmatched payment evidence')
            result.update(message='Synthetic ledger checked: '+match['financial_state'].replace('_',' ')+'. Source AR balance unchanged.',reconciliation=match)
        elif tool in {'inspect_dispute','retrieve_documents'}:
            sc=c['workflow'].get('scenario',{});docs=sc.get('documents',[]);comparison=sc.get('comparison')
            report={'documents':docs,'comparison':comparison,'synthetic':True,
                'missing_documents':[key for key in sc.get('required_documents',[]) if key not in {d['id'] for d in docs}]}
            if comparison:
                if comparison['type']=='price':difference=(Decimal(comparison['invoice_unit_price'])-Decimal(comparison['po_unit_price']))*comparison['quantity']
                else:difference=(comparison['invoiced_units']-comparison['delivered_units'])*Decimal(comparison['unit_price'])
                report['difference_amount']=f'{difference:.2f}'
            patch.update(status='dispute_hold_review_required' if tool=='inspect_dispute' else 'documents_ready',
                collection_status='dispute_hold_review_required' if tool=='inspect_dispute' else 'documents_ready',evidence=report,
                next_action='Review discrepancy or missing evidence' if tool=='inspect_dispute' else 'Review documents and prepare customer response')
            result.update(message=('Dispute held; ' if tool=='inspect_dispute' else '')+str(len(docs))+' controlled synthetic document(s) retrieved.'+(' Missing: '+', '.join(report['missing_documents'])+'.' if report['missing_documents'] else '')+' No document email sent.',evidence=report)
        await self.store.rpc('ca_workflow_effect',{'p_session_key':s['actor'],'p_case_id':s['case_id'],'p_event_key':s['event_key'],
            'p_tool':tool,'p_result':result,'p_patch':patch})
        return {}

    async def plan_followup(self,s):
        c=await self.case(s['actor'],s['case_id']);w=c['workflow'];sc=w.get('scenario',{});m=w.get('reconciliation') or {}
        row=c['snapshot']['invoice'];prior=w.get('followup') or {}
        promise=w.get('promise') or sc.get('prior_promise') or {}
        promised=promise.get('promise_date') or promise.get('date')
        newest=next((x for x in reversed(c['messages']) if x['channel']=='simulated_customer_reply'),None)
        reason=None
        if m.get('financial_state')=='fully_matched':reason='Payment matched in demo ledger. No follow-up email needed.'
        elif m.get('financial_state')=='review_overpayment':reason='Payment evidence needs review; no follow-up generated.'
        elif row['dispute'] or c['collection_status']=='dispute_hold_review_required':reason='Dispute hold blocks outreach.'
        elif sc.get('missing_contact') or sc.get('prior_transport'):reason='Contact or simulated delivery issue requires review.'
        elif newest and newest['id']!=w.get('promise_event_key'):reason='A newer or unsupported reply needs review before chasing a promise.'
        elif not promised:reason='No supported promise date.'
        elif any(e['type'] in {'email.bounced','email.complained','email.failed','email.suppressed'} for e in (c.get('outbound') or {}).get('events',[])):reason='Original delivery issue requires review.'
        elif c.get('outbound') and c['outbound']['state']!='accepted':reason='Original reminder outcome is unknown; reconcile it before new outreach.'
        elif prior.get('event_key')==s['event_key']:
            if prior.get('status')=='draft_ready':
                # Business patch can persist before the node checkpoint. Replay must
                # still reach authorization, not strand an unsendable saved draft.
                return {'proposal':{'tool':'send_followup_email','status':'followup_due','next_action':'Send missed-promise follow-up'},'approved':False}
            reason='Existing follow-up retained; no duplicate draft or send.'
        if reason:
            status=w.get('status','manual_review_required')
            if m.get('financial_state')!='fully_matched':
                status='contact_required' if sc.get('missing_contact') else 'delivery_exception' if sc.get('prior_transport') else 'manual_review_required'
                if row['dispute'] or c['collection_status']=='dispute_hold_review_required':status='dispute_hold_review_required'
            await self.patch(s,{'status':status,'next_action':reason},'plan_followup',reason)
            return {'proposal':{'tool':'none'}}
        remaining=Decimal(m['remaining_amount']);currency=c['snapshot']['currency']
        draft={'subject':'Payment promise follow-up — '+row['id'],
            'body':f"Hello {row['customer']},\n\nOur demo records show a payment promise for invoice {row['id']} dated {promised}. "
                f"After checking the available synthetic payment evidence, {currency} {remaining:,.2f} remains unmatched. "
                "Please confirm the payment date or share remittance details if payment has been made.\n\nThank you,\nCollections team",
            'generation_mode':'template_no_llm','remaining_amount':f'{remaining:.2f}'}
        follow={'event_key':s['event_key'],'promise_date':promised,'as_of_date':w.get('demo_date',c['snapshot']['as_of_date']),'draft':draft,'status':'draft_ready'}
        proposal={'tool':'send_followup_email','status':'followup_due','next_action':'Send missed-promise follow-up','message':'Payment evidence checked; prepare reminder only for the demo remaining amount.'}
        await self.patch(s,{'followup':follow,'proposal':proposal,'status':'followup_due','next_action':proposal['next_action']},'plan_followup','Follow-up template prepared from saved promise and synthetic remaining balance. No model call.')
        return {'proposal':proposal,'approved':False}

    async def finish(self,s):
        await self.patch(s,{'processing':False,'pending':None},'finish','This case invocation finished. Waiting/review states remain open.')
        return {}

    async def invoke(self,actor,case_id,event='start',event_key='start',mode='limited',allow_auto_send=False):
        async with self.locks[case_id]:
            await self.case(actor,case_id)
            config=self.config(case_id)
            with tracing_context(enabled=False):
                previous=await self.graph.aget_state(config)
                if (event=='start' or (event=='due' and previous.values.get('event_key')==event_key)) and previous.values:
                    if previous.next and not any(t.interrupts for t in previous.tasks):
                        await self.graph.ainvoke(None,config,durability='sync')
                    return await self.case(actor,case_id)  # New runs never silently change prior authority.
                if previous.tasks and any(t.interrupts for t in previous.tasks):
                    await self.graph.ainvoke(Command(resume=False),config,durability='sync')
                await self.graph.ainvoke({'actor':actor,'case_id':case_id,'event':event,'event_key':event_key,
                    'mode':mode,'allow_auto_send':allow_auto_send,'proposal':{},'approved':False,'review':None},config,durability='sync')
            return await self.case(actor,case_id)

    async def approve(self,actor,case_id,event_key,approved):
        async with self.locks[case_id]:
            c=await self.case(actor,case_id);pending=(c.get('workflow') or {}).get('pending')
            if not pending or pending['event_key']!=event_key:raise HTTPException(409,'This approval is stale or already completed. Refresh the case.')
            with tracing_context(enabled=False):
                await self.graph.ainvoke(Command(resume=approved),self.config(case_id),durability='sync')
            return {'case':await self.case(actor,case_id)}

    async def resume(self,actor,case_id):
        async with self.locks[case_id]:
            c=await self.case(actor,case_id)
            if not c.get('workflow'):raise HTTPException(409,'This case has no LangGraph workflow to resume.')
            with tracing_context(enabled=False):
                config=self.config(case_id);state=await self.graph.aget_state(config)
                newest=next((m for m in reversed(c['messages']) if m['channel']=='simulated_customer_reply'),None)
                # Reply can be committed before its first input checkpoint exists.
                if newest and newest['review']['status'] in {'pending_review','model_attempt_reserved'} and state.values.get('event_key')!=newest['id']:
                    if any(t.interrupts for t in state.tasks):
                        await self.graph.ainvoke(Command(resume=False),config,durability='sync')
                    await self.graph.ainvoke({'actor':actor,'case_id':case_id,'event':'reply','event_key':newest['id'],
                        'mode':c['workflow']['mode'],'allow_auto_send':False,'proposal':{},'approved':False,'review':None},config,durability='sync')
                elif not any(t.interrupts for t in state.tasks) and state.next:
                    await self.graph.ainvoke(None,config,durability='sync')
            return {'case':await self.case(actor,case_id)}

    async def retry_email(self,actor,case_id):
        async with self.locks[case_id]:
            c=await self.case(actor,case_id)
            if c['workflow']['status'] not in {'delivery_unknown','quota_wait'}:
                raise HTTPException(409,'This case is not waiting for an explicit email retry.')
            result=await self.mail.send_case(actor,case_id)
            accepted=result['case']['outbound']['state']=='accepted'
            s={'actor':actor,'case_id':case_id,'event_key':'retry:'+str(uuid4())}
            c=await self.patch(s,{'status':'awaiting_delivery' if accepted else 'delivery_unknown','next_action':'Await verified delivery' if accepted else 'Review unknown outcome','pending':None,'processing':False},
                'execute','Explicit email action accepted by Resend.' if accepted else 'Explicit retry outcome remains unknown.')
            return {'case':c}

    async def retry_followup(self,actor,case_id):
        async with self.locks[case_id]:
            c=await self.case(actor,case_id);follow=(c.get('workflow') or {}).get('followup') or {}
            if follow.get('status') not in {'quota_wait','unknown','review_required'}:raise HTTPException(409,'No follow-up is waiting for explicit retry.')
            result=await self.mail.send_followup(actor,case_id,follow['event_key'],explicit_retry=True)
            out=next(x for x in result['case']['followups'] if x['event_key']==follow['event_key'])
            accepted=out['state']=='accepted';follow['status']='accepted' if accepted else 'unknown'
            s={'actor':actor,'case_id':case_id,'event_key':'followup-retry:'+str(uuid4())}
            c=await self.patch(s,{'followup':follow,'status':'awaiting_delivery' if accepted else 'delivery_unknown','next_action':'Await follow-up delivery' if accepted else 'Review unknown follow-up outcome'},'execute','Explicit follow-up accepted by Resend.' if accepted else 'Follow-up outcome still unknown.')
            return {'case':c}

    async def run_job(self,actor,run_id,mode):
        progress={'processed':0,'total':0,'auto_send_limit':3,'auto_case_ids':[]}
        async def save(status='running'):
            return await self.store.rpc('ca_agent_job',{'p_action':'update','p_session_key':actor,'p_run_id':run_id,'p_progress':progress,'p_status':status})
        try:
            job=await self.store.rpc('ca_agent_job',{'p_action':'get','p_session_key':actor,'p_run_id':run_id})
            progress.update(job['progress'])
            progress.setdefault('report',{'version':1,'invoices':{},'legacy_partial':bool(progress.get('processed'))})
            report=progress['report']['invoices']
            progress['processed']=0
            run=await self.store.get_run(run_id);rows=run['result']['invoices'];progress['total']=len(rows)
            progress.pop('error',None);progress.pop('failure',None)
            for row in rows:
                progress['current_invoice']=row['id']
                entry=report.setdefault(row['id'],{'completed':False})
                if entry['completed']:
                    progress['processed']+=1
                    continue
                phase='open_case'
                try:
                    opened=await self.cases.open(actor,run_id,row['id']);c=opened['case']
                    entry.setdefault('case_id',c['id']);entry.setdefault('before',case_snapshot(c))
                    ids=progress['auto_case_ids']
                    if opened['recorded'] and mode=='autopilot' and len(ids)<3 and row.get('draft') and row['eligible']:
                        ids.append(c['id'])
                    phase='save_baseline'
                    await save()  # Durable baseline and automatic authority before graph work.
                    phase='process_invoice'
                    if not c.get('workflow'):
                        await self.invoke(actor,c['id'],mode=mode,allow_auto_send=c['id'] in ids)
                    elif c['workflow'].get('processing') and not c['workflow'].get('pending'):
                        await self.resume(actor,c['id'])
                    phase='read_outcome'
                    c=await self.case(actor,c['id'])
                    entry.update(completed=True,after=case_snapshot(c),result=case_result(entry['before'],c))
                    entry.pop('error',None)
                    progress['processed']+=1
                except Exception as exc:
                    # A bad invoice cannot abandon the remaining portfolio. Never
                    # replay a model/send here; explicit recovery uses checkpoints.
                    if phase=='save_baseline':raise
                    entry['error']=failure(exc,row['id'],phase)
                progress['failed']=sum(bool(v.get('error')) for v in report.values())
                progress['attempted']=sum(v.get('completed',False) or bool(v.get('error')) for v in report.values())
                await save()
            await save('completed')  # Terminal scan; failures remain explicit in the report.
        except asyncio.CancelledError:
            progress['failure']={'code':'server_stopped','message':'The server stopped before processing finished. Saved results are retained.','phase':'job','invoice_id':progress.get('current_invoice')}
            try:await save('interrupted')
            except StorageError:pass
            raise
        except Exception as exc:
            progress['failure']=failure(exc,progress.get('current_invoice'),'save_or_load_job')
            progress['error']=progress['failure']['message']
            try:await save('interrupted')
            except StorageError:pass
