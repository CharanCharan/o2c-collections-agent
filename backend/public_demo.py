"""Bounded public POC: signed sessions, run ownership, owner role and SQL quotas.

A cookie is a browser session, not a verified person. Global SQL caps also apply.
"""
import base64
import copy
import hashlib
import hmac
import json
import os
import re
import secrets
import time
from contextvars import ContextVar
from dataclasses import dataclass, field

from fastapi import HTTPException
from .llm.errors import LanguageError
from .storage import StorageError

ACTOR=ContextVar('collections_demo_actor',default=('webhook',False))
COOKIE='collections_session'
PRIVATE_STAGES={'email_approval','email_send','email_delivery','email_reply','followup_scheduled'}


@dataclass(frozen=True)
class PublicConfig:
    enabled: bool = False
    secret: str = field(default='',repr=False)
    owner_token: str = field(default='',repr=False)
    cloud: bool = False
    invalid: bool = False

    @classmethod
    def from_env(cls):
        value=os.getenv('PUBLIC_DEMO','false').strip().lower()
        return cls(enabled=value=='true',secret=os.getenv('DEMO_SESSION_SECRET','').strip(),
            owner_token=os.getenv('EMAIL_OWNER_TOKEN','').strip(),cloud=os.getenv('RENDER','').lower()=='true',
            invalid=value not in {'true','false'})

    def check(self):
        if self.invalid or (self.cloud and not self.enabled):
            raise HTTPException(503,'Cloud deployment requires PUBLIC_DEMO=true. Check server environment.')
        if self.enabled and (len(self.secret)<32 or len(self.owner_token)<32):
            raise HTTPException(503,'Public demo requires separate private session secret and owner token, each32+characters.')
        if self.enabled and hmac.compare_digest(self.secret,self.owner_token):
            raise HTTPException(503,'Use different session and owner secrets.')


class PublicAccess:
    def __init__(self,config,store):self.config,self.store=config,store

    def owner(self,token):
        return bool(token and self.config.owner_token and hmac.compare_digest(token.encode(),self.config.owner_token.encode()))

    def encode(self,session):
        body=base64.urlsafe_b64encode(json.dumps(session,separators=(',',':')).encode()).decode().rstrip('=')
        signature=hmac.new(self.config.secret.encode(),body.encode(),hashlib.sha256).hexdigest()
        return body+'.'+signature

    def decode(self,value):
        try:
            body,signature=value.split('.')
            expected=hmac.new(self.config.secret.encode(),body.encode(),hashlib.sha256).hexdigest()
            if not hmac.compare_digest(signature,expected):raise ValueError
            result=json.loads(base64.urlsafe_b64decode(body+'='*(-len(body)%4)))
            if not re.fullmatch(r'[0-9a-f]{64}',result['id']) or not 0<=time.time()-result['issued']<7*86400:raise ValueError
            if type(result.get('owner_until',0)) not in {int,float}:raise ValueError
            return result
        except (ValueError,TypeError,KeyError,AttributeError):return None

    def session(self,request):
        return self.decode(request.cookies.get(COOKIE,'')) or {'id':secrets.token_hex(32),'issued':int(time.time()),'owner_until':0}

    def set_cookie(self,response,session):
        response.set_cookie(COOKIE,self.encode(session),max_age=7*86400,secure=True,httponly=True,samesite='lax',path='/')

    def actor(self,request):
        session=request.state.demo_session
        return hashlib.sha256(session['id'].encode()).hexdigest(),request.state.demo_owner

    async def allowed(self,request,run_id):
        if not self.config.enabled:return
        if request.state.demo_owner:return
        if self.store is None:raise StorageError("Configure Supabase before using the public demo.")
        actor,_=self.actor(request)
        if not await self.store.rpc('ca_public_allowed',{'p_run_id':str(run_id),'p_session_key':actor}):
            raise HTTPException(404,'Run not found in this browser session.')

    def require_owner(self,request):
        if self.config.enabled and not request.state.demo_owner:
            raise HTTPException(401,'Owner login required for private email activity.')

    def event(self,request,event):
        return not self.config.enabled or request.state.demo_owner or event.get('stage') not in PRIVATE_STAGES

    def sanitize(self,request,value):
        if not self.config.enabled or request.state.demo_owner:return value
        result=copy.deepcopy(value)
        # Domain results have synthetic data only; private post-run email events do not.
        run=result.get('run',result)
        if isinstance(run,dict) and 'events' in run:
            run['events']=[event for event in run['events'] if self.event(request,event)]
        return result

    async def reserve_llm(self,llm_config):
        if not llm_config.free_only or llm_config.provider!='groq' or llm_config.error():
            raise LanguageError('Public demo requires valid free-only Groq routing; no model request made.')
        actor,owner=ACTOR.get()
        try:
            allowed=await self.store.rpc('ca_public_reserve',{'p_actor':actor,'p_kind':'llm','p_owner':owner})
        except StorageError:
            raise LanguageError('Durable demo budget unavailable; no model request made.') from None
        if not allowed:raise LanguageError('Daily demo LLM quota reached; template/manual-review fallback, no model request made.')
