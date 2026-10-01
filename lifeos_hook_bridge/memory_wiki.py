# ABOUTME: Selects current registered native notes for authenticated wiki read views.
# ABOUTME: Validates fixed routes and renders each request in an isolated native worker.
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlsplit

from .memory_access import MemoryUnavailable
from .memory_canonical import corpus, RESPONSE_LIMIT

DOMAINS = {'People': 'person', 'Companies': 'company', 'Ideas': 'idea',
           'Blogs': 'blog', 'Books': 'book', 'Research': 'research'}

def request_target(value: object) -> str:
    if not isinstance(value, str) or len(value) > 8192 or any(ord(char) < 32 for char in value):
        raise ValueError('Choose a fixed wiki read route')
    url = urlsplit(value)
    if url.scheme or url.netloc or url.fragment:
        raise ValueError('Wiki reads cannot select a server')
    path = url.path
    fixed = {'/api/wiki', '/api/wiki/graph', '/api/wiki/search'}
    match = re.fullmatch(r'/api/wiki/(?:doc|backlinks)/([^/]+)|/api/wiki/knowledge/([^/]+)/([^/]+)', path)
    if path not in fixed and match is None:
        raise LookupError('This wiki route is not a governed read view')
    if match:
        for part in (part for part in match.groups() if part is not None):
            if re.search(r'%(?![0-9A-Fa-f]{2})', part):
                raise ValueError('Wiki reads require valid page names')
            decoded = unquote(part, errors='strict')
            if (len(decoded) > 256 or decoded in {'.', '..'} or not decoded
                    or any(char in '/\\%' or ord(char) < 32 or ord(char) == 127 for char in decoded)):
                raise ValueError('Wiki reads require valid page names')
        path = '/'.join(quote(unquote(part, errors='strict'), safe='') for part in path.split('/'))
    query = parse_qsl(url.query, keep_blank_values=True, strict_parsing=True)
    if path != '/api/wiki/search' and query:
        raise ValueError('Only wiki search accepts query parameters')
    if (any(key not in {'q', 'limit'} for key, _ in query)
            or len({key for key, _ in query}) != len(query)):
        raise ValueError('Wiki search accepts one query and one result limit')
    for key, argument in query:
        if key == 'q' and (len(argument) > 1024 or any(ord(char) < 32 for char in argument)):
            raise ValueError('Wiki search query exceeds its limit')
        if key == 'limit' and (not re.fullmatch(r'[0-9]{1,3}', argument) or not 1 <= int(argument) <= 200):
            raise ValueError('Wiki search result limit must be between 1 and 200')
    return path + ('?' + urlencode(query) if query else '')


def view(memory, scope, target: str) -> dict:
    target = request_target(target)
    physical = memory.root.parent / '.config/LIFEOS/USER/MEMORY'
    with memory._transaction() as connection:
        current = corpus(memory, scope, str(physical), connection=connection)
        sources = []
        for record in current['records']:
            relative = Path(record['provenance']['path'])
            if len(relative.parts) != 3 or relative.parts[0] != 'KNOWLEDGE' or relative.parts[1] not in DOMAINS:
                continue
            path = physical / relative
            if str(path) not in current['files']:
                raise MemoryUnavailable('The wiki source changes its declared canonical path')
            sources.append({'path': str(path), 'content': record['content'],
                'lastModified': datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
                'category': DOMAINS[relative.parts[1]], 'slug': path.stem})
        if len(json.dumps(sources).encode()) > RESPONSE_LIMIT:
            raise MemoryUnavailable('The declared wiki sources exceed their transport limit')
        result = memory._native('wiki_view', target=target, sources=sources)
        if (set(result) != {'status', 'body'} or type(result['status']) is not int
                or result['status'] not in {200, 404} or not isinstance(result['body'], dict)
                or len(json.dumps(result).encode()) > RESPONSE_LIMIT):
            raise MemoryUnavailable('Native wiki rendering returned an invalid response')
        return result
