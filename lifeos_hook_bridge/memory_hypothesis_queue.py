# ABOUTME: Supplies admitted retained hypotheses to the native review queue renderer.
# ABOUTME: Validates fixed read routes and rechecks source and owner authority after rendering.
from datetime import datetime,timezone
import json
from pathlib import Path
import re
from urllib.parse import quote,unquote,urlsplit

from .memory_access import MemoryUnavailable
from .memory_recurrence import _entries
from .memory_sources import authorize,read_markdown,CORPUS_LIMIT

PREFIX='LIFEOS/MEMORY/WISDOM/FRAMES/_hypotheses'


def request_target(value):
    if not isinstance(value,str) or len(value)>1024:
        raise ValueError('Hypothesis views require a bounded installed route')
    parsed=urlsplit(value)
    if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment:
        raise ValueError('Hypothesis views require one fixed route without query parameters')
    if parsed.path=='/api/hypotheses':return parsed.path
    matched=re.fullmatch('/api/hypotheses/([^/]+)',parsed.path)
    if matched is None:raise LookupError('This hypothesis route is not a governed read view')
    encoded=matched[1]
    if re.search(r'%(?![0-9A-Fa-f]{2})',encoded):raise ValueError('A hypothesis slug requires valid encoding')
    decoded=unquote(encoded,errors='strict')
    if re.fullmatch('[a-zA-Z0-9_-]{1,128}',decoded) is None:
        raise ValueError('A hypothesis slug requires a bounded native identifier')
    return '/api/hypotheses/'+quote(decoded,safe='')


def _sources(memory,scope,connection):
    authorize(scope)
    paths=[str(path) for path in _entries(memory,PREFIX,[0]) if path.suffix=='.md' and path.name!='README.md']
    sources=[{'filename':Path(source['path']).name,'content':source['content']}
        for source in read_markdown(memory,scope,paths,connection=connection)]
    if len(json.dumps(sources).encode())>CORPUS_LIMIT:
        raise MemoryUnavailable('The hypothesis queue exceeds its source transport limit')
    return sources


def view(memory,scope,target,*,check_current=None):
    target=request_target(target)
    if check_current is not None:check_current()
    with memory._transaction() as connection:
        sources=_sources(memory,scope,connection)
        result=memory._native('hypothesis_view',sources=sources,target=target)
        if check_current is not None:check_current()
        if _sources(memory,scope,connection)!=sources:
            raise MemoryUnavailable('Hypothesis sources change during native rendering')
        if (not isinstance(result,dict) or set(result)!={'status','body'}
                or type(result['status']) is not int or result['status'] not in (200,404)
                or not isinstance(result['body'],dict) or len(json.dumps(result).encode())>CORPUS_LIMIT):
            raise MemoryUnavailable('The native hypothesis queue changes its declared response')
        if memory._filter_history(connection,scope,json.dumps(result),datetime.now(timezone.utc).isoformat())['excluded']:
            raise MemoryUnavailable('The native hypothesis queue contains excluded source text')
        if check_current is not None:check_current()
        return result
