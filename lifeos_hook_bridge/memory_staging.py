# ABOUTME: Publishes reviewed native staged notes with current facts and derived indexes.
# ABOUTME: Binds source identity and project grants to a recoverable publication receipt.
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re

from .memory_access import MemoryUnavailable, _digest
from .memory_adoption import _owner, _sections
from .memory_backup import _read
from .memory_canonical import corpus
from .memory_sources import _strings
from .memory_transaction import publish


KNOWLEDGE='LIFEOS/MEMORY/KNOWLEDGE'
STATE=KNOWLEDGE+'/.harvest-state.json'
DOMAINS=('People','Companies','Ideas','Research')
SOURCE_LIMIT=256*1024
BATCH_LIMIT=50


def _authorize(scope):
    if not _owner(scope):
        raise MemoryUnavailable('Staged publication requires an unrestricted owner context')


def _path(memory,relative,*,file=True):
    path=memory._path(relative)
    physical=memory.root.parent/'.config/LIFEOS/USER/MEMORY'/Path(relative).relative_to('LIFEOS/MEMORY')
    if path.is_symlink() or path.resolve()!=physical or (path.exists() and file and not path.is_file()):
        raise MemoryUnavailable('A staged publication path changes its permitted physical source')
    if path.exists() and file and path.stat().st_size>SOURCE_LIMIT:
        raise MemoryUnavailable('A staged publication source exceeds its size limit')
    return path


def _selected(memory,target,all):
    if type(all) is not bool or (all and target is not None):
        raise MemoryUnavailable('Choose one staged selector or the complete staged queue')
    if not all and (not isinstance(target,str) or not target):
        raise MemoryUnavailable('Choose a native staged note')
    names=[]
    root=_path(memory,KNOWLEDGE+'/_harvest-queue',file=False)
    if root.exists() and not root.is_dir():
        raise MemoryUnavailable('The staged queue is not a directory')
    if all:
        for domain in DOMAINS:
            directory=_path(memory,KNOWLEDGE+'/_harvest-queue/'+domain,file=False)
            if directory.is_dir():
                for path in sorted(directory.iterdir()):
                    if path.suffix=='.md':names.append(domain+'/'+path.stem)
                    if len(names)>BATCH_LIMIT:raise MemoryUnavailable('The staged batch exceeds its publication limit')
    else:
        selector=target.removesuffix('.md')
        parts=selector.split('/')
        if len(parts)>2 or not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,180}',parts[-1]):
            raise MemoryUnavailable('A native staged selector has an invalid path')
        domains=DOMAINS if len(parts)==1 else tuple(domain for domain in DOMAINS if domain.casefold()==parts[0].casefold())
        names=[domain+'/'+parts[-1] for domain in domains
               if _path(memory,KNOWLEDGE+'/_harvest-queue/'+domain+'/'+parts[-1]+'.md').exists()]
    if not names or (not all and len(names)!=1):
        raise MemoryUnavailable('The staged selector is missing or ambiguous')
    return names


def _plan(memory,connection,scope,target,all,project):
    _authorize(scope)
    if not isinstance(project,str) or project=='*' or len(project)>256 or project!=project.strip():
        raise MemoryUnavailable('Choose an exact project or leave this note unclassified')
    notes=[]
    sources=[]
    for name in _selected(memory,target,all):
        source=_path(memory,KNOWLEDGE+'/_harvest-queue/'+name+'.md')
        destination=_path(memory,KNOWLEDGE+'/'+name+'.md')
        if destination.exists():
            raise MemoryUnavailable('A staged publication destination already exists')
        if not source.is_file():raise MemoryUnavailable('The native staged source is missing')
        original=source.read_text(encoding='utf-8')
        text=re.sub(r'^status: pending-review\n','',original,flags=re.MULTILINE)
        front=re.match(r'^---\n[\s\S]*?\n---\n',text)
        if front is None:raise MemoryUnavailable('Staged publication needs native note metadata')
        sections=_sections(text,text[front.end():].strip())
        if len(sections)!=1:raise MemoryUnavailable('A staged note needs one complete fact body')
        position,body=sections[0]
        timestamp=datetime.fromtimestamp(source.stat().st_mtime,timezone.utc).isoformat()
        if memory._filter_history(connection,scope,body,timestamp)['excluded']:
            raise MemoryUnavailable('The staged source is excluded by current memory policy')
        item={'type':'idea','title':'Native staged publication','content':body}
        checked=memory._native('validate',item=item)
        if not checked.get('ok') or checked.get('item')!=item:
            raise MemoryUnavailable('Native validation refuses the declared staged fact')
        notes.append({'name':name,'source':source.relative_to(memory.root).as_posix(),
                      'destination':destination.relative_to(memory.root).as_posix(),'original_digest':_digest(original),
                      'content':text,'body':body,'position':position})
        sources.append({'path':str(destination),'content':text})
    parsed=memory._native('canonical_records',root=str(memory.root/'LIFEOS/MEMORY'),sources=sources)
    for note,record,metadata in zip(notes,parsed['records'],parsed['metadata'],strict=True):
        if record['content']!=note['content']:
            raise MemoryUnavailable('Native parsing changes the declared staged note')
        if memory._filter_history(connection,scope,'\n'.join(_strings(metadata)),datetime.now(timezone.utc).isoformat())['excluded']:
            raise MemoryUnavailable('The staged metadata is excluded by current memory policy')
        note['title']=record['title']
    current=corpus(memory,scope,str(memory.root/'LIFEOS/MEMORY'),connection=connection)
    identifiers=[record['id'] for record in [*current['records'],*parsed['records']]]
    if len(set(identifiers))!=len(identifiers):
        raise MemoryUnavailable('Staged publication cannot duplicate a current native record identifier')
    sources=[{'path':str(memory.root/'LIFEOS/MEMORY'/Path(path).relative_to(current['root'])),
              'content':record['content']} for path,record in zip(current['files'],current['records'],strict=True)]+sources
    state_path=_path(memory,STATE)
    state_text=state_path.read_text() if state_path.exists() else ''
    state=json.loads(state_text) if state_text else {'lastHarvest':'1970-01-01T00:00:00Z','harvestedPaths':[],'totalHarvested':0}
    if (not isinstance(state,dict) or not isinstance(state.get('lastHarvest'),str)
            or not isinstance(state.get('harvestedPaths'),list) or not all_strings(state['harvestedPaths'])
            or type(state.get('totalHarvested')) is not int or not 0<=state['totalHarvested']<2**53-len(notes)):
        raise MemoryUnavailable('The native harvest state needs review before publication')
    try:
        if datetime.fromisoformat(state['lastHarvest'].replace('Z','+00:00')).tzinfo is None:
            raise ValueError('The harvest clock needs its timezone')
    except ValueError as error:
        raise MemoryUnavailable('The native harvest state needs a valid clock before publication') from error
    state['totalHarvested']+=len(notes)
    writes=memory._native('knowledge_indexes',sources=sources,state=state)['writes']
    allowed={str(memory.root/KNOWLEDGE/domain/'_index.md') for domain in DOMAINS}|{str(memory.root/KNOWLEDGE/'_index.md')}
    for write in writes:
        if set(write)!={'path','content'} or write['path'] not in allowed or not isinstance(write['content'],str):
            raise MemoryUnavailable('Native Knowledge rendering changes its declared index destinations')
        _path(memory,Path(write['path']).relative_to(memory.root).as_posix())
    if len(writes)!=len(allowed) or len({write['path'] for write in writes})!=len(allowed):
        raise MemoryUnavailable('Native Knowledge rendering changes its declared index set')
    identity={'root':str(memory.root),'scope':scope.signature,'project':project,'notes':notes,
              'state_before':state_text,'state':state,'writes':writes,'sources':sources}
    encoded=json.dumps(identity,sort_keys=True)
    if len(encoded.encode())>3*1024*1024:
        raise MemoryUnavailable('The staged transaction exceeds its declared source limit')
    return {'signature':_digest(encoded),'notes':notes,'state':state,'state_before':state_text,
            'indexes':writes,'project':project}


def all_strings(values):
    return all(isinstance(value,str) for value in values)


def _public(plan):
    return {'signature':plan['signature'],'project':plan['project'],'notes':[{'selector':note['name'],'title':note['title']}
                                                                         for note in plan['notes']],
            'index_files':len(plan['indexes'])}


def preview(memory,scope,target=None,*,all=False,project=''):
    _authorize(scope)
    with memory._transaction() as connection:
        return _public(_plan(memory,connection,scope,target,all,project))


def publication_paths(memory,connection,scope,payload):
    plan=_plan(memory,connection,scope,payload['target'],payload['all'],payload['project'])
    if plan['signature']!=payload['signature']:return []
    return ([name for note in plan['notes'] for name in (note['source'],note['destination'])]+[STATE]
            +[Path(write['path']).relative_to(memory.root).as_posix() for write in plan['indexes']])


def promote(memory,scope,target,signature,request_id,*,all=False,project='',source_session='',check_current=None):
    try:_authorize(scope)
    except MemoryUnavailable as error:return {'status':'rejected','reason':str(error)}
    if not isinstance(signature,str) or re.fullmatch('[0-9a-f]{64}',signature) is None:
        return {'status':'rejected','reason':'Staged publication needs the reviewed source signature'}
    def apply(connection):
        plan=_plan(memory,connection,scope,target,all,project)
        if plan['signature']!=signature:return {'status':'conflict','reason':'The staged preview changed. Review a fresh preview.'}
        if check_current is not None:check_current()
        for note in plan['notes']:
            source=_path(memory,note['source'])
            if not source.is_file() or _digest(source.read_text())!=note['original_digest']:
                return {'status':'conflict','reason':'The staged source changes during publication rendering'}
        state_path=_path(memory,STATE)
        current_state=state_path.read_text() if state_path.exists() else ''
        if current_state!=plan['state_before']:
            return {'status':'conflict','reason':'The harvest state changes during publication rendering'}
        references=[]
        for note in plan['notes']:
            destination=_path(memory,note['destination'])
            publish(destination,note['content'].encode())
            references.append(memory._record(connection,scope,destination,note['body'],'project',project,
                                              {'kind':'native-promotion','session':source_session}))
            if memory._content(connection.execute('SELECT * FROM records WHERE id=?',(references[-1]['id'],)).fetchone())!=note['body']:
                raise MemoryUnavailable('Staged publication changes its registered current fact')
        for write in plan['indexes']:publish(Path(write['path']),write['content'].encode())
        publish(_path(memory,STATE),(json.dumps(plan['state'],indent=2)+'\n').encode())
        for note in plan['notes']:_path(memory,note['source']).unlink()
        return {'status':'committed','references':references,'notes_promoted':len(references),
                'indexes_published':len(plan['indexes']),'project':project}
    return memory._operation(scope,request_id,{'operation':'staged_promote','target':target,'all':all,'project':project,
                                             'signature':signature,'source_session':source_session},apply)


def _rejection_plan(memory,scope,target,all):
    _authorize(scope)
    notes=[]
    for name in _selected(memory,target,all):
        relative=KNOWLEDGE+'/_harvest-queue/'+name+'.md'
        path=_path(memory,relative)
        info=path.stat()
        if info.st_uid!=os.getuid() or info.st_nlink!=1 or info.st_mode&0o022:
            raise MemoryUnavailable('Staged rejection requires regular unshared owner files')
        content,stamp=_read(path)
        if len(content)>SOURCE_LIMIT:
            raise MemoryUnavailable('Staged rejection exceeds its source limit')
        notes.append({'path':relative,'digest':_digest(content.hex()),'stamp':stamp})
    return notes


def rejection_paths(memory,scope,payload):
    _authorize(scope)
    notes=payload.get('notes')
    if (not isinstance(notes,list) or not 0<len(notes)<=BATCH_LIMIT
            or any(not isinstance(note,dict) or set(note)!={'path','digest','stamp'}
                   or not isinstance(note['path'],str) or re.fullmatch(
                       r'LIFEOS/MEMORY/KNOWLEDGE/_harvest-queue/(People|Companies|Ideas|Research)/[a-z0-9][a-z0-9_-]{0,180}\.md',
                       note['path']) is None for note in notes)
            or len({note['path'] for note in notes})!=len(notes)):
        raise MemoryUnavailable('Staged rejection requires bounded reviewed queue paths')
    for note in notes:_path(memory,note['path'])
    return [note['path'] for note in notes]


def reject(memory,scope,target,request_id,*,all=False,source_session='',check_current=None):
    _authorize(scope)
    if check_current is not None:check_current()
    identity={'operation':'staged_reject','target':target,'all':all,'source_session':source_session}
    with memory._transaction() as connection:
        prior=connection.execute('SELECT 1 FROM operations WHERE writer=? AND request_id=?',
                                 (scope.writer,request_id)).fetchone()
        notes=[] if prior is not None else _rejection_plan(memory,scope,target,all)
    payload={**identity,'notes':notes}

    def apply(connection):
        current=_rejection_plan(memory,scope,target,all)
        if current!=notes:
            return {'status':'conflict','reason':'The staged queue changes before rejection'}
        if check_current is not None:check_current()
        if _rejection_plan(memory,scope,target,all)!=notes:
            return {'status':'conflict','reason':'The staged queue changes during rejection authorization'}
        for relative in rejection_paths(memory,scope,payload):_path(memory,relative).unlink()
        return {'status':'committed','notes_rejected':len(notes)}

    return memory._operation(scope,request_id,payload,apply,identity_payload=identity)
