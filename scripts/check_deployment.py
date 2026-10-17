"""Read-only public checks. Usage: python -m scripts.check_deployment https://APP.onrender.com"""
import http.cookiejar
import json
import sys
from urllib.error import HTTPError,URLError
from urllib.parse import urlsplit
from urllib.request import HTTPCookieProcessor,Request,build_opener


def check(origin):
    parsed=urlsplit(origin)
    if parsed.scheme!='https' or not parsed.hostname or parsed.path not in {'','/'} or parsed.query or parsed.fragment or parsed.username:
        raise ValueError('Provide only the HTTPS website origin, without a path, query or credentials.')
    base=origin.rstrip('/')
    opener=build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))
    def get(path):
        with opener.open(Request(base+path,headers={'Accept':'application/json'}),timeout=90) as response:
            return json.load(response)
    assert get('/livez')['status']=='alive','Liveness failed.'
    health=get('/api/health')
    assert health.get('status')=='ok' and health.get('public_demo',{}).get('enabled'),'M6 public health not ready.'
    assert get('/api/webhooks/resend')['status']=='reachable','Webhook URL not reachable.'
    assert get('/api/runs')['runs']==[],'Fresh visitor unexpectedly sees saved runs. Do not share this deployment.'
    try:
        get('/api/runs/00000000-0000-0000-0000-000000000000/email')
    except HTTPError as error:
        assert error.code==401,'Private email access did not reject visitor correctly.'
    else:raise AssertionError('Private email route exposed to visitor.')
    print('PASS: cloud health, public-mode configuration, webhook reachability, fresh-session history isolation and private email gate.')
    print('No run, LLM call or email was triggered. Next verify Start in a private browser, then an owner-approved email/reply.')


if __name__=='__main__':
    try:
        if len(sys.argv)!=2:raise ValueError('Usage: python -m scripts.check_deployment https://YOUR-APP.onrender.com')
        check(sys.argv[1])
    except (AssertionError,ValueError,KeyError,URLError,TimeoutError) as error:
        print('CHECK FAILED:',str(error))
        print('For a sleeping free service, open the website, wait for it to wake, then retry. Check Render logs and M6 setup.')
        sys.exit(1)
