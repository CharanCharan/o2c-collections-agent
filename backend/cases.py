"""Session-only conversation foundation; no transport or financial mutation.

A draft copy is NOT a sent email. Typed customer text is NOT a Resend receipt.
Replies are committed before classification; replay never repeats a model call.
Graph-enabled cases automatically invoke their durable LangGraph thread on reply.
"""
import asyncio
import hashlib

from fastapi import HTTPException
from .language import facts_for, LanguageError
from .storage import StorageError


class CaseService:
    def __init__(self,store,language):
        self.store,self.language=store,language
        self.lock=asyncio.Lock()
        self.agent=None

    async def list(self,actor):
        return await self.store.rpc('ca_cases_list',{'p_session_key':actor})

    async def open(self,actor,run_id,invoice_id):
        return await self.store.rpc('ca_case_open',{'p_session_key':actor,'p_run_id':run_id,'p_invoice_id':invoice_id})

    async def redraft(self, actor, case_id, request_id, instructions):
        instructions = instructions.strip()
        if any(ord(c) < 32 and c not in '\n\t' for c in instructions):
            raise HTTPException(422, 'Use plain text for draft preferences.')
        try:
            await self.store.rpc('ca_ai_draft_health')
        except StorageError:
            raise HTTPException(503, 'Apply sql/015_ai_draft.sql after SQL014 to enable Draft with AI.') from None
        # Serialize with this case's graph approvals; SQL also guards send/reply races.
        async with self.agent.locks[case_id]:
            args = {'p_session_key': actor, 'p_case_id': case_id, 'p_request_id': request_id,
                    'p_instructions_hash': hashlib.sha256(instructions.encode()).hexdigest()}
            claimed = await self.store.rpc('ca_ai_draft', {'p_action': 'claim', **args})
            if not claimed['recorded']:
                return claimed
            case = claimed['case']
            audit = {'tool': 'draft_reminder', **self.language.identity(), 'api_attempted': False,
                     'generation_trigger': 'visitor_requested', 'preferences_sha256': args['p_instructions_hash']}
            try:
                draft, result_audit = await self.language.redraft(case['snapshot']['invoice'], case['snapshot'], instructions)
            except LanguageError as exc:
                audit.update(getattr(exc, 'audit', {}))
                result = await self.store.rpc('ca_ai_draft', {'p_action': 'fail', **args,
                    'p_audit': audit, 'p_reason': str(exc)})
            else:
                audit.update(result_audit)
                result = await self.store.rpc('ca_ai_draft', {'p_action': 'complete', **args,
                    'p_draft': draft, 'p_audit': audit})
            self.agent.publish_case(result['case'])
            return result

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
