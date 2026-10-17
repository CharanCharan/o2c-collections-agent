"""Explicit demo-clock due checks; no always-on scheduler or model calls."""
import asyncio
from datetime import date,timedelta

from fastapi import HTTPException

from ..storage import StorageError


class FollowupService:
    def __init__(self,store,agent):
        self.store,self.agent=store,agent

    async def clock(self,actor,value=None):
        return await self.store.rpc('ca_demo_clock',{'p_session_key':actor,'p_date':value.isoformat() if value else None})

    async def job(self,actor,ident=None):
        return await self.store.rpc('ca_due_job',{'p_action':'get','p_session_key':actor,'p_id':ident})

    async def start(self,actor,ident):
        clock=await self.clock(actor);today=date.fromisoformat(clock['demo_date'])
        cases=await self.store.rpc('ca_cases_list',{'p_session_key':actor});ids=[]
        for c in cases:
            w=c.get('workflow') or {};p=w.get('promise') or w.get('scenario',{}).get('prior_promise') or {}
            promised=p.get('promise_date') or p.get('date')
            if promised and today>=date.fromisoformat(promised)+timedelta(days=1):ids.append(c['id'])
        return await self.store.rpc('ca_due_job',{'p_action':'create','p_session_key':actor,'p_id':ident,
            'p_data':{'as_of_date':clock['demo_date'],'case_ids':ids}})

    async def resume(self,actor,ident):
        return await self.store.rpc('ca_due_job',{'p_action':'resume','p_session_key':actor,'p_id':ident})

    async def run(self,actor,ident):
        progress={'processed':0,'total':0,'auto_case_ids':[],'outcomes':[]}
        async def save(status='running'):
            await self.store.rpc('ca_due_job',{'p_action':'update','p_session_key':actor,'p_id':ident,
                'p_data':{'status':status,'progress':progress}})
        try:
            job=await self.job(actor,ident);progress.update(job['progress']);ids=job['case_ids'];progress['total']=len(ids)
            for cid in ids:
                c=await self.agent.case(actor,cid);w=c['workflow']
                p=w.get('promise') or w.get('scenario',{}).get('prior_promise') or {}
                promised=p.get('promise_date') or p.get('date')
                key='due:'+str(w.get('promise_event_key') or 'seed:'+str(promised))
                auto=progress['auto_case_ids']
                if w['mode']=='autopilot' and not w.get('followup') and cid not in auto and len(auto)<3:auto.append(cid)
                progress['current_invoice']=c['invoice_id'];await save()
                # invoke deduplicates this exact promise event, including waiting approvals.
                c=await self.agent.invoke(actor,cid,event='due',event_key=key,mode=w['mode'],allow_auto_send=cid in auto)
                outcome={'case_id':cid,'invoice_id':c['invoice_id'],'status':c['workflow']['status']}
                progress['outcomes']=[x for x in progress['outcomes'] if x['case_id']!=cid]+[outcome]
                progress['processed']=len(progress['outcomes']);await save()
            await save('completed')
        except asyncio.CancelledError:
            try:await save('interrupted')
            except StorageError:pass
            raise
        except Exception:
            progress['error']='Due check interrupted. Saved case checkpoints remain; resume this check.'
            try:await save('interrupted')
            except StorageError:pass
