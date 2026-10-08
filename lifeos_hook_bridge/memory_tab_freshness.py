# ABOUTME: Collects fixed native tab metadata under current owner recall authority.
# ABOUTME: Excludes private and retired source labels and rechecks bytes and timestamps after rendering.
from datetime import datetime,timezone
from itertools import islice
import json
import os
from pathlib import Path
import re
from urllib.parse import parse_qs,urlsplit,urlencode

from .memory_access import MemoryUnavailable
from .memory_sources import authorize,SOURCE_LIMIT,SOURCE_COUNT_LIMIT,CORPUS_LIMIT,_source_time,_admit,json_projection


def request_target(value):
    if not isinstance(value,str) or len(value)>512:raise ValueError('Choose a bounded native tab route')
    parsed=urlsplit(value)
    if parsed.scheme or parsed.netloc or parsed.fragment or parsed.path!='/api/tab-freshness':
        raise ValueError('Tab freshness requires its fixed installed route')
    query=parse_qs(parsed.query,keep_blank_values=True,strict_parsing=True)
    if not query:return parsed.path
    if set(query)!={'tab'} or len(query['tab'])!=1:raise ValueError('Choose one native freshness tab')
    tab=query['tab'][0].strip().lower()
    if re.fullmatch('[a-z0-9_-]{0,64}',tab) is None:raise ValueError('Choose a bounded native freshness tab')
    return parsed.path+'?'+urlencode({'tab':tab})


def _checked(memory,path):
    try:relative=path.relative_to(memory.root).as_posix()
    except ValueError:
        allowed=memory.root.parent/'.local/state/lifeos/atlas'
        if path not in (allowed/'snapshot.json',allowed/'atlas.db'):
            raise MemoryUnavailable('Tab metadata leaves its fixed installed sources') from None
        physical=path
    else:
        if '..' in Path(relative).parts:raise MemoryUnavailable('Tab metadata leaves its installed root')
        if relative.startswith(('LIFEOS/USER/','LIFEOS/MEMORY/')):
            memory._path(relative)
            physical=memory.root.parent/'.config/LIFEOS/USER'/Path(relative).relative_to(
                'LIFEOS/USER' if relative.startswith('LIFEOS/USER/') else 'LIFEOS')
        else:physical=memory.physical_root/relative
    if path.is_symlink() or path.resolve()!=physical or path.exists() and (
            path.stat().st_uid!=os.getuid() or not (path.is_file() or path.is_dir())
            or path.is_file() and path.stat().st_nlink!=1
            or memory.database.exists() and path.samefile(memory.database)):
        raise MemoryUnavailable('Tab metadata changes its fixed physical owner source')
    return path


def _unknown(name,path):return {'name':name,'path':str(path),'exists':False,'mtime':None,'content':None}


def _collect(memory,scope,connection,specifications):
    authorize(scope)
    if not scope.principal:raise MemoryUnavailable('Tab metadata requires a bound owner')
    groups=[];candidates=[];fingerprints=[];total=0;discovered=0
    def source(name,path):
        nonlocal total
        _checked(memory,path)
        if not path.exists():return _unknown(name,path)
        before=path.stat()
        content=None
        if path.is_file() and path.suffix!='.db':
            if before.st_size>SOURCE_LIMIT:raise MemoryUnavailable('A tab source exceeds its byte limit')
            content=path.read_text(encoding='utf-8')
            total+=len(content.encode())
            if total>CORPUS_LIMIT:raise MemoryUnavailable('Tab metadata exceeds its source transport limit')
        after=path.stat()
        before_key=(before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)
        key=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns)
        _checked(memory,path)
        if before_key!=key:raise MemoryUnavailable('A tab source changes during collection')
        fingerprints.append((str(path),key,content))
        relative=os.path.relpath(path,memory.root)
        projection=json_projection(content) if content is not None and path.suffix=='.json' else content or ''
        item={'name':name,'path':str(path),'exists':True,'mtime':_source_time(after,milliseconds=True),'content':content}
        candidates.append((item,relative,projection,_source_time(after)))
        return item
    for specification in specifications:
        if (not isinstance(specification,dict) or not {'name','path'}<=set(specification)
                or not set(specification)<={'name','path','expand'}
                or not isinstance(specification['name'],str) or len(specification['name'])>128
                or not isinstance(specification['path'],str) or not Path(specification['path']).is_absolute()
                or 'expand' in specification and type(specification['expand']) is not bool):
            raise MemoryUnavailable('Native tab specifications change their declared format')
        path=_checked(memory,Path(specification['path']));name=specification['name']
        discovered+=1
        if specification.get('expand') and path.is_dir():
            entries=list(islice(path.iterdir(),SOURCE_COUNT_LIMIT+1))
            discovered+=len(entries)
            if discovered>SOURCE_COUNT_LIMIT:raise MemoryUnavailable('Tab discovery exceeds its source count limit')
            children=[]
            for entry in entries:
                if entry.suffix not in ('.md','.json','.yaml','.yml'):continue
                _checked(memory,entry)
                if entry.is_file():children.append(entry)
            items=[source(name.rstrip('/')+'/'+child.name,child) for child in children] if children else [source(name,path)]
            fingerprints.append((str(path),tuple(str(entry) for entry in entries)))
        else:items=[source(name,path)]
        groups.append((name,path,items))
    if discovered>SOURCE_COUNT_LIMIT or len(json.dumps([item for _,_,items in groups for item in items]).encode())>CORPUS_LIMIT:
        raise MemoryUnavailable('Tab metadata exceeds its declared source transport limit')
    contents=[(projection or '')+'\n'+relative+'\n'+relative.replace('_',' ').replace('-',' ')
        for _,relative,projection,_ in candidates]
    checked=memory._native('validate_source_batch',contents=contents)['accepted'] if contents else []
    excluded=set()
    knowledge_files=None
    if any(relative.startswith('LIFEOS/MEMORY/KNOWLEDGE/') and relative.endswith('.md')
            for _,relative,_,_ in candidates):
        from .memory_canonical import corpus
        physical=memory.root.parent/'.config/LIFEOS/USER/MEMORY'
        knowledge_files=set(corpus(memory,scope,str(physical),connection=connection)['files'])
    for (item,relative,projection,timestamp),accepted in zip(candidates,checked,strict=True):
        if (projection is None or accepted is not True or _admit(memory,connection,scope,item['content'] or '',
                relative,timestamp,projection=projection)['excluded']
                or knowledge_files is not None and relative.startswith('LIFEOS/MEMORY/KNOWLEDGE/')
                    and relative.endswith('.md') and str(Path(item['path']).resolve()) not in knowledge_files):
            excluded.add(item['path'])
    result=[]
    for name,path,items in groups:
        admitted=[item for item in items if item['path'] not in excluded]
        result.extend(admitted or [_unknown(name,path)])
    return result,fingerprints


def view(memory,scope,target,*,check_current=None):
    target=request_target(target)
    tab=parse_qs(urlsplit(target).query,keep_blank_values=True).get('tab',[''])[0]
    authorize(scope)
    if not scope.principal:raise MemoryUnavailable('Tab metadata requires a bound owner')
    if check_current is not None:check_current()
    specifications=memory._native('tab_freshness_specs',tab=tab).get('specifications')
    if not isinstance(specifications,list) or len(specifications)>32:
        raise MemoryUnavailable('Native tab specifications exceed their declared registry')
    with memory._transaction() as connection:
        sources,fingerprints=_collect(memory,scope,connection,specifications)
        result=memory._native('tab_freshness_view',tab=tab,sources=sources)
        if check_current is not None:check_current()
        if _collect(memory,scope,connection,specifications)!=(sources,fingerprints):
            raise MemoryUnavailable('Tab sources change during native rendering')
        if (not isinstance(result,dict) or set(result)!={'status','body'} or result['status']!=200
                or not isinstance(result['body'],dict) or len(json.dumps(result).encode())>CORPUS_LIMIT):
            raise MemoryUnavailable('Native tab freshness changes its declared response')
        text=json.dumps(result)
        if memory._filter_history(connection,scope,text+'\n'+text.replace('_',' ').replace('-',' '),
                datetime.now(timezone.utc).isoformat())['excluded']:
            raise MemoryUnavailable('Native tab freshness contains excluded source labels')
        if check_current is not None:check_current()
        return result
