"""Session-only conversation foundation; no transport or financial mutation.

A draft copy is NOT a sent email. Typed customer text is NOT a Resend receipt.
Replies are committed before classification; replay never repeats a model call.
Graph-enabled cases automatically invoke their durable LangGraph thread on reply.
"""
import asyncio

from fastapi import HTTPException
from .language import facts_for


class CaseService:
    def __init__(self,store,language):
        self.store,self.language=store,language
        self.lock=asyncio.Lock()
        self.agent=None

    async def list(self,actor):
        return await self.store.rpc('ca_cases_list',{'p_session_key':actor})

    async def open(self,actor,run_id,invoice_id):
        return await self.store.rpc('ca_case_open',{'p_session_key':actor,'p_run_id':run_id,'p_invoice_id':invoice_id})

    async def reply(self,actor,case_id,request_id,text):
        text=text.strip()
        if not text or any(ord(c)<32 and c not in '\n\t' for c in text):
            raise HTTPException(422,'Enter a plain-text demo reply (1–4000 characters).')
        # One POC worker. SQL reservations also prevent duplicates across restarts.
        async with self.lock:
            saved=await self.store.rpc('ca_case_reply',{'p_session_key':actor,'p_case_id':case_id,
                'p_request_id':request_id,'p_text':text})
            if not saved['recorded']:
                return saved
            case=saved['case']
            if self.agent and case.get('workflow'):
                case=await self.agent.invoke(actor,case_id,event='reply',event_key=request_id,mode=case['workflow']['mode'])
                return {'recorded':True,'case':case}
            review=await self.language.classify(facts_for(case['snapshot']['invoice'],case['snapshot']),text)
            review['input_channel']='simulated_customer_reply'
            review['financial_state_updated']=False
            return await self.store.rpc('ca_case_review',{'p_session_key':actor,'p_case_id':case_id,
                'p_request_id':request_id,'p_review':review})
