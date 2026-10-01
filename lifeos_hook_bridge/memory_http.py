# ABOUTME: Relays native memory HTTP reads to a fixed authenticated local dashboard.
# ABOUTME: Uses only incoming session credentials and refuses redirects or raw fallback.
from __future__ import annotations

import ipaddress
import hashlib
import http.client
import json
from pathlib import Path
import re
from typing import TYPE_CHECKING
import urllib.error
import urllib.parse
import urllib.request

if TYPE_CHECKING:
    from .memory_service import MemoryConfiguration

VIEWS = frozenset({'snapshot','state','health','runs'})
RESPONSE_LIMIT = 3 * 1024 * 1024
SESSION_COOKIES = frozenset(prefix+name for prefix in ('','__Host-','__Secure-')
    for name in ('hermes_session_at','hermes_session_rt','hermes_session_provider'))


def installation_binding(configuration: dict, path: Path) -> str:
    identity={'root':str(Path(configuration['root']).absolute()),
              'profile':str(path.parent.absolute()),'principal':configuration['principal']}
    return hashlib.sha256(json.dumps(identity,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def dashboard_base(value: object) -> str:
    return _dashboard_url(value,loopback=True)


def _dashboard_url(value: object, *, loopback: bool) -> str:
    if not isinstance(value,str) or len(value)>2048:
        raise ValueError('PULSE requires a fixed local dashboard URL')
    url=urllib.parse.urlsplit(value)
    if (url.scheme not in {'http','https'} or url.username or url.password or url.query or url.fragment
            or not url.hostname or not re.fullmatch(r'(?:/[A-Za-z0-9_-]+)*/?',url.path)):
        raise ValueError('PULSE requires a fixed local dashboard URL')
    try:
        address=ipaddress.ip_address(url.hostname)
    except ValueError:
        if loopback or not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?',url.hostname):
            raise ValueError('PULSE requires a supported dashboard host') from None
    else:
        if loopback and not address.is_loopback:
            raise ValueError('PULSE requires a loopback dashboard host')
    if (loopback and url.port is None) or url.port==0:
        raise ValueError('PULSE requires a valid dashboard port')
    return value.rstrip('/')


def _response(status: int, body: object, cookies: list[str] | None = None) -> dict:
    headers=[['content-type','application/json'],['cache-control','no-store']]
    headers.extend(['set-cookie',cookie] for cookie in cookies or [])
    return {'status':status,'headers':headers,'body':json.dumps(body)}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def relay(configuration: MemoryConfiguration, arguments: dict) -> dict:
    if (set(arguments)!={'view','authorization','cookie'}
            or not isinstance(arguments['view'],str) or arguments['view'] not in VIEWS):
        return _response(400,{'error':'Choose a supported native memory view'})
    credentials={}
    for key in ('authorization','cookie'):
        value=arguments[key]
        if not isinstance(value,str) or len(value)>16384 or '\r' in value or '\n' in value:
            return _response(400,{'error':'Invalid memory request credentials'})
        if key=='authorization' and value:
            if not re.fullmatch(r'Bearer [^\s]+',value):
                return _response(401,{'error':'An authenticated Hermes session is required'})
            credentials['Authorization']=value
        if key=='cookie':
            selected=[part.strip() for part in value.split(';') if '=' in part
                      and part.strip().split('=',1)[0] in SESSION_COOKIES]
            if selected:
                credentials['Cookie']='; '.join(selected)
    if not credentials:
        return _response(401,{'error':'An authenticated Hermes session is required'})
    try:
        config=configuration.load()
        settings=config.get('pulse_http')
        if (not isinstance(settings,dict) or 'dashboard_base_url' not in settings
                or not set(settings)<={'dashboard_base_url','dashboard_browser_url'}):
            raise ValueError('PULSE HTTP setup is unavailable')
        base=dashboard_base(settings['dashboard_base_url'])
        browser=(_dashboard_url(settings['dashboard_browser_url'],loopback=False)
                 if 'dashboard_browser_url' in settings else None)
        request=urllib.request.Request(base+'/api/plugins/lifeos-hook-bridge/memory/pulse/'+arguments['view'],
                                      headers=credentials,method='GET')
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
        try:
            response=opener.open(request,timeout=8)
        except urllib.error.HTTPError as error:
            response=error
        with response:
            status=response.status
            if status not in (200,400,401,403):
                return _response(503,{'error':'Authenticated memory is unavailable'})
            if (status==200 and response.headers.get('x-lifeos-memory-installation')
                    !=installation_binding(config,configuration.path)):
                raise ValueError('The authenticated response belongs to another installation')
            if response.headers.get_content_type()!='application/json':
                raise ValueError('Invalid authenticated memory response')
            lengths=response.headers.get_all('content-length',[])
            if lengths and (len(lengths)!=1 or not re.fullmatch(r'[0-9]{1,10}',lengths[0])
                            or int(lengths[0])>RESPONSE_LIMIT):
                raise ValueError('Invalid authenticated memory response length')
            payload=response.read(RESPONSE_LIMIT+1)
            if len(payload)>RESPONSE_LIMIT or (lengths and len(payload)!=int(lengths[0])):
                raise ValueError('Authenticated memory response exceeds its limit')
            body=json.loads(payload)
            if status==200 and (not isinstance(body,(dict,list)) and body is not None):
                raise ValueError('Invalid authenticated memory response')
            if status==401 and isinstance(body,dict):
                body.pop('login_url',None)
                if browser:
                    body['login_url']=browser+'/login'
            return _response(status,body,response.headers.get_all('set-cookie',[]))
    except (ValueError,OSError,RuntimeError,urllib.error.URLError,http.client.HTTPException):
        return _response(503,{'error':'Authenticated memory is unavailable'})
