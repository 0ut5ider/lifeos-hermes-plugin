# ABOUTME: Supplies current admitted records and hypotheses to the native upgrades queue.
# ABOUTME: Governs fixed HTTP read and review routes through owner publication operations.
from datetime import datetime,timezone
import json
import re
from urllib.parse import quote,unquote,urlsplit
from uuid import uuid4

from .memory_access import MemoryUnavailable
from .memory_sources import CORPUS_LIMIT
from .memory_upgrades import _collect,run
from .memory_hypothesis_queue import _sources
from .memory_hypothesis_review import review as review_hypothesis


def request_target(value):
    if not isinstance(value,str) or len(value)>1024:
        raise ValueError('Upgrade views require a bounded installed route')
    parsed=urlsplit(value)
    if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment:
        raise ValueError('Upgrade views require one fixed route without query parameters')
    if parsed.path=='/api/upgrades':return parsed.path
    matched=re.fullmatch('/api/upgrades/([^/]+)',parsed.path)
    if matched is None:raise LookupError('This upgrade route is not a governed read view')
    if re.search(r'%(?![0-9A-Fa-f]{2})',matched[1]):raise ValueError('An upgrade identifier requires valid encoding')
    identifier=unquote(matched[1],errors='strict')
    if (re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,239}',identifier) is None
            and re.fullmatch(r'hyp:[a-zA-Z0-9_-]{1,128}',identifier) is None):
        raise ValueError('An upgrade identifier requires a bounded native identifier')
    return '/api/upgrades/'+quote(identifier,safe=':')


def action_target(value):
    if not isinstance(value,str):raise ValueError('Choose a fixed upgrade review route')
    matched=re.fullmatch(r'(/api/upgrades/[^/]+)/(accept|reject)',value)
    if matched is None:raise LookupError('This upgrade route is not a governed review action')
    target=request_target(matched[1])
    return target.rsplit('/',1)[1],matched[2]


def view(memory,scope,target,*,check_current=None):
    target=request_target(target)
    if target=='/api/upgrades':
        run(memory,scope,action='expire',arguments={},request_id='upgrades-view-'+uuid4().hex,
            check_current=check_current)
    if check_current is not None:check_current()
    with memory._transaction() as connection:
        records=_collect(memory,scope,connection,with_state=False)
        hypotheses=_sources(memory,scope,connection)
        if len(json.dumps([records['sources'],hypotheses]).encode())>CORPUS_LIMIT:
            raise MemoryUnavailable('The combined upgrades queue exceeds its source transport limit')
        result=memory._native('upgrades_view',records=records['sources'],hypotheses=hypotheses,target=target)
        if check_current is not None:check_current()
        if (_collect(memory,scope,connection,with_state=False)!=records or _sources(memory,scope,connection)!=hypotheses):
            raise MemoryUnavailable('Combined upgrade sources change during native rendering')
        if (not isinstance(result,dict) or set(result)!={'status','body'} or type(result['status']) is not int
                or result['status'] not in (200,404) or not isinstance(result['body'],dict)
                or len(json.dumps(result).encode())>CORPUS_LIMIT):
            raise MemoryUnavailable('The native upgrades queue changes its declared response')
        text=json.dumps(result)
        if memory._filter_history(connection,scope,text+'\n'+text.replace('_',' ').replace('-',' '),
                datetime.now(timezone.utc).isoformat())['excluded']:
            raise MemoryUnavailable('The native upgrades queue contains excluded source text')
        if check_current is not None:check_current()
        return result


def review(memory,scope,*,target,note,request_id,check_current=None):
    identifier,verb=action_target(target)
    if note is not None and (not isinstance(note,str) or len(note)>8192):
        raise ValueError('Choose a bounded upgrade review note')
    if identifier.startswith('hyp:'):
        result=review_hypothesis(memory,scope,target='/api/hypotheses/'+identifier[4:]+'/'+
            ('graduate' if verb=='accept' else 'reject'),note=note,request_id=request_id,check_current=check_current)
        body=result['body']
        if body.get('patch')=='still-red-pending':
            response={'ok':False,'reason':'patch_still_red','detail':body['patch_detail']}
        elif result['status']==200 and body.get('ok') is True:response={'ok':True}
        elif isinstance(body.get('error'),str):response={'ok':False,'reason':body['error']}
        else:raise MemoryUnavailable('Hypothesis review requires a declared native response')
    else:
        response=run(memory,scope,action='status',arguments={'id':identifier,
            'status':'accepted' if verb=='accept' else 'rejected','opts':{} if note is None else {'note':note}},
            request_id=request_id,check_current=check_current)['result']
    return {'status':200 if response['ok'] else 404 if response.get('reason')=='not_found' else 409,'body':response}
