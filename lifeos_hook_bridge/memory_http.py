# ABOUTME: Relays native memory HTTP requests to a fixed authenticated local dashboard.
# ABOUTME: Uses only incoming session credentials and refuses redirects or raw fallback.
from __future__ import annotations

import ipaddress
import hashlib
import http.client
import json
import math
from pathlib import Path
import re
from typing import TYPE_CHECKING
import urllib.error
import urllib.parse
import urllib.request

if TYPE_CHECKING:
    from .memory_service import MemoryConfiguration

VIEWS = frozenset({'snapshot','state','health','runs','graph', 'telos_freshness', 'telos_stale',
                  'telos_freshness_summary', 'context_freshness', 'context_freshness_summary', 'telos_health'})
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
    source_view = arguments.get('view') in ('wiki', 'knowledge', 'hypotheses', 'upgrades', 'tab_freshness', 'life', 'telos_file')
    review = arguments.get('view') in ('hypothesis_review','upgrades_review')
    edit = arguments.get('view') == 'telos_file_edit'
    expected = {'view','authorization','cookie'} | ({'target'} if source_view else set()) | (
        {'target','note','request_id'} if review else {'name','content','reference','request_id'} if edit else set())
    if (set(arguments)!=expected or not isinstance(arguments['view'],str)
            or (arguments['view'] not in VIEWS and not source_view and not review and not edit and arguments['view'] != 'remount')):
        return _response(400,{'error':'Choose a supported native memory view'})
    route = '/memory/pulse/' + arguments['view']
    remount = arguments['view'] == 'remount'
    if remount:
        route = '/memory/remount'
    if source_view:
        if arguments['view'] == 'wiki':
            from .memory_wiki import request_target
        elif arguments['view'] == 'knowledge':
            from .memory_knowledge import request_target
        elif arguments['view'] == 'hypotheses':
            from .memory_hypothesis_queue import request_target
        elif arguments['view']=='upgrades':
            from .memory_upgrade_queue import request_target
        elif arguments['view']=='life':
            from .memory_life import request_target
        elif arguments['view']=='telos_file':
            from .memory_telos_file import request_target
        else:
            from .memory_tab_freshness import request_target
        try:
            target = request_target(arguments['target'])
        except LookupError:
            return _response(404,{'error':'This source route is not a governed read view'})
        except ValueError:
            return _response(400,{'error':'Invalid source read route'})
        route = '/memory/' + arguments['view'] + '?' + urllib.parse.urlencode({'target':target})
    data = None
    if edit:
        from .memory_telos_file import validate_name
        from .memory_sources import SOURCE_LIMIT
        try:
            validate_name(arguments['name'])
            if (not isinstance(arguments['content'], str) or len(arguments['content'].encode()) > SOURCE_LIMIT
                    or not isinstance(arguments['reference'], str) or re.fullmatch('[0-9a-f]{64}', arguments['reference']) is None
                    or not isinstance(arguments['request_id'], str) or not 1 <= len(arguments['request_id']) <= 256):
                raise ValueError('Choose bounded TELOS edit arguments')
        except ValueError:
            return _response(400, {'error': 'Invalid TELOS edit arguments'})
        route = '/memory/telos_file'
        data = json.dumps({key: arguments[key] for key in ('name', 'content', 'reference', 'request_id')}, ensure_ascii=False).encode()
    if review:
        if arguments['view']=='hypothesis_review':
            from .memory_hypothesis_review import action_target
        else:
            from .memory_upgrade_queue import action_target
        try:
            action_target(arguments['target'])
            if (arguments['note'] is not None and (not isinstance(arguments['note'],str) or len(arguments['note'])>8192)
                    or not isinstance(arguments['request_id'],str) or not 1<=len(arguments['request_id'])<=256):
                raise ValueError('Choose bounded memory review arguments')
        except LookupError:
            return _response(404,{'error':'Choose a governed memory review route'})
        except ValueError:
            return _response(400,{'error':'Invalid memory review arguments'})
        route = '/memory/' + ('hypotheses' if arguments['view']=='hypothesis_review' else 'upgrades') + '/review'
        data = json.dumps({key:arguments[key] for key in ('target','note','request_id')},ensure_ascii=False).encode()
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
        if review or edit:credentials['Content-Type']='application/json'
        request=urllib.request.Request(base+'/api/plugins/lifeos-hook-bridge'+route, data=data,
                                      headers=credentials,method='POST' if remount or review or edit else 'GET')
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
        timeout = 120 if remount else 8
        if arguments['view'] == 'life':
            from .memory_operational_views import CAPABILITY_WINDOWS
            from .memory_performance import ROUTES as PERFORMANCE_ROUTES
            from .memory_conduit import ROUTES as CONDUIT_ROUTES
            from .memory_menubar import ROUTES as MENUBAR_ROUTES
            from .memory_local_intelligence import ROUTES as LOCAL_ROUTES
            from .memory_content import ROUTES as CONTENT_ROUTES
            from .memory_algorithm_tab import ROUTES as ALGORITHM_ROUTES
            if target in CAPABILITY_WINDOWS or urllib.parse.urlsplit(target).path in frozenset(PERFORMANCE_ROUTES) | CONDUIT_ROUTES | MENUBAR_ROUTES | LOCAL_ROUTES | CONTENT_ROUTES | ALGORITHM_ROUTES: timeout = 30
        try:
            response=opener.open(request,timeout=timeout)
        except urllib.error.HTTPError as error:
            response=error
        with response:
            status=response.status
            if status not in ({200,400,401,403,404,409} if review or edit else {200,400,401,403,409} if remount else
                              {200,400,401,403,404} if source_view else {200,400,401,403}):
                return _response(503,{'error':'Authenticated memory is unavailable'})
            if (status in ({200,404,409} if review or edit else {200,404} if source_view else {200}) and response.headers.get('x-lifeos-memory-installation')
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
            source_scalar = (arguments['view'] == 'life' and target in {'/api/novelty', '/api/local-intelligence'}
                and type(body) in (str, bool, int, float) and (type(body) is not float or math.isfinite(body)))
            if status==200 and (not isinstance(body,(dict,list)) and body is not None and not source_scalar):
                raise ValueError('Invalid authenticated memory response')
            if status==401 and isinstance(body,dict):
                body.pop('login_url',None)
                if browser:
                    body['login_url']=browser+'/login'
            return _response(status,body,response.headers.get_all('set-cookie',[]))
    except (ValueError,OSError,RuntimeError,urllib.error.URLError,http.client.HTTPException):
        return _response(503,{'error':'Authenticated memory is unavailable'})
