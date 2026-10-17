"""Fixed HTTPS endpoints; no retries, redirects, SDK or credentials in evidence."""
import httpx
from fastapi import HTTPException
from uuid import UUID


class ResendProvider:
    def __init__(self,config,transport=None):
        self.config=config;self.transport=transport;self.client=None

    async def request(self,method,path,body=None,headers=None):
        try:
            if self.client is None:
                self.client=httpx.AsyncClient(base_url='https://api.resend.com/',
                    headers={'Authorization':'Bearer '+self.config.key},timeout=20,
                    follow_redirects=False,transport=self.transport)
            response=await self.client.request(method,path,json=body,headers=headers)
            if not 200<=response.status_code<300:
                raise HTTPException(502,f'Resend HTTP{response.status_code}; details withheld. No automatic retry.')
            data=response.json()
            if not isinstance(data,dict):raise ValueError
            return data
        except (httpx.HTTPError,ValueError,ImportError):
            raise HTTPException(502,'Resend connection/response failed. Acceptance may be unknown; no automatic retry.') from None

    async def send(self,job):
        data=await self.request('POST','emails',job['payload'],{'Idempotency-Key':'collections-'+job['id']})
        try: return str(UUID(data['id']))
        except (KeyError,TypeError,ValueError):
            raise HTTPException(502,'Resend did not return a valid email ID; acceptance unknown.') from None

    async def received(self,email_id):
        return await self.request('GET','emails/receiving/'+str(UUID(email_id))+'?html_format=cid')

    async def sent(self,email_id):
        return await self.request('GET','emails/'+str(UUID(email_id)))

    async def close(self):
        if self.client:await self.client.aclose()
