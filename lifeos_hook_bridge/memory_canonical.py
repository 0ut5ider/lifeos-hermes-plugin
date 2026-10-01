# ABOUTME: Supplies registered current native notes to the alternate Cortex reader.
# ABOUTME: Authorizes roots and filters canonical metadata without admitting raw history.
from datetime import datetime, timezone
from contextlib import nullcontext
import json
from pathlib import Path
import re

from .memory_access import MemoryUnavailable
from .memory_sources import authorize, _strings


RESPONSE_LIMIT = 3 * 1024 * 1024


def corpus(memory, scope, root: str, *, connection=None) -> dict:
    authorize(scope)
    if not isinstance(root,str) or not Path(root).is_absolute():
        raise MemoryUnavailable('Canonical recall needs the installed memory root')
    with (memory._transaction() if connection is None else nullcontext(connection)) as connection:
        physical=memory.root.parent/'.config/LIFEOS/USER/MEMORY'
        requested=Path(root).resolve()
        if requested not in (physical,physical/'KNOWLEDGE'):
            raise MemoryUnavailable('Canonical recall cannot select another memory root')
        grouped={}
        for row in connection.execute("SELECT * FROM records WHERE status='active' AND category='project' ORDER BY path,position"):
            relative=Path(row['path'])
            if (not row['path'].startswith('LIFEOS/MEMORY/KNOWLEDGE/') or relative.suffix!='.md'
                    or any(part.startswith(('_','.')) for part in relative.parts[3:])):
                continue
            if not memory._allowed(scope,row):
                raise MemoryUnavailable('Canonical recall needs every selected source grant')
            grouped.setdefault(row['path'],[]).append(row)
        sources=[]
        source_bytes=2
        for relative,rows in grouped.items():
            source=memory._path(relative)
            expected=physical/Path(relative).relative_to('LIFEOS/MEMORY')
            if source.resolve()!=expected or not source.is_file():
                raise MemoryUnavailable('Canonical recall requires its permitted physical source')
            if source.stat().st_size>8*1024*1024:
                raise MemoryUnavailable('Canonical source exceeds the native file limit')
            entries=[memory._content(row) for row in rows]
            text=source.read_text(encoding='utf-8')
            front=re.match(r'^---\n.*?\n---\n',text,re.DOTALL)
            if front is None:
                raise MemoryUnavailable('Canonical recall requires the native note metadata')
            header=front.group()
            source={'path':str(expected),'content':header+'\n'+'\n\n'.join(entries)}
            source_bytes+=len(json.dumps(source).encode())+(2 if sources else 0)
            sources.append(source)
            if source_bytes>RESPONSE_LIMIT:
                raise MemoryUnavailable('The declared canonical sources exceed their transport limit')
        parsed=memory._native('canonical_records',root=str(requested),sources=sources)
        if len(parsed['records'])!=len(sources) or len(parsed['metadata'])!=len(sources):
            raise MemoryUnavailable('Native canonical parsing changed its declared sources')
        if len({record['id'] for record in parsed['records']})!=len(parsed['records']):
            raise MemoryUnavailable('The canonical source declares duplicate native record identifiers')
        for source,record,metadata in zip(sources,parsed['records'],parsed['metadata'],strict=True):
            if record['content']!=source['content']:
                raise MemoryUnavailable('Native canonical parsing changes the declared source text')
            labels='\n'.join([*_strings(metadata),record['id'],record['title'],
                              *record['related'],
                              record['provenance']['session'] or ''])
            if memory._filter_history(connection,scope,labels,datetime.now(timezone.utc).isoformat())['excluded']:
                raise MemoryUnavailable('Canonical metadata contains an excluded claim')
        result={'ok':True,'root':str(requested),'files':[source['path'] for source in sources],
                'records':parsed['records']}
        if len(json.dumps(result).encode())>RESPONSE_LIMIT:
            raise MemoryUnavailable('The governed canonical response exceeds its transport limit')
        return result
