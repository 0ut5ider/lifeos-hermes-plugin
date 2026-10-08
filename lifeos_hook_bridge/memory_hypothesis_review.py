# ABOUTME: Publishes reviewed native hypotheses as one recoverable owner operation.
# ABOUTME: Preserves current sources, registered facts, and later archive or frame changes.
from datetime import datetime,timezone
import json
from pathlib import Path
import re

from .memory_access import MemoryConflict,MemoryUnavailable,_digest
from .memory_adoption import _owner
from .memory_hypothesis_queue import PREFIX,_sources,request_target
from .memory_recurrence import _entries,_path
from .memory_sources import read_markdown,SOURCE_LIMIT,CORPUS_LIMIT,json_projection
from .memory_transaction import publish

FRAMES='LIFEOS/MEMORY/WISDOM/FRAMES'
STATE=PREFIX+'/.state.json'


def action_target(value):
    if not isinstance(value,str):raise ValueError('Choose a fixed hypothesis review route')
    match=re.fullmatch(r'(/api/hypotheses/[^/]+)/(graduate|reject)',value)
    if match is None:raise LookupError('This hypothesis route is not a governed review action')
    target=request_target(match[1])
    return target.rsplit('/',1)[1],match[2]


def _collect(memory,scope,connection):
    paths=[str(path) for path in _entries(memory,FRAMES,[0]) if path.suffix=='.md']
    frames={Path(source['path']).name:source['content']
        for source in read_markdown(memory,scope,paths,connection=connection)}
    state_path=_path(memory,STATE)
    if state_path.exists() and state_path.stat().st_size>SOURCE_LIMIT:
        raise MemoryUnavailable('The hypothesis review state exceeds its source limit')
    state=state_path.read_text() if state_path.exists() else None
    text=(state or '')+'\n'+(json_projection(state or '') or '')
    instant=datetime.now(timezone.utc).isoformat()
    if (memory._native('validate_source_batch',contents=[text])['accepted']!=[True]
            or memory._filter_history(connection,scope,text,instant,reviewed=True)['excluded']):
        raise MemoryUnavailable('Hypothesis review state contains an excluded source')
    result={'hypotheses':_sources(memory,scope,connection),'frames':frames,'state':state,
        'directory_exists':_path(memory,PREFIX,directory=True).exists()}
    if len(json.dumps(result).encode())>CORPUS_LIMIT:
        raise MemoryUnavailable('Hypothesis review exceeds its source transport limit')
    return result


def _destination(memory,relative):
    allowed=(relative==STATE or re.fullmatch(re.escape(FRAMES)+r'/[a-zA-Z0-9_-]{1,128}\.md',relative)
        or re.fullmatch(re.escape(PREFIX)+r'/(?:_archive/)?[a-zA-Z0-9][a-zA-Z0-9._-]{0,200}\.md',relative))
    if not allowed:raise MemoryUnavailable('Hypothesis review changes its declared publication path')
    path=_path(memory,relative)
    if path.exists() and path.stat().st_size>SOURCE_LIMIT:
        raise MemoryUnavailable('A hypothesis review destination exceeds its source limit')
    return path


def publication_paths(memory,scope,payload):
    if not _owner(scope) or 'approve' not in scope.proposals:
        raise MemoryUnavailable('Hypothesis review requires unrestricted owner approval authority')
    return [_destination(memory,relative).relative_to(memory.root).as_posix() for relative in payload['outputs']]


def _preserve(memory,connection,artifacts):
    for artifact in artifacts:
        path=_destination(memory,artifact['path'])
        if connection.execute("SELECT 1 FROM records WHERE path=? AND status='active' LIMIT 1",(artifact['path'],)).fetchone():
            if artifact['content'] is None or not path.exists() or path.read_text()!=artifact['content']:
                raise MemoryUnavailable('A registered fact source requires explicit fact review before hypothesis publication')


def review(memory,scope,*,target,note,request_id,check_current=None):
    slug,verb=action_target(target)
    if (not _owner(scope) or 'approve' not in scope.proposals or note is not None and
            (not isinstance(note,str) or len(note)>8192)
            or not isinstance(request_id,str) or not 1<=len(request_id)<=256):
        raise MemoryUnavailable('Hypothesis review requires owner approval authority and bounded arguments')
    if check_current is not None:check_current()
    if note is not None and memory._native('validate_source_batch',contents=[note])['accepted']!=[True]:
        raise MemoryUnavailable('Hypothesis review notes contain excluded source text')
    identity={'operation':'hypothesis_review','target':target,'note':note}
    with memory._transaction() as connection:
        prior=connection.execute('SELECT * FROM operations WHERE writer=? AND request_id=?',(scope.writer,request_id)).fetchone()
        if prior is not None:
            if prior['payload_digest']!=_digest(json.dumps(identity,sort_keys=True)):
                raise MemoryConflict('The hypothesis review request names another operation')
            receipt=json.loads(prior['receipt'])
            if receipt.get('status')!='committed' or not isinstance(receipt.get('result'),dict):
                raise MemoryUnavailable('The retained hypothesis review requires outcome recovery')
            if memory._filter_history(connection,scope,json.dumps(receipt),datetime.now(timezone.utc).isoformat())['excluded']:
                raise MemoryUnavailable('The retained hypothesis review response contains an excluded source')
            if check_current is not None:check_current()
            return receipt['result']
        sources=_collect(memory,scope,connection)
        rendered=memory._native('hypothesis_review',sources=sources,slug=slug,verb=verb,note=note,
            now=datetime.now(timezone.utc).isoformat())
        if check_current is not None:check_current()
        if _collect(memory,scope,connection)!=sources:
            raise MemoryConflict('Hypothesis review sources change during native rendering')
        if (not isinstance(rendered,dict) or set(rendered)!={'status','body','publications'} or rendered['status'] not in (200,404,409)
                or not isinstance(rendered['body'],dict) or not isinstance(rendered['publications'],list)
                or len(json.dumps(rendered).encode())>CORPUS_LIMIT):
            raise MemoryUnavailable('Native hypothesis review changes its declared response')
        artifacts=rendered['publications']
        before={}
        for artifact in artifacts:
            if (not isinstance(artifact,dict) or set(artifact)!={'path','content'}
                    or not isinstance(artifact['path'],str) or artifact['content'] is not None and not isinstance(artifact['content'],str)
                    or artifact['path'] in before):
                raise MemoryUnavailable('Native hypothesis review changes its declared artifacts')
            if artifact['content'] is not None and len(artifact['content'].encode())>SOURCE_LIMIT:
                raise MemoryUnavailable('A hypothesis review artifact exceeds its source limit')
            path=_destination(memory,artifact['path'])
            before[artifact['path']]=path.read_bytes() if path.exists() else None
            if '/_archive/' in artifact['path'] and path.exists():
                raise MemoryConflict('The hypothesis review archive destination already exists')
        contents=[artifact['content'] for artifact in artifacts if artifact['content'] is not None]
        if contents and memory._native('validate_source_batch',contents=contents)['accepted']!=[True]*len(contents):
            raise MemoryUnavailable('Hypothesis review artifacts contain excluded source text')
        if memory._filter_history(connection,scope,json.dumps(rendered),datetime.now(timezone.utc).isoformat())['excluded']:
            raise MemoryUnavailable('Native hypothesis review output contains an excluded source')
        _preserve(memory,connection,artifacts)
        result={'status':rendered['status'],'body':rendered['body']}
        if not artifacts:return result
    def apply(connection):
        if check_current is not None:check_current()
        if (_collect(memory,scope,connection)!=sources or any(
                (_destination(memory,name).read_bytes() if _destination(memory,name).exists() else None)!=content
                for name,content in before.items())):
            raise MemoryConflict('Hypothesis review sources or destinations change before publication')
        _preserve(memory,connection,artifacts)
        for artifact in artifacts:
            if check_current is not None:check_current()
            path=_destination(memory,artifact['path'])
            if artifact['content'] is None:path.unlink()
            else:publish(path,artifact['content'].encode())
        return {'status':'committed','result':result}
    receipt=memory._operation(scope,request_id,{'operation':'hypothesis_review','outputs':sorted(before)},apply,
        identity_payload=identity)
    if check_current is not None:check_current()
    if receipt['status']!='committed':raise MemoryUnavailable('Hypothesis review does not complete its recoverable publication')
    return receipt['result']
