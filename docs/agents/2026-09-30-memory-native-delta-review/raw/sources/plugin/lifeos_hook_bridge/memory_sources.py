# ABOUTME: Governs retained native source reads before startup summaries reach a model.
# ABOUTME: Excludes restricted, invalid, forgotten, and superseded source text without copying files.
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any

from .memory_access import MemoryUnavailable
from .memory_policy import CATEGORIES, MemoryScope


PREFIXES = ('LIFEOS/MEMORY/LEARNING/', 'LIFEOS/MEMORY/WISDOM/FRAMES/',
            'LIFEOS/MEMORY/RELATIONSHIP/', 'LIFEOS/MEMORY/WORK/', 'LIFEOS/MEMORY/STATE/progress/')
FILES = {'LIFEOS/MEMORY/STATE/learning-cache.sh', 'LIFEOS/MEMORY/STATE/session-names.json',
         'LIFEOS/MEMORY/STATE/events.jsonl'}
LOG_FILES = {'LIFEOS/MEMORY/OBSERVABILITY/memory-writes.jsonl',
             'LIFEOS/MEMORY/OBSERVABILITY/memory-health.jsonl'}
CACHE_FILES = {'LIFEOS/USER/CACHE/freshness.json'}


def authorize(scope: MemoryScope) -> dict[str, Any]:
    if not CATEGORIES <= set(scope.read) or '*' not in scope.projects:
        raise MemoryUnavailable('This unclassified native source requires unrestricted owner recall')
    return {'ok':True}


def _source_path(memory, scope: MemoryScope, path: str) -> tuple[Path, str]:
    authorize(scope)
    if not isinstance(path,str):
        raise MemoryUnavailable('A supported native source path is required')
    relative = Path(path).relative_to(memory.root).as_posix()
    if relative not in FILES | LOG_FILES | CACHE_FILES and not relative.startswith(PREFIXES):
        raise MemoryUnavailable('This is not a supported native history or context source')
    source = memory._path(relative)
    physical = memory.root.parent/'.config/LIFEOS/USER'/Path(relative).relative_to(
        'LIFEOS/USER' if relative in CACHE_FILES else 'LIFEOS')
    if source.resolve() != physical.absolute() or not source.is_file():
        raise MemoryUnavailable('The native source is missing or changes its permitted physical path')
    return source, relative


def check(memory, scope: MemoryScope, path: str) -> dict[str, Any]:
    with memory._transaction():
        _source_path(memory,scope,path)
    return {'ok':True}


def _strings(value: Any) -> list[str]:
    if isinstance(value,str):
        return [value]
    if isinstance(value,list):
        return [text for item in value for text in _strings(item)]
    if isinstance(value,dict):
        return [text for key,item in value.items() for text in [key,*_strings(item)]]
    return []


def read(memory, scope: MemoryScope, path: str) -> dict[str, Any]:
    rejected = {'ok':False, 'content':'', 'excluded':True}
    with memory._transaction() as connection:
        source, relative = _source_path(memory,scope,path)
        content = source.read_text(encoding='utf-8')
        timestamp = datetime.fromtimestamp(source.stat().st_mtime,timezone.utc).isoformat()
        if relative in LOG_FILES:
            rows = []
            for line in content.splitlines():
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(row,dict):
                    continue
                decoded = '\n'.join(_strings(row))
                text = line + '\n' + decoded
                if memory._validate({'type':'idea','title':'Native retained log','content':text},text,'project'):
                    continue
                row_timestamp = row.get('ts') if isinstance(row.get('ts'),str) else timestamp
                if not memory._filter_history(connection,scope,text,row_timestamp)['excluded']:
                    rows.append(line)
            return {'ok':True, 'content':'\n'.join(rows), 'excluded':False, 'historical':True}
        decoded = ''
        if source.suffix in ('.json','.jsonl'):
            values = ([json.loads(line) for line in content.splitlines() if line.strip()]
                      if source.suffix == '.jsonl' else [json.loads(content)])
            decoded = '\n'.join(text for value in values for text in _strings(value))
        for text in (content,decoded) if decoded else (content,):
            checked = memory._validate({'type':'idea','title':'Native retained source','content':text},text,'project')
            if checked:
                return {**rejected, 'reason':'Native validation rejected this source text'}
        labels = re.sub(r'(^|/)\d{8}-\d{6}_',r'\1',relative).replace('-',' ')
        filtered = memory._filter_history(connection,scope,'\n'.join((content,decoded,relative,labels)),timestamp)
        if filtered['excluded']:
            return {**rejected, 'reason':'This retained source predates a correction or contains a removed claim'}
        return {'ok':True, 'content':content, 'excluded':False, 'historical':relative.startswith('LIFEOS/MEMORY/LEARNING/')}


def filter_content(memory, scope: MemoryScope, content: str, timestamp: str) -> dict[str, Any]:
    if (not CATEGORIES <= set(scope.read) or '*' not in scope.projects
            or not isinstance(content,str) or not isinstance(timestamp,str)):
        return {'content':'', 'excluded':True}
    if memory._validate({'type':'idea','title':'Native retained context','content':content},content,'project'):
        return {'content':'', 'excluded':True}
    return memory.filter_history(scope,content,timestamp)
