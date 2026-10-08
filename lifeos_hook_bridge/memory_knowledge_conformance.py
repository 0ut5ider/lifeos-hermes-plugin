# ABOUTME: Renders native schema finding sets from current registered notes and owner sources.
# ABOUTME: Appends private finding events through recoverable publication with current authority checks.
from datetime import datetime, timezone
import json
import os
from pathlib import Path

from .memory_access import MemoryConflict, MemoryUnavailable
from .memory_adoption import _owner
from .memory_knowledge_lint import _sources, DIRECTORIES
from .memory_sources import authorize, CORPUS_LIMIT
from .memory_transaction import publish


EVENTS='LIFEOS/MEMORY/STATE/events.jsonl'
KNOWLEDGE='LIFEOS/MEMORY/KNOWLEDGE'
EVENT_LIMIT=8*1024*1024


def _destination(memory):
    path=memory._path(EVENTS)
    expected=memory.root.parent/'.config/LIFEOS/USER/MEMORY/STATE/events.jsonl'
    if (path.resolve()!=expected or path.is_symlink() or path.exists() and (
            not path.is_file() or path.stat().st_uid!=os.getuid() or path.stat().st_size>EVENT_LIMIT
            or path.samefile(memory.database))):
        raise MemoryUnavailable('The Knowledge finding event changes its owner destination')
    return path


def publication_paths(memory,scope,payload):
    if not _owner(scope) or payload['destination']!=EVENTS:
        raise MemoryUnavailable('Knowledge findings require unrestricted owner publication authority')
    _destination(memory)
    return [EVENTS]


def _current(memory,scope,connection):
    root=memory._path(KNOWLEDGE)
    if root.exists() and (not root.is_dir() or root.is_symlink()):
        raise MemoryUnavailable('Knowledge findings require their physical owner archive')
    directories=[]
    for name in sorted(DIRECTORIES):
        path=root/name
        if path.is_symlink() or path.resolve()!=root.resolve()/name or path.exists() and not path.is_dir():
            raise MemoryUnavailable('A Knowledge finding directory changes its physical path')
        if path.is_dir():directories.append(name)
    return {'sources':_sources(memory,scope,connection),'directories':directories,'exists':root.exists()}


def run(memory,scope,*,request_id,source_session='',check_current=None):
    authorize(scope)
    if not _owner(scope) or not isinstance(request_id,str) or not 1<=len(request_id)<=256:
        raise MemoryUnavailable('Knowledge finding publication requires owner grants and a bounded request identifier')
    if check_current is not None:check_current()
    with memory._transaction() as connection:
        current=_current(memory,scope,connection)
        destination=_destination(memory)
        before=destination.read_bytes() if destination.exists() else None
        result=memory._native('knowledge_conformance',**current)
        if check_current is not None:check_current()
        if _current(memory,scope,connection)!=current:
            raise MemoryUnavailable('Knowledge finding sources change during native rendering')
        if (set(result)!={'stderr','event'} or not isinstance(result['stderr'],str)
                or result['event'] is not None and not isinstance(result['event'],dict)
                or len(json.dumps(result).encode())>CORPUS_LIMIT):
            raise MemoryUnavailable('Native Knowledge findings change their declared response')
        if memory._filter_history(connection,scope,json.dumps(result),datetime.now(timezone.utc).isoformat())['excluded']:
            raise MemoryUnavailable('Native Knowledge findings contain an excluded source label')
        if result['event'] is None:
            if current['exists'] or result['stderr']:
                raise MemoryUnavailable('Native Knowledge findings return an invalid skipped check')
            return {'ok':True,'stderr':''}
        event=result['event']
        if (set(event)!={'type','source','findings','extra'} or event['type']!='doc.integrity.knowledge_conformance'
                or event['source']!='KnowledgeConformance' or not isinstance(event['findings'],list)
                or not isinstance(event['extra'],dict)):
            raise MemoryUnavailable('Native Knowledge findings return an undeclared event')
        counts=event['extra']
        if (set(counts)!={'total','conformant','non_conformant','conformance_pct','per_dir'}
                or any(type(counts[key]) is not int or counts[key]<0 for key in ('total','conformant','non_conformant'))
                or counts['conformant']+counts['non_conformant']!=counts['total']
                or type(counts['conformance_pct']) not in (int,float) or not 0<=counts['conformance_pct']<=100
                or not isinstance(counts['per_dir'],dict) or not set(counts['per_dir'])<=DIRECTORIES):
            raise MemoryUnavailable('Native Knowledge findings return invalid conformance counts')
        for values in counts['per_dir'].values():
            if (not isinstance(values,dict) or set(values)!={'n','ok'}
                    or any(type(values[key]) is not int or values[key]<0 for key in ('n','ok'))
                    or values['ok']>values['n']):
                raise MemoryUnavailable('Native Knowledge findings return invalid directory counts')
        if sum(values['n'] for values in counts['per_dir'].values())!=counts['total']:
            raise MemoryUnavailable('Native Knowledge findings change their directory totals')
        for finding in event['findings']:
            if (not isinstance(finding,dict) or set(finding)!={'kind','key','detail'}
                    or finding['kind']!='off_schema' or any(not isinstance(finding[key],str) for key in ('key','detail'))):
                raise MemoryUnavailable('Native Knowledge finding text is unavailable')
        record={'timestamp':datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z'),
            'session_id':source_session,
            **event['extra'],'type':event['type'],'source':event['source'],
            'ok':not event['findings'],'finding_count':len(event['findings']),'findings':event['findings']}
        content=(before or b'')+(json.dumps(record,separators=(',',':'),ensure_ascii=False)+'\n').encode()
        if len(content)>EVENT_LIMIT:
            raise MemoryUnavailable('The Knowledge finding event log exceeds its publication limit')
    def apply(connection):
        if check_current is not None:check_current()
        path=_destination(memory)
        if (_current(memory,scope,connection)!=current
                or (path.read_bytes() if path.exists() else None)!=before):
            raise MemoryConflict('Knowledge sources or event history change before finding publication')
        if check_current is not None:check_current()
        publish(path,content)
        return {'status':'committed','stderr':result['stderr']}
    receipt=memory._operation(scope,request_id,{'operation':'knowledge_conformance','destination':EVENTS,
        'sources':current,'source_session':source_session},apply)
    if check_current is not None:check_current()
    return {'ok':receipt['status']=='committed','stderr':receipt.get('stderr',''),'receipt':receipt}
