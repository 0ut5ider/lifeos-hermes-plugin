# ABOUTME: Supplies current admitted TELOS sources to the native morning brief renderer.
# ABOUTME: Rechecks source bytes, caller authority, and retained content before returning narration.
from datetime import datetime,timezone
import json
import os

from .memory_access import MemoryUnavailable
from .memory_sources import authorize,read_markdown,CORPUS_LIMIT,_source_path

SOURCES=tuple('LIFEOS/USER/TELOS/'+name for name in ('GOALS.md','TELOS.md','SPARKS.md','CURRENT.md'))


def _sources(memory,scope,connection):
    authorize(scope)
    if not scope.principal:raise MemoryUnavailable('Morning brief requires a bound owner')
    paths=[]
    for relative in SOURCES:
        path,_=_source_path(memory,scope,str(memory.root/relative),require_file=False)
        if path.is_symlink() or path.exists() and (path.stat().st_uid!=os.getuid() or path.stat().st_nlink!=1):
            raise MemoryUnavailable('Morning brief requires regular fixed owner sources')
        if path.exists():paths.append(str(path))
    sources=read_markdown(memory,scope,paths,connection=connection)
    result=[{'filename':source['relative'].rsplit('/',1)[1],'content':source['content']} for source in sources]
    if len(json.dumps(result).encode())>CORPUS_LIMIT:
        raise MemoryUnavailable('Morning brief sources exceed their transport limit')
    return result


def run(memory,scope,*,check_current=None):
    if check_current is not None:check_current()
    with memory._transaction() as connection:
        sources=_sources(memory,scope,connection)
        result=memory._native('morning_brief',sources=sources)
        if check_current is not None:check_current()
        if _sources(memory,scope,connection)!=sources:
            raise MemoryUnavailable('Morning brief sources change during native rendering')
        if (not isinstance(result,dict) or set(result)!={'stdout'} or not isinstance(result['stdout'],str)
                or len(result['stdout'].encode())>CORPUS_LIMIT):
            raise MemoryUnavailable('Native morning brief changes its declared output')
        if memory._filter_history(connection,scope,result['stdout'],datetime.now(timezone.utc).isoformat())['excluded']:
            raise MemoryUnavailable('Native morning brief contains excluded source text')
        if check_current is not None:check_current()
        return {'ok':True,'stdout':result['stdout']}
