# ABOUTME: Recovers registered current hot facts from reviewed native snapshots.
# ABOUTME: Preserves later facts and references with bounded sources and journaled publication.
import json
from pathlib import Path
import re

from .memory_access import HOT_FILES, MemoryUnavailable, _digest
from .memory_adoption import _owner


SNAPSHOTS = 'LIFEOS/MEMORY/OBSERVABILITY/memory-snapshots'
SOURCE_LIMIT = 256 * 1024
NAME = re.compile(r'(PRINCIPAL_MEMORY|DA_MEMORY)__\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}-\d{3}Z\.md')


def _authorize(scope):
    if not _owner(scope):
        raise MemoryUnavailable('Native recovery requires an unrestricted owner context')


def _source(memory, snapshot):
    if not isinstance(snapshot,str) or NAME.fullmatch(snapshot) is None:
        raise MemoryUnavailable('Native recovery needs an exact snapshot file name')
    category='principal' if snapshot.startswith('PRINCIPAL_MEMORY__') else 'assistant'
    path=memory._path(SNAPSHOTS+'/'+snapshot)
    physical=memory.root.parent/'.config/LIFEOS/USER/MEMORY/OBSERVABILITY/memory-snapshots'/snapshot
    if path.is_symlink() or not path.is_file() or path.resolve()!=physical:
        raise MemoryUnavailable('The native recovery snapshot is missing or changes its physical path')
    if path.stat().st_size>SOURCE_LIMIT:
        raise MemoryUnavailable('The native recovery snapshot exceeds its size limit')
    return path,category


def _plan(memory, connection, scope, snapshot):
    _authorize(scope)
    source,category=_source(memory,snapshot)
    target=memory._path(HOT_FILES[category])
    physical=memory.root.parent/'.config/LIFEOS/USER'/Path(HOT_FILES[category]).relative_to('LIFEOS/USER')
    if target.is_symlink() or not target.is_file() or target.resolve()!=physical:
        raise MemoryUnavailable('Native recovery needs its permitted current hot file')
    if target.stat().st_size>SOURCE_LIMIT:
        raise MemoryUnavailable('The current native hot file exceeds its recovery limit')
    original=source.read_text(encoding='utf-8')
    current=target.read_text(encoding='utf-8')
    parsed=memory._native('parse_hot',content=original)
    entries=parsed['entries']
    rows=[dict(row) for row in connection.execute('SELECT * FROM records WHERE category=? ORDER BY id',(category,))]
    active={row['digest']:row for row in rows if row['status']=='active'}
    if len(active)!=sum(row['status']=='active' for row in rows):
        raise MemoryUnavailable('Native recovery cannot resolve duplicate current fact identities')
    current_entries=memory._native('read_hot',path=str(target))
    if not isinstance(current_entries.get('entries'),list):
        raise MemoryUnavailable('The current native hot file cannot be parsed for recovery')
    for entry in current_entries['entries']:
        if _digest(entry) not in active and not memory._blocked(connection,entry):
            raise MemoryUnavailable('Current unregistered facts need review before native recovery')
    desired=[]
    excluded=0
    recovered=0
    for entry in entries:
        if _digest(entry) not in active:
            excluded+=1
            continue
        desired.append(entry)
        if entry not in current_entries['entries']:recovered+=1
    retained={_digest(entry) for entry in desired}
    preserved=0
    cache={target:current_entries['entries']}
    for digest,row in active.items():
        if digest not in retained:
            desired.append(memory._content(row,cache))
            preserved+=1
    items=[{'type':'memory','actor':category,'content':entry} for entry in desired]
    if items:
        results=memory._native('validate_batch',items=items)['results']
        if len(results)!=len(items) or any(not result.get('ok') or result.get('item')!=item
                                         for item,result in zip(items,results,strict=True)):
            raise MemoryUnavailable('Native validation refuses the declared recovery facts')
    identity={'root':str(memory.root),'scope':scope.signature,'snapshot':snapshot,
              'source':_digest(original),'current':_digest(current),'records':rows,'entries':desired}
    return {'signature':_digest(json.dumps(identity,sort_keys=True)), 'snapshot':snapshot,'category':category,
            'entries':desired,'recovered_facts':recovered,'preserved_facts':preserved,
            'excluded_snapshot_facts':excluded,'references':[{'id':row['id'],'revision':row['revision']}
                                                           for row in active.values()]}


def _public(plan):
    return {key:value for key,value in plan.items() if key!='entries'}


def preview(memory, scope, snapshot):
    _authorize(scope)
    with memory._transaction() as connection:
        return _public(_plan(memory,connection,scope,snapshot))


def list_snapshots(memory, scope, category=None):
    _authorize(scope)
    if category not in (None,'principal','assistant'):
        raise MemoryUnavailable('Choose principal or assistant snapshots')
    with memory._transaction():
        directory=memory._path(SNAPSHOTS)
        physical=memory.root.parent/'.config/LIFEOS/USER/MEMORY/OBSERVABILITY/memory-snapshots'
        if directory.is_symlink() or directory.resolve()!=physical:
            raise MemoryUnavailable('The native snapshot directory changes its physical path')
        names=[]
        if directory.is_dir():
            for path in sorted(directory.iterdir()):
                if NAME.fullmatch(path.name):
                    _,kind=_source(memory,path.name)
                    if category is None or category==kind:names.append(path.name)
        return {'ok':True,'snapshots':names}


def publication_paths(memory, connection, scope, payload):
    plan=_plan(memory,connection,scope,payload['snapshot'])
    return memory._hot_publication_paths(plan['category']) if plan['signature']==payload['signature'] else []


def restore(memory, scope, snapshot, signature, request_id):
    try:_authorize(scope)
    except MemoryUnavailable as error:return {'status':'rejected','reason':str(error)}
    if not isinstance(signature,str) or re.fullmatch('[0-9a-f]{64}',signature) is None:
        return {'status':'rejected','reason':'Native recovery needs the reviewed preview signature'}
    def apply(connection):
        plan=_plan(memory,connection,scope,snapshot)
        if plan['signature']!=signature:
            return {'status':'conflict','reason':'The recovery preview changed. Review a fresh preview.'}
        path=memory._path(HOT_FILES[plan['category']])
        result=memory._native('set_hot',path=str(path),entries=plan['entries'],writer=scope.writer,allowDrastic=False)
        if not result.get('ok'):
            raise MemoryUnavailable('The native writer refuses recovery publication')
        actual=memory._native('read_hot',path=str(path))
        if actual.get('entries')!=plan['entries'] or actual.get('dropped_invalid'):
            raise MemoryUnavailable('Native recovery did not publish the complete current fact set')
        memory._hot_snapshot(connection,plan['category'])
        summary={key:result[key] for key in ('accepted','prior_count','new_count')}
        return {'status':'committed',**_public(plan),'native_receipt':summary,'references_preserved':True}
    return memory._operation(scope,request_id,{'operation':'restore','snapshot':snapshot,'signature':signature},apply)
