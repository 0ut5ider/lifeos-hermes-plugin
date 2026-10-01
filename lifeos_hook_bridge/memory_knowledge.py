# ABOUTME: Selects registered current Knowledge notes for authenticated native Observability reads.
# ABOUTME: Restricts page routes and renders native response shapes without reopening retained files.
import json
from pathlib import Path
import re

from .memory_access import MemoryUnavailable
from .memory_canonical import corpus, RESPONSE_LIMIT


DOMAINS = frozenset({'people', 'companies', 'ideas', 'research'})


def request_target(value: object) -> str:
    if not isinstance(value, str) or len(value) > 512:
        raise ValueError('Choose a fixed Knowledge read route')
    if value == '/api/knowledge':
        return value
    if '?' in value or '#' in value or '%' in value or any(ord(char) < 32 for char in value):
        raise ValueError('Knowledge reads require an exact page route without query parameters')
    match = re.fullmatch(r'/api/knowledge/([A-Za-z]+)/([a-z0-9][a-z0-9-]{0,255})', value)
    if match is None or match[1].lower() not in DOMAINS:
        raise LookupError('This Knowledge route is not a governed read view')
    return '/api/knowledge/' + match[1].lower() + '/' + match[2]


def view(memory, scope, target: str) -> dict:
    target = request_target(target)
    physical = memory.root.parent / '.config/LIFEOS/USER/MEMORY'
    with memory._transaction() as connection:
        current = corpus(memory, scope, str(physical), connection=connection)
        sources = []
        for record in current['records']:
            relative = Path(record['provenance']['path'])
            if (len(relative.parts) != 3 or relative.parts[0] != 'KNOWLEDGE'
                    or relative.parts[1].lower() not in DOMAINS):
                continue
            if str(physical / relative) not in current['files']:
                raise MemoryUnavailable('The Knowledge source changes its declared canonical path')
            sources.append({'path': str(memory.root / 'LIFEOS/MEMORY' / relative), 'content': record['content']})
        if len(json.dumps(sources).encode()) > RESPONSE_LIMIT:
            raise MemoryUnavailable('The declared Knowledge sources exceed their transport limit')
        result = memory._native('knowledge_view', target=target, sources=sources)
        if (set(result) != {'status', 'body'} or type(result['status']) is not int
                or result['status'] not in {200, 404} or not isinstance(result['body'], dict)
                or len(json.dumps(result).encode()) > RESPONSE_LIMIT):
            raise MemoryUnavailable('Native Knowledge rendering returned an invalid response')
        return result
