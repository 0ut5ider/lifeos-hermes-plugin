# ABOUTME: Supplies registered current Knowledge notes to the native read-only schema linter.
# ABOUTME: Withholds reports when source content, retirement policy, or caller authority changes.
from datetime import datetime, timezone
from pathlib import Path

from .memory_access import MemoryUnavailable
from .memory_canonical import corpus
from .memory_sources import authorize, CORPUS_LIMIT


DIRECTORIES=frozenset(('People','Companies','Ideas','Blogs','Research','Books'))


def _sources(memory,scope,connection):
    current=corpus(memory,scope,str(memory.root/'LIFEOS/MEMORY/KNOWLEDGE'),connection=connection)
    return [{'path':str(memory.root/'LIFEOS/MEMORY/KNOWLEDGE'/Path(file).relative_to(current['root'])),
             'content':record['content']} for file,record in zip(current['files'],current['records'],strict=True)]


def run(memory,scope,*,json,list,directory,check_current=None):
    authorize(scope)
    if (not scope.principal or type(json) is not bool or type(list) is not int or not 0<=list<=10000
            or directory is not None and (not isinstance(directory,str) or directory not in DIRECTORIES)):
        raise MemoryUnavailable('Native Knowledge lint requires bounded report options and authenticated owner recall')
    if check_current is not None:check_current()
    with memory._transaction() as connection:
        sources=_sources(memory,scope,connection)
        report=memory._native('knowledge_lint',sources=sources,json=json,list=list,directory=directory)
        if check_current is not None:check_current()
        if _sources(memory,scope,connection)!=sources:
            raise MemoryUnavailable('Knowledge lint sources change during native rendering')
        if (set(report)!={'stdout'} or not isinstance(report['stdout'],str)
                or len(report['stdout'].encode())>CORPUS_LIMIT):
            raise MemoryUnavailable('Native Knowledge lint changes its declared response')
        projection=report['stdout']+'\n'+report['stdout'].replace('_',' ').replace('-',' ')
        if memory._filter_history(connection,scope,projection,datetime.now(timezone.utc).isoformat())['excluded']:
            raise MemoryUnavailable('Native Knowledge lint contains an excluded source label')
        if check_current is not None:check_current()
        return {'ok':True,'stdout':report['stdout']}
