"""Real PostgreSQL RPCs + fixed mock Resend contracts. No actual mail/network."""
import base64
import hashlib
import hmac
import json
import time
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.language import LanguageService
from backend.mail.config import MailConfig
from backend.mail.signatures import verify
from backend.main import create_app
from tests.test_milestone_2 import finish

TOKEN='owner-test-only-token-12345678901234567890'
SECRET='whsec_'+base64.b64encode(b'test-secret-32-bytes-not-real-xxxx').decode()
CONFIG=MailConfig(enabled=True,key='resend-test-only',owner_token=TOKEN,webhook_secret=SECRET,
    recipient='owner@example.com',receiving_domain='demo123.resend.app')
AUTH={'X-Collections-Owner':TOKEN}
INVOICE='INV-10287'


def signed(event,ident=None,stamp=None):
    raw=json.dumps(event,separators=(',',':')).encode()
    stamp=str(int(time.time()) if stamp is None else stamp);ident=ident or 'msg_'+str(uuid4())
    digest=base64.b64encode(hmac.new(base64.b64decode(SECRET[6:]),ident.encode()+b'.'+stamp.encode()+b'.'+raw,hashlib.sha256).digest()).decode()
    return raw,{'svix-id':ident,'svix-timestamp':stamp,'svix-signature':'v1,'+digest}


class ResendMock:
    def __init__(self):
        self.sent=[];self.gets=[];self.fail=False;self.originals={};self.inbound={}
    def handler(self,request):
        assert str(request.url).startswith('https://api.resend.com/')
        assert request.headers['authorization']=='Bearer resend-test-only'
        if request.method=='POST':
            assert str(request.url)=='https://api.resend.com/emails'
            body=json.loads(request.content);key=request.headers['idempotency-key']
            assert body['to']==['owner@example.com'] and body['from']=='onboarding@resend.dev'
            assert body['subject'].startswith('[O2C DEMO]') and 'SYNTHETIC' in body['text']
            self.sent.append({'key':key,'body':body})
            if self.fail:raise httpx.ReadTimeout('private resend-test-only error',request=request)
            if key not in self.originals:self.originals[key]=str(uuid4())
            return httpx.Response(200,json={'id':self.originals[key]})
        self.gets.append(str(request.url))
        if '/receiving/' in str(request.url):return httpx.Response(200,json=self.inbound[request.url.path.split('/')[-1]])
        return httpx.Response(200,json={'id':request.url.path.split('/')[-1],'message_id':'<original@resend.dev>'})


def client_for(store_factory,provider,config=CONFIG,language=None):
    return TestClient(create_app(store_factory(),language=language or LanguageService(),mail_config=config,
        mail_transport=httpx.MockTransport(provider.handler)))


def send(c,rid,**kwargs):
    return c.post(f'/api/runs/{rid}/invoices/{INVOICE}/send-email',json={'confirm_reviewed':True},headers=AUTH,**kwargs)


def receive(c,provider,message,text='We paid this invoice yesterday.',change=None,event_id=None):
    ident=str(uuid4());payload={'id':ident,'from':'Owner <owner@example.com>',
        'to':[message['reply_to']],'headers':{'in-reply-to':'<original@resend.dev>'},
        'authentication':{'dmarc':'pass'},'text':text,'message_id':'<reply@example.com>'}
    payload.update(change or {});provider.inbound[ident]=payload
    event={'type':'email.received','data':{'email_id':ident,'to':[message['reply_to']]}}
    raw,headers=signed(event,ident=event_id)
    return c.post('/api/webhooks/resend',content=raw,headers=headers),ident,raw,headers


def test_disabled_email_owner_auth_confirmation_and_recipient_injection(store_factory):
    provider=ResendMock()
    with client_for(store_factory,provider,replace(CONFIG,enabled=False)) as c:
        run,_=finish(c);rid=run['run_id']
        assert send(c,rid).status_code==409
        assert not provider.sent
    with client_for(store_factory,provider) as c:
        run,_=finish(c);path=f"/api/runs/{run['run_id']}/invoices/{INVOICE}/send-email"
        assert c.post(path,json={'confirm_reviewed':True}).status_code==401
        assert c.post(path,json={'confirm_reviewed':False},headers=AUTH).status_code==422
        assert c.post(path,json={'confirm_reviewed':'true'},headers=AUTH).status_code==422
        assert c.post(path,json={'confirm_reviewed':True,'to':'stranger@example.com'},headers=AUTH).status_code==422
        assert not provider.sent
        health=c.get('/api/health').json()['email']
        assert health['ready'] and 'resend-test-only' not in json.dumps(health) and TOKEN not in json.dumps(health)
        assert 'owner@example.com' not in json.dumps(health)
        assert c.get('/api/email/owner-config',headers=AUTH).json()['recipient']=='owner@example.com'


def test_acceptance_dedup_delivery_and_restart_history(store_factory):
    provider=ResendMock()
    with client_for(store_factory,provider) as c:
        run,_=finish(c);rid=run['run_id'];before=run['result']
        response=send(c,rid);assert response.status_code==200,response.text
        message=response.json()['mail']['messages'][0]
        assert message['state']=='accepted' and len(provider.sent)==1
        assert response.json()['run']['result']==before
        assert not response.json()['mail']['delivery_events']
        assert send(c,rid).status_code==200 and len(provider.sent)==1
        data={'type':'email.delivered','data':{'email_id':message['provider_id']},'created_at':'2026-10-17T12:00:00Z'}
        raw,headers=signed(data)
        assert c.post('/api/webhooks/resend',content=raw,headers=headers).json()['recorded']
        assert not c.post('/api/webhooks/resend',content=raw,headers=headers).json()['recorded']
    with client_for(store_factory,provider) as fresh:
        state=fresh.get(f'/api/runs/{rid}/email').json()
        assert len(state['mail']['messages'])==1 and len(state['mail']['delivery_events'])==1
        assert state['run']['result']==before
        assert send(fresh,rid).status_code==200 and len(provider.sent)==1


def test_uncertain_attempt_explicit_retry_same_payload_and_20h_cutoff(store_factory,database):
    provider=ResendMock();provider.fail=True
    with client_for(store_factory,provider) as c:
        run,_=finish(c);rid=run['run_id']
        response=send(c,rid);assert response.status_code==200,response.text
        message=response.json()['mail']['messages'][0]
        assert message['state']=='uncertain' and len(provider.sent)==1
        assert 'resend-test-only' not in json.dumps(response.json())
        provider.fail=False
        assert send(c,rid).json()['mail']['messages'][0]['state']=='accepted'
        assert provider.sent[0]==provider.sent[1]
        run,_=finish(c);rid=run['run_id'];provider.fail=True
        message=send(c,rid).json()['mail']['messages'][0]
        database.sql("update ca_mail_messages set created_at=now()-interval '21 hours' where id=$1",[message['id']])
        count=len(provider.sent)
        assert send(c,rid).status_code==409 and len(provider.sent)==count


@pytest.mark.parametrize('invoice',['INV-10317','INV-unknown'])
def test_no_email_for_ineligible_invoice(store_factory,invoice):
    provider=ResendMock()
    with client_for(store_factory,provider) as c:
        run,_=finish(c)
        response=c.post(f"/api/runs/{run['run_id']}/invoices/{invoice}/send-email",json={'confirm_reviewed':True},headers=AUTH)
        assert response.status_code==409 and not provider.sent


def test_real_reply_manual_review_paid_resolution_dedup_and_no_payment_mutation(store_factory):
    provider=ResendMock()
    with client_for(store_factory,provider) as c:
        run,_=finish(c);rid=run['run_id'];original=run['result']
        message=send(c,rid).json()['mail']['messages'][0]
        response,ident,raw,headers=receive(c,provider,message)
        assert response.status_code==200,response.text
        count=len(provider.gets)
        assert not c.post('/api/webhooks/resend',content=raw,headers=headers).json()['recorded']
        assert len(provider.gets)==count
        state=c.get(f'/api/runs/{rid}/email').json()
        review=state['mail']['replies'][0]['review']
        assert review['thread_verified'] and review['simulated_input'] is False
        assert review['classification'] is None and review['status']=='manual_review'
        path=f'/api/runs/{rid}/replies/{ident}/resolve'
        assert c.post(path,json={'intent':'payment_claim'}).status_code==401
        response=c.post(path,json={'intent':'payment_claim'},headers=AUTH)
        assert response.status_code==200,response.text
        state=response.json();assert len(state['mail']['followups'])==1
        assert 'Reconcile' in state['mail']['followups'][0]['task']
        assert state['run']['result']==original
        events=len(state['run']['events'])
        repeated=c.post(path,json={'intent':'payment_claim'},headers=AUTH).json()
        assert len(repeated['mail']['followups'])==1 and len(repeated['run']['events'])==events


@pytest.mark.parametrize('change',[
    {'from':'attacker@example.com'}, {'headers':{'in-reply-to':'<wrong@thread.com>'}},
    {'authentication':{'dmarc':'fail'}}, {'to':['other@demo123.resend.app']},
])
def test_mismatched_replies_quarantined_without_llm(store_factory,change):
    from tests.test_llm_providers import mock_groq
    language,requests=mock_groq();provider=ResendMock()
    with client_for(store_factory,provider,language=language) as c:
        run,_=finish(c);rid=run['run_id'];count=len(requests)
        message=send(c,rid).json()['mail']['messages'][0]
        response,_,_,_=receive(c,provider,message,change=change)
        assert response.status_code==200,response.text
        reply=c.get(f'/api/runs/{rid}/email').json()['mail']['replies'][0]
        assert reply['review']['status']=='quarantined' and not reply['review']['audit']['api_attempted']
        assert len(requests)==count


def test_verified_reply_groq_classifies_but_requires_owner_resolution(store_factory):
    from tests.test_llm_providers import mock_groq
    language,requests=mock_groq();provider=ResendMock()
    with client_for(store_factory,provider,language=language) as c:
        run,_=finish(c);rid=run['run_id'];count=len(requests)
        message=send(c,rid).json()['mail']['messages'][0]
        response,_,_,_=receive(c,provider,message)
        assert response.status_code==200,response.text
        state=c.get(f'/api/runs/{rid}/email').json()
        reply=state['mail']['replies'][0]
        assert reply['review']['classification']['intent']=='payment_claim' and reply['resolution'] is None
        assert not state['mail']['followups'] and len(requests)==count+1


def test_promise_evidence_followup_date_and_dispute_hold(store_factory):
    provider=ResendMock()
    with client_for(store_factory,provider) as c:
        run,_=finish(c);rid=run['run_id']
        message=send(c,rid).json()['mail']['messages'][0]
        future=(datetime.now(timezone.utc).date()+timedelta(days=10)).isoformat()
        text=f'We will pay 1000.00 on {future}.'
        _,ident,_,_=receive(c,provider,message,text=text)
        route=f'/api/runs/{rid}/replies/{ident}/resolve'
        body={'intent':'promise_to_pay','promise_date':future,'promise_amount':'1000.00','evidence_quote':text}
        assert c.post(route,json={**body,'promise_amount':'999999.00'},headers=AUTH).status_code==422
        response=c.post(route,json=body,headers=AUTH);assert response.status_code==200,response.text
        task=response.json()['mail']['followups'][0]
        assert task['due_date']==(datetime.now(timezone.utc).date()+timedelta(days=11)).isoformat()
        _,dispute,_,_=receive(c,provider,message,text='We dispute this invoice.')
        assert c.post(f'/api/runs/{rid}/replies/{dispute}/resolve',json={'intent':'dispute'},headers=AUTH).status_code==200
        second,_=finish(c)
        assert send(c,second['run_id']).status_code==409


def test_signed_webhook_tamper_expiry_unknown_and_size(store_factory):
    provider=ResendMock()
    with client_for(store_factory,provider) as c:
        data={'type':'email.received','data':{'email_id':str(uuid4()),'to':['unknown@demo123.resend.app']}}
        raw,headers=signed(data)
        assert c.post('/api/webhooks/resend',content=raw+b' ',headers=headers).status_code==401
        expired,eh=signed(data,stamp=int(time.time())-301)
        assert c.post('/api/webhooks/resend',content=expired,headers=eh).status_code==401
        assert c.post('/api/webhooks/resend',content=raw,headers=headers).json()['ignored']
        assert not provider.gets
        assert c.post('/api/webhooks/resend',content=b'x'*65537,headers=headers).status_code==413


def test_svix_official_reference_vector():
    secret='whsec_plJ3nmyCDGBKInavdOK15jsl'
    assert verify(b'{"event_type":"ping","data":{"success":true}}',
        {'svix-id':'msg_loFOjxBNrRLzqYUf','svix-timestamp':'1731705121',
         'svix-signature':'v1,rAvfW3dJ/X/qxhsaXPOyyCGmRKsaKWcsNccKXlIktD0='},secret,now=1731705121)=='msg_loFOjxBNrRLzqYUf'


def test_database_daily_cap_and_anonymous_permissions(store_factory,database):
    provider=ResendMock()
    with client_for(store_factory,provider) as c:
        for _ in range(10):
            run,_=finish(c)
            assert send(c,run['run_id']).status_code==200
        run,_=finish(c)
        assert send(c,run['run_id']).status_code==429 and len(provider.sent)==10
    database.sql('set role anon')
    try:
        assert 'error' in database.call(command='sql',sql='select ca_mail_state(gen_random_uuid())')
        assert 'error' in database.call(command='sql',sql='select * from ca_mail_messages')
    finally:database.sql('reset role')


def test_webhook_gateway_exposes_only_callback_and_preserves_signed_bytes():
    from backend.webhook_gateway import create_gateway
    requests=[]
    def handler(request):
        requests.append(request)
        assert str(request.url)=='http://127.0.0.1:8000/api/webhooks/resend'
        assert request.content==b'{ "raw": true }' and request.headers['svix-signature']=='unchanged'
        return httpx.Response(401,json={'detail':'signature invalid'})
    with TestClient(create_gateway(httpx.MockTransport(handler))) as c:
        assert c.get('/').status_code==404 and c.get('/docs').status_code==404
        assert c.post('/api/runs').status_code==404 and c.get('/api/health').status_code==404
        assert c.post('/api/webhooks/resend',content=b'{}').status_code==401
        assert not requests
        response=c.post('/api/webhooks/resend',content=b'{ "raw": true }',
            headers={'svix-id':'test','svix-timestamp':'123','svix-signature':'unchanged'})
        assert response.status_code==401 and len(requests)==1


def test_reviewed_dispute_also_blocks_retry_of_an_earlier_uncertain_intent(store_factory):
    provider=ResendMock()
    with client_for(store_factory,provider) as c:
        first,_=finish(c)
        message=send(c,first['run_id']).json()['mail']['messages'][0]
        second,_=finish(c);provider.fail=True
        assert send(c,second['run_id']).json()['mail']['messages'][0]['state']=='uncertain'
        provider.fail=False
        _,ident,_,_=receive(c,provider,message,text='We dispute this invoice.')
        assert c.post(f"/api/runs/{first['run_id']}/replies/{ident}/resolve",json={'intent':'dispute'},headers=AUTH).status_code==200
        calls=len(provider.sent)
        assert send(c,second['run_id']).status_code==409 and len(provider.sent)==calls
