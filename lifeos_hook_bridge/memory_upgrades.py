# ABOUTME: Supplies admitted upgrade records to native store reads and publication planning.
# ABOUTME: Journals fixed owner mutations with current source, authority, and retirement checks.
from datetime import datetime,timezone
import json
from pathlib import Path
import re

from .memory_access import MemoryConflict,MemoryUnavailable,_digest
from .memory_adoption import _owner
from .memory_recurrence import _entries,_path
from .memory_sources import authorize,read_markdown,SOURCE_LIMIT,CORPUS_LIMIT,json_projection
from .memory_transaction import publish

ROOT='LIFEOS/MEMORY/UPGRADES'
RECORDS=ROOT+'/records'
STATE=ROOT+'/.state.json'
STATUSES=frozenset(('recommended','accepted','applied','verified','rejected','expired'))
SOURCES=frozenset(('directive','correction','upgrade-skill','algo-run','autonomous','manual'))


def _identifier(value):
    if not isinstance(value,str) or re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,239}',value) is None:
        raise MemoryUnavailable('Upgrades require a bounded native identifier')
    return value


def _text(value,maximum=8192):
    return isinstance(value,str) and len(value)<=maximum


def _arguments(action,arguments):
    if not isinstance(arguments,dict):raise MemoryUnavailable('Upgrade store arguments require declared fields')
    if action=='list' and set(arguments)=={'filter'}:
        value=arguments['filter']
        if value is None or isinstance(value,dict) and set(value)<={'status','source'} and all(_text(item,128) for item in value.values()):return
    elif action=='get' and set(arguments)=={'id'}:
        _identifier(arguments['id'])
        return
    elif action=='status' and set(arguments)=={'id','status','opts'}:
        _identifier(arguments['id'])
        opts=arguments['opts']
        if (isinstance(arguments['status'],str) and arguments['status'] in STATUSES and (opts is None or isinstance(opts,dict)
                and set(opts)<={'note','ledger_id'} and all(_text(item) for item in opts.values()))):return
    elif action=='expire' and not arguments:return
    elif action=='add' and set(arguments)=={'input'}:
        value=arguments['input']
        if (isinstance(value,dict) and {'claim','source'}<=set(value)
                and set(value)<={'claim','source','current_state','recommendation','target_surface','confidence','session_id','evidence'}
                and _text(value['claim']) and isinstance(value['source'],str) and value['source'] in SOURCES
                and all(_text(value[key]) for key in ('current_state','recommendation','target_surface','session_id') if key in value)
                and ('confidence' not in value or type(value['confidence']) in (int,float) and 0<=value['confidence']<=1)
                and ('evidence' not in value or isinstance(value['evidence'],list) and len(value['evidence'])<=100
                    and all(_text(item) for item in value['evidence']))):return
    raise MemoryUnavailable('Choose bounded native upgrade store arguments')


def _destination(memory,relative):
    if relative!=STATE:
        if not relative.startswith(RECORDS+'/') or not relative.endswith('.md'):
            raise MemoryUnavailable('Upgrade publication changes its fixed store')
        _identifier(relative.removeprefix(RECORDS+'/').removesuffix('.md'))
    path=_path(memory,relative)
    if path.exists() and path.stat().st_size>SOURCE_LIMIT:
        raise MemoryUnavailable('An upgrade store destination exceeds its source limit')
    return path


def _collect(memory,scope,connection,*,with_state):
    authorize(scope)
    if not scope.principal:raise MemoryUnavailable('Upgrade store reads require a bound owner')
    paths=sorted(str(path) for path in _entries(memory,RECORDS,[0]) if path.suffix=='.md')
    raw={}
    for name in paths:
        relative=Path(name).relative_to(memory.root).as_posix()
        path=_destination(memory,relative)
        raw[relative]=path.read_text()
    state=None
    if with_state:
        path=_destination(memory,STATE)
        if path.exists():
            state=path.read_text()
            projection=json_projection(state)
            if projection is None:raise MemoryUnavailable('Upgrade creation preserves malformed state for explicit recovery')
            text=state+'\n'+projection
            if (memory._native('validate_source_batch',contents=[text])['accepted']!=[True]
                    or memory._filter_history(connection,scope,text,datetime.now(timezone.utc).isoformat(),reviewed=True)['excluded']):
                raise MemoryUnavailable('Upgrade state contains excluded source text')
            raw[STATE]=state
    sources=[{'filename':Path(item['path']).name,'content':item['content']}
        for item in read_markdown(memory,scope,paths,connection=connection)]
    if max(len(json.dumps(raw).encode()),len(json.dumps(sources).encode()))>CORPUS_LIMIT:
        raise MemoryUnavailable('Upgrade store sources exceed their transport limit')
    return {'raw':raw,'sources':sources,'state':state}


def publication_paths(memory,scope,payload):
    if not _owner(scope):raise MemoryUnavailable('Upgrade publication requires unrestricted owner authority')
    return [_destination(memory,path).relative_to(memory.root).as_posix() for path in payload['outputs']]


def _preserve(memory,connection,artifacts):
    for artifact in artifacts:
        if connection.execute("SELECT 1 FROM records WHERE path=? AND status='active' LIMIT 1",(artifact['path'],)).fetchone():
            path=_destination(memory,artifact['path'])
            if not path.exists() or path.read_text()!=artifact['content']:
                raise MemoryUnavailable('A registered fact source requires explicit review before upgrade publication')


def run(memory,scope,*,action,arguments,request_id,source_session='',check_current=None):
    _arguments(action,arguments)
    if not isinstance(request_id,str) or not 1<=len(request_id)<=256:
        raise MemoryUnavailable('Upgrade store requests require a bounded identifier')
    authorize(scope)
    mutation=action in ('add','status','expire')
    required='create' if action=='add' else 'approve'
    if mutation and (not _owner(scope) or required not in scope.proposals):
        raise MemoryUnavailable('Upgrade publication requires current owner proposal authority')
    if check_current is not None:check_current()
    if mutation and memory._native('validate_source_batch',contents=[json_projection(json.dumps(arguments)) or ''])['accepted']!=[True]:
        raise MemoryUnavailable('Upgrade store arguments contain excluded source text')
    identity={'operation':'upgrade_store','action':action,'arguments':arguments,'source_session':source_session}
    with memory._transaction() as connection:
        prior=connection.execute('SELECT * FROM operations WHERE writer=? AND request_id=?',(scope.writer,request_id)).fetchone()
        if prior is not None:
            if prior['payload_digest']!=_digest(json.dumps(identity,sort_keys=True)):
                raise MemoryConflict('The upgrade store request names another operation')
            receipt=json.loads(prior['receipt'])
            if receipt.get('status')!='committed' or 'result' not in receipt:
                raise MemoryUnavailable('The retained upgrade store operation requires outcome recovery')
            if memory._filter_history(connection,scope,json.dumps(receipt),datetime.now(timezone.utc).isoformat())['excluded']:
                raise MemoryUnavailable('The retained upgrade receipt contains excluded source text')
            if check_current is not None:check_current()
            return {'ok':True,'result':receipt['result']}
        collected=_collect(memory,scope,connection,with_state=action=='add')
        plan=memory._native('upgrade_store',action_name=action,arguments=arguments,sources=collected['sources'],
            state=collected['state'],now=datetime.now(timezone.utc).isoformat(),source_session=source_session)
        if check_current is not None:check_current()
        if _collect(memory,scope,connection,with_state=action=='add')!=collected:
            raise MemoryConflict('Upgrade sources change during native rendering')
        if (not isinstance(plan,dict) or set(plan)!={'result','publications'} or not isinstance(plan['publications'],list)
                or len(json.dumps(plan).encode())>CORPUS_LIMIT):
            raise MemoryUnavailable('Native upgrade planning changes its declared response')
        artifacts=plan['publications']
        if not mutation and artifacts:raise MemoryUnavailable('An upgrade read attempts a publication')
        before={}
        for artifact in artifacts:
            if (not isinstance(artifact,dict) or set(artifact)!={'path','content'} or not isinstance(artifact['path'],str)
                    or not isinstance(artifact['content'],str) or len(artifact['content'].encode())>SOURCE_LIMIT
                    or artifact['path'] in before):
                raise MemoryUnavailable('Native upgrade planning changes its declared artifacts')
            path=_destination(memory,artifact['path'])
            before[artifact['path']]=path.read_bytes() if path.exists() else None
            if action=='add' and artifact['path']!=STATE and path.exists():
                raise MemoryConflict('The upgrade creation destination already exists')
        output=json.dumps(plan)
        text=output+'\n'+output.replace('_',' ').replace('-',' ')
        if memory._filter_history(connection,scope,text,datetime.now(timezone.utc).isoformat())['excluded']:
            raise MemoryUnavailable('Native upgrade output contains excluded source text')
        contents=[artifact['content'] for artifact in artifacts]
        if contents and memory._native('validate_source_batch',contents=contents)['accepted']!=[True]*len(contents):
            raise MemoryUnavailable('Native upgrade artifacts contain excluded source text')
        _preserve(memory,connection,artifacts)
        if not artifacts:return {'ok':True,'result':plan['result']}
    def apply(connection):
        if check_current is not None:check_current()
        if (_collect(memory,scope,connection,with_state=action=='add')!=collected or any(
                (_destination(memory,path).read_bytes() if _destination(memory,path).exists() else None)!=content
                for path,content in before.items())):
            raise MemoryConflict('Upgrade sources or destinations change before publication')
        _preserve(memory,connection,artifacts)
        for artifact in artifacts:
            if check_current is not None:check_current()
            publish(_destination(memory,artifact['path']),artifact['content'].encode())
        return {'status':'committed','result':plan['result']}
    receipt=memory._operation(scope,request_id,{'operation':'upgrade_store','outputs':sorted(before)},apply,
        identity_payload=identity,publication_digests={artifact['path']:_digest(artifact['content']) for artifact in artifacts})
    if check_current is not None:check_current()
    if receipt['status']!='committed':raise MemoryUnavailable('Upgrade store publication requires outcome recovery')
    return {'ok':True,'result':receipt['result']}
