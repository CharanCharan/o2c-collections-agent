"""Controlled owner-approved sends, verified receipt, explicit review and durable tasks.

No scheduled task automatically sends mail; no payment/dispute source is mutated.
"""
import asyncio
import hmac
import json
from datetime import date, datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi import HTTPException

from ..language import facts_for, validate_reply
from .config import MailConfig, address
from .provider import ResendProvider
from .signatures import verify

DELIVERY={'email.sent','email.delivered','email.bounced','email.complained','email.failed','email.delivery_delayed','email.suppressed'}
INTENTS={'promise_to_pay','payment_claim','dispute','request_info','other'}


class MailService:
    def __init__(self,store,language,config=None,transport=None):
        self.store,self.language=store,language
        self.config=config or MailConfig.from_env()
        self.provider=ResendProvider(self.config,transport)
        self.lock=asyncio.Lock()

    def authorize(self,token):
        if not self.config.owner_token or not hmac.compare_digest((token or '').encode(),self.config.owner_token.encode()):
            raise HTTPException(401,'Owner token required for live email actions.')
        self.config.check()

    async def readiness(self):
        await self.store.rpc('ca_mail_health')

    async def activity(self,run_id):
        await self.readiness()
        run=await self.store.get_run(run_id)
        if not run:raise HTTPException(404,'Run not found.')
        state=await self.store.rpc('ca_mail_state',{'p_run_id':run_id})
        return {'run':run,'mail':state}

    async def send(self,run_id,invoice_id,token):
        self.authorize(token)
        await self.readiness()
        async with self.lock:
            run=await self.store.get_run(run_id)
            if not run:raise HTTPException(404,'Run not found.')
            row=next((r for r in run['result']['invoices'] if r['id']==invoice_id),None)
            if run['status']!='completed' or not row or not row['eligible'] or not row['draft'] or row['dispute']:
                raise HTTPException(409,'A completed run with an eligible reviewed overdue draft is required.')
            state=await self.store.rpc('ca_mail_state',{'p_run_id':run_id})
            existing=next((m for m in state['messages'] if m['invoice_id']==invoice_id),None)
            if existing and existing['state']=='accepted':return await self.activity(run_id)
            # Stored payload is immutable across retries, even if owner changes .env.
            # Do not send a stored intent to a recipient no longer allowed.
            if existing and (existing['payload']['to']!=[self.config.recipient] or existing['payload']['from']!=self.config.sender):
                raise HTTPException(409,'Stored email configuration differs; inspect old intent before proceeding.')
            ident=str(uuid4())
            reply_to='collections-'+ident+'@'+self.config.receiving_domain
            payload={'from':self.config.sender,'to':[self.config.recipient],
                'reply_to':reply_to,'subject':'[O2C DEMO] '+row['draft']['subject'],
                'text':'SYNTHETIC COLLECTIONS DEMO — no real debt or payment request.\n\n'+row['draft']['body']}
            job=await self.store.rpc('ca_mail_prepare',{'p_run_id':run_id,'p_invoice_id':invoice_id,
                'p_id':ident,'p_payload':payload,'p_reply_to':reply_to})
            age=datetime.now(timezone.utc)-datetime.fromisoformat(job['created_at'].replace('Z','+00:00'))
            if age>timedelta(hours=20):
                raise HTTPException(409,'Unresolved intent is older than20hours. Do not resend: reconcile it in Resend first. Provider idempotency expires.')
            try:
                provider_id=await self.provider.send(job)
            except HTTPException as exc:
                await self.store.rpc('ca_mail_finish',{'p_id':job['id'],'p_provider_id':None,'p_error':exc.detail})
            else:
                await self.store.rpc('ca_mail_finish',{'p_id':job['id'],'p_provider_id':provider_id,'p_error':None})
            return await self.activity(run_id)

    async def webhook(self,raw,headers):
        self.config.check()
        event_id=verify(raw,headers,self.config.webhook_secret)
        try:
            event=json.loads(raw)
            kind=event['type'];data=event['data']
            if not isinstance(kind,str) or not isinstance(data,dict):raise ValueError
            provider_id=str(UUID(data['email_id'])) if kind in DELIVERY or kind=='email.received' else None
        except (ValueError,KeyError,TypeError):raise HTTPException(400,'Invalid webhook envelope.') from None
        if kind not in DELIVERY|{'email.received'}:return {'ignored':True,'reason':'Unsubscribed event type.'}
        await self.readiness()
        async with self.lock:
            if await self.store.rpc('ca_mail_seen',{'p_event_id':event_id,'p_reply_id':provider_id if kind=='email.received' else None}):
                return {'recorded':False}
            if kind in DELIVERY:
                job=await self.store.rpc('ca_mail_find',{'p_provider_id':provider_id})
                if not job:
                    # Callback can race the send-result database write; let Resend retry.
                    raise HTTPException(503,'Email acceptance not yet matched; retry callback later.')
                return await self.store.rpc('ca_mail_webhook',{'p_id':job['id'],'p_event_id':event_id,
                    'p_type':kind,'p_evidence':{'provider_id':provider_id,'provider_created_at':str(event.get('created_at',''))[:100],
                        'webhook_signature_verified':True}})
            recipients=data.get('to',[])
            if not isinstance(recipients,list):raise HTTPException(400,'Invalid recipient list.')
            matches=[]
            for recipient in recipients[:10]:
                job=await self.store.rpc('ca_mail_find',{'p_reply_to':address(recipient)})
                if job and job['id'] not in [m['id'] for m in matches]:matches.append(job)
            if len(matches)!=1:return {'ignored':True,'reason':'No unique controlled reply address matched.'}
            job=matches[0]
            if not job['provider_id']:raise HTTPException(503,'Original send is unresolved; retry callback after reconciliation.')
            received=await self.provider.received(provider_id)
            original=await self.provider.sent(job['provider_id'])
            sender=address(received.get('from'))
            actual_to=received.get('to',[])
            headers_received=received.get('headers') or {}
            if not isinstance(headers_received,dict) or not isinstance(actual_to,list):raise HTTPException(502,'Unsupported received email envelope.')
            received_headers={str(k).lower():v for k,v in headers_received.items()}
            references=str(received_headers.get('in-reply-to',''))+' '+str(received_headers.get('references',''))
            message_id=original.get('message_id')
            if not isinstance(message_id,str) or not message_id:
                raise HTTPException(503,'Original RFC message ID not available; retry later.')
            auth=received.get('authentication') or {}
            authenticated=isinstance(auth,dict) and auth.get('dmarc')=='pass'
            matched=(received.get('id')==provider_id and sender==job['payload']['to'][0]
                and job['reply_to'] in [address(v) for v in actual_to]
                and message_id in references.split() and authenticated)
            text=received.get('text')
            supported=isinstance(text,str) and 0<len(text)<=4000
            run=await self.store.get_run(job['run_id'])
            row=next(r for r in run['result']['invoices'] if r['id']==job['invoice_id'])
            facts=facts_for(row,run['result']);facts['as_of_date']=datetime.now(timezone.utc).date().isoformat()
            if matched and supported:
                review=await self.language.classify(facts,text)
            else:
                review={'classification':None,'status':'manual_review' if matched else 'quarantined',
                    'review_required':True,'reason':'Sender/authentication/thread/plain-text checks require manual review.',
                    'audit':{'api_attempted':False}}
            review.update({'simulated_input':False,'invoice_payment_updated':False,'received_from':sender,
                'text':text[:4000] if isinstance(text,str) else '', 'text_truncated':isinstance(text,str) and len(text)>4000,
                'thread_verified':matched,'authentication':auth if isinstance(auth,dict) else {},
                'original_message_id':message_id,'received_message_id':str(received.get('message_id',''))[:300],
                'review_required':True})
            return await self.store.rpc('ca_mail_webhook',{'p_id':job['id'],'p_event_id':event_id,'p_type':kind,
                'p_evidence':{'provider_id':provider_id,'webhook_signature_verified':True,'thread_verified':matched},
                'p_reply_id':provider_id,'p_review':review})

    async def resolve(self,run_id,reply_id,body,token):
        self.authorize(token)
        await self.readiness()
        async with self.lock:
            activity=await self.activity(run_id)
            reply=next((r for r in activity['mail']['replies'] if r['id']==reply_id),None)
            if not reply:raise HTTPException(404,'Reply not found in this run.')
            if reply['resolution'] is not None:return activity
            if body.intent not in INTENTS:raise HTTPException(422,'Unsupported review intent.')
            mail=next(m for m in activity['mail']['messages'] if m['id']==reply['mail_id'])
            row=next(r for r in activity['run']['result']['invoices'] if r['id']==mail['invoice_id'])
            facts=facts_for(row,activity['run']['result']);today=datetime.now(timezone.utc).date()
            facts['as_of_date']=today.isoformat()
            if body.intent=='promise_to_pay':
                if not body.promise_date:raise HTTPException(422,'A literal future promise date is required.')
                try:
                    result=validate_reply({'invoice_id':row['id'],'intent':body.intent,'promise_date':body.promise_date,
                        'promise_amount':body.promise_amount,'evidence_quote':body.evidence_quote},facts,reply['review']['text'])
                    due=date.fromisoformat(result.promise_date)+timedelta(days=1)
                except ValueError:raise HTTPException(422,'Promise must be supported by a literal quote, future ISO date and optional bounded amount.') from None
                if due>today+timedelta(days=366):raise HTTPException(422,'Promise is outside the one-year POC window.')
                task='Check promised payment against reconciled AR; review if unpaid.'
            else:
                if body.promise_date or body.promise_amount:raise HTTPException(422,'Promise fields require promise intent.')
                due=today+timedelta(days=1)
                task={'payment_claim':'Reconcile claimed payment; do not close invoice from email.',
                    'dispute':'Investigate dispute with AR owner before further collection.',
                    'request_info':'Review requested documents and respond manually.',
                    'other':'Review customer reply and decide next action.'}[body.intent]
            resolution={'intent':body.intent,'promise_date':body.promise_date,'promise_amount':body.promise_amount,
                'evidence_quote':body.evidence_quote,'reviewed_by':'owner_token','reviewed_at':datetime.now(timezone.utc).isoformat(),
                'invoice_payment_updated':False,'automatic_email_scheduled':False}
            await self.store.rpc('ca_mail_resolve',{'p_reply_id':reply_id,'p_resolution':resolution,
                'p_due_date':due.isoformat(),'p_task':task})
            return await self.activity(run_id)

    async def close(self):await self.provider.close()
