"""Local M5 helper: expose only signed callback forwarding on port8001.

Keep the main app on127.0.0.1:8000. Forward8001 in VS Code for Resend;
never forward the main app before M6. No database/service startup here.
"""
from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response


def create_gateway(transport=None):
    client=httpx.AsyncClient(base_url='http://127.0.0.1:8000',timeout=90,
        trust_env=False,follow_redirects=False,transport=transport)
    @asynccontextmanager
    async def lifespan(app):
        yield
        await client.aclose()
    app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None,lifespan=lifespan)
    @app.post('/api/webhooks/resend')
    async def forward(request: Request):
        raw=bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw)>65536:raise HTTPException(413,'Webhook exceeds POC size limit.')
        headers={name:request.headers.get(name,'') for name in ['svix-id','svix-timestamp','svix-signature']}
        # Reject obviously unsigned requests before contacting the main app.
        if not all(headers.values()):raise HTTPException(401,'Signature headers required.')
        headers['Content-Type']='application/json'
        try:
            response=await client.post('/api/webhooks/resend',content=bytes(raw),headers=headers)
        except httpx.HTTPError:
            raise HTTPException(503,'Local application unavailable; retry later.') from None
        return Response(content=response.content,status_code=response.status_code,media_type='application/json')
    return app


app=create_gateway()
