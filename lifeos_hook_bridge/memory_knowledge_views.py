# ABOUTME: Supplies current registered notes and admitted staging metadata to native Knowledge views.
# ABOUTME: Publishes native indexes through owner transactions with current audience and source checks.
from datetime import datetime, timezone
from pathlib import Path
import re

from .memory_access import MemoryUnavailable
from .memory_adoption import _owner
from .memory_canonical import corpus
from .memory_knowledge_harvest import _snapshot, _state, _file
from .memory_sources import authorize, _admit, source_labels, CORPUS_LIMIT
from .memory_staging import KNOWLEDGE, STATE, DOMAINS
from .memory_transaction import publish


INDEXES = frozenset([KNOWLEDGE+'/_index.md', *(KNOWLEDGE+'/'+domain+'/_index.md' for domain in DOMAINS)])


def _sources(memory, connection, scope, snapshot, view):
    sources=[]
    if view=='review':
        pending=[]
        for relative,item in snapshot['files'].items():
            if re.fullmatch(r'LIFEOS/MEMORY/KNOWLEDGE/_harvest-queue/(People|Companies|Ideas|Research)/[^/]+\.md',relative) is None:
                continue
            timestamp=datetime.fromtimestamp((memory.root/relative).stat().st_mtime,timezone.utc).isoformat()
            if not _admit(memory,connection,scope,item['content'],relative,timestamp)['excluded']:
                pending.append({'path':str(memory.root/relative),'content':item['content']})
        if pending:
            accepted=memory._native('validate_source_batch',contents=[item['path']+'\n'+item['content'] for item in pending])['accepted']
            sources.extend(item for item,allowed in zip(pending,accepted,strict=True) if allowed is True)
    else:
        current=corpus(memory,scope,str(memory.root/'LIFEOS/MEMORY'),connection=connection)
        sources.extend({'path':str(memory.root/'LIFEOS/MEMORY'/Path(file).relative_to(current['root'])),
                        'content':record['content']} for file,record in zip(current['files'],current['records'],strict=True))
        if STATE in snapshot['files']:
            text=snapshot['files'][STATE]['content']
            _state(text)
            sources.append({'path':str(memory.root/STATE),'content':text})
    return sources


def publication_paths(memory,scope,payload):
    if not _owner(scope) or set(payload['writes'])!=INDEXES:
        raise MemoryUnavailable('Native Knowledge index publication requires its complete owner destination set')
    for relative in INDEXES:_file(memory,relative)
    return sorted(INDEXES)


def run(memory,scope,*,view,request_id,source_session='',check_current=None):
    authorize(scope)
    if not scope.principal or view not in ('review','status','contradictions','index'):
        raise MemoryUnavailable('Choose a native Knowledge view with authenticated owner recall')
    if view=='index' and not _owner(scope):
        raise MemoryUnavailable('Native Knowledge index publication requires unrestricted owner authority')
    if not isinstance(request_id,str) or not 1<=len(request_id)<=256:
        raise MemoryUnavailable('Native Knowledge views require a bounded request identifier')
    if check_current is not None:check_current()
    with memory._transaction() as connection:
        snapshot=_snapshot(memory)
        sources=_sources(memory,connection,scope,snapshot,view)
        plan=memory._native('knowledge_harvester_view',view=view,sources=sources,
            ordering=[str(memory.root/name/child) for name,children in snapshot['directories'].items() for child in children or []])
        if check_current is not None:check_current()
        if _snapshot(memory)!=snapshot:
            raise MemoryUnavailable('Knowledge view sources change during native rendering')
        if (set(plan)!={'stdout','writes','deletes','moves'} or not isinstance(plan['stdout'],str)
                or plan['deletes'] or plan['moves'] or not isinstance(plan['writes'],list)
                or len(plan['stdout'].encode())>CORPUS_LIMIT):
            raise MemoryUnavailable('Native Knowledge view changes its declared response')
        output_projection=plan['stdout']+'\n'+plan['stdout'].replace('_',' ').replace('-',' ')
        if memory._filter_history(connection,scope,output_projection,datetime.now(timezone.utc).isoformat())['excluded']:
            raise MemoryUnavailable('Native Knowledge view contains an excluded source label')
        if view!='index':
            if plan['writes']:raise MemoryUnavailable('A native Knowledge read attempts a publication')
            if check_current is not None:check_current()
            return {'ok':True,'stdout':plan['stdout']}
        writes={}
        for item in plan['writes']:
            if (not isinstance(item,dict) or set(item)!={'path','content'} or not isinstance(item['path'],str)
                    or not isinstance(item['content'],str)):
                raise MemoryUnavailable('Native Knowledge rendering returns an invalid index')
            relative=Path(item['path']).relative_to(memory.root).as_posix()
            if relative in writes:raise MemoryUnavailable('Native Knowledge rendering repeats an index')
            writes[relative]=item['content']
        payload={'operation':'knowledge_view','view':view,'source_session':source_session,'writes':writes}
        publication_paths(memory,scope,payload)
        if sum(len(text.encode()) for text in writes.values())>CORPUS_LIMIT:
            raise MemoryUnavailable('Native Knowledge indexes exceed their publication byte limit')
        accepted=memory._native('validate_source_batch',contents=[text+'\n'+source_labels(name) for name,text in writes.items()])['accepted']
        if not all(value is True for value in accepted):
            raise MemoryUnavailable('Native validation refuses a declared Knowledge index')
        if any(memory._filter_history(connection,scope,text,datetime.now(timezone.utc).isoformat())['excluded'] for text in writes.values()):
            raise MemoryUnavailable('Native Knowledge indexes contain an excluded claim')
    def apply(connection):
        if check_current is not None:check_current()
        if _snapshot(memory)!=snapshot:
            return {'status':'conflict','reason':'Knowledge sources change before index publication'}
        for name,text in writes.items():publish(_file(memory,name),text.encode())
        return {'status':'committed','indexes_published':len(writes),'stdout':plan['stdout']}
    receipt=memory._operation(scope,request_id,payload,apply)
    return {'ok':receipt['status']=='committed','receipt':receipt}
