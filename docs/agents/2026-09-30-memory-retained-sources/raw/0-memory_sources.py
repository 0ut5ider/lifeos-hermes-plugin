# ABOUTME: Governs retained native source reads before startup summaries reach a model.
# ABOUTME: Excludes restricted, invalid, forgotten, and superseded source text without copying files.
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .memory_policy import CATEGORIES, MemoryScope


PREFIXES = ('LIFEOS/MEMORY/LEARNING/', 'LIFEOS/MEMORY/WISDOM/FRAMES/',
            'LIFEOS/MEMORY/RELATIONSHIP/', 'LIFEOS/MEMORY/WORK/', 'LIFEOS/MEMORY/STATE/progress/')
FILES = {'LIFEOS/MEMORY/STATE/learning-cache.sh', 'LIFEOS/MEMORY/STATE/session-names.json',
         'LIFEOS/MEMORY/STATE/events.jsonl'}


def read(memory, scope: MemoryScope, path: str) -> dict[str, Any]:
    rejected = {'ok':False, 'content':'', 'excluded':True}
    if not CATEGORIES <= set(scope.read) or '*' not in scope.projects:
        return {**rejected, 'reason':'This unclassified native source requires unrestricted owner recall'}
    if not isinstance(path,str):
        return {**rejected, 'reason':'A supported native source path is required'}
    relative = Path(path).relative_to(memory.root).as_posix()
    if relative not in FILES and not relative.startswith(PREFIXES):
        return {**rejected, 'reason':'This is not a supported native history or context source'}
    with memory._transaction() as connection:
        source = memory._path(relative)
        physical = memory.root.parent/'.config/LIFEOS/USER/MEMORY'/Path(relative).relative_to('LIFEOS/MEMORY')
        if source.resolve() != physical.absolute() or not source.is_file():
            return {**rejected, 'reason':'The native source is missing or changes its permitted physical path'}
        content = source.read_text(encoding='utf-8')
        checked = memory._validate({'type':'idea','title':'Native retained source','content':content},content,'project')
        if checked:
            return {**rejected, 'reason':'Native validation rejected this source text'}
        timestamp = datetime.fromtimestamp(source.stat().st_mtime,timezone.utc).isoformat()
        filtered = memory._filter_history(connection,scope,content+'\n'+relative,timestamp)
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
