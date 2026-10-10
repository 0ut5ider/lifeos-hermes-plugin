# ABOUTME: Reads and edits declared TELOS files under current authenticated owner authority.
# ABOUTME: Binds owner saves to exact source references and recovers interrupted private publication.
from datetime import datetime, timezone
import hashlib
import json
import re
from urllib.parse import parse_qs, urlencode, urlsplit

from .memory_access import MemoryConflict, MemoryUnavailable, _digest
from .memory_policy import CATEGORIES
from .memory_source_review import _retirement_digest, _source_digest
from .memory_sources import authorize, _admit, _markdown_source, SOURCE_LIMIT, TELOS_EDITOR_SOURCES
from .memory_tab_freshness import _checked
from .memory_transaction import publish


PREFIX = 'LIFEOS/USER/TELOS/'
NAMES = frozenset(path.removeprefix(PREFIX) for path in TELOS_EDITOR_SOURCES)


def validate_name(value):
    if not isinstance(value, str) or value not in NAMES:
        raise ValueError('Choose one declared TELOS file')
    return value


def request_target(value):
    if not isinstance(value, str) or len(value) > 256:
        raise ValueError('Choose one bounded TELOS file route')
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc or parsed.fragment or parsed.path != '/api/telos/file':
        raise ValueError('TELOS files require their fixed installed route')
    query = parse_qs(parsed.query, keep_blank_values=True, strict_parsing=True)
    if set(query) != {'name'} or len(query['name']) != 1:
        raise ValueError('Choose exactly one declared TELOS filename')
    return parsed.path + '?' + urlencode({'name': validate_name(query['name'][0])})


def _snapshot(memory, scope, connection, filename):
    authorize(scope)
    if not scope.principal:
        raise MemoryUnavailable('TELOS files require a bound owner')
    filename = validate_name(filename)
    registry = memory._native('telos_file_names')
    if set(registry) != {'filenames'} or not isinstance(registry['filenames'], list) or set(registry['filenames']) != NAMES:
        raise MemoryUnavailable('Native TELOS files change their declared registry')
    relative = PREFIX + filename
    path = _checked(memory, memory.root / relative)
    content = ''
    mtime = None
    fingerprint = None
    if path.exists():
        source, timestamp = _markdown_source(memory, scope, str(path))
        content = source['content']
        if (memory._native('validate_source_batch', contents=[content + '\n' + relative])['accepted'] != [True]
                or _admit(memory, connection, scope, content, relative, timestamp)['excluded']):
            raise MemoryUnavailable('The TELOS file requires current safe owner source review')
        info = _checked(memory, path).stat()
        fingerprint = (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
        mtime = datetime.fromisoformat(source['lastModified']).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
    result = {'name': filename, 'content': content, 'mtime': mtime, 'missing': fingerprint is None}
    result['reference'] = _digest(json.dumps({'root': str(memory.root), 'principal': scope.principal,
        'scope': scope.signature, 'source': result, 'fingerprint': fingerprint,
        'retirement': _retirement_digest(connection)}, sort_keys=True))
    return result


def view(memory, scope, target, *, check_current):
    target = request_target(target)
    filename = parse_qs(urlsplit(target).query)['name'][0]
    check_current()
    with memory._transaction() as connection:
        snapshot = _snapshot(memory, scope, connection, filename)
        check_current()
        if _snapshot(memory, scope, connection, filename) != snapshot:
            raise MemoryConflict('The TELOS file changes before owner delivery')
        check_current()
        return {'status': 200, 'body': snapshot}


def publication_paths(memory, scope, payload):
    authorize(scope)
    if not scope.principal or not CATEGORIES <= set(scope.write):
        raise MemoryUnavailable('TELOS saves require unrestricted owner write authority')
    relative = PREFIX + validate_name(payload['name'])
    path = _checked(memory, memory.root / relative)
    if path.exists() and (not path.is_file() or path.stat().st_size > SOURCE_LIMIT):
        raise MemoryUnavailable('The TELOS destination requires a bounded regular owner file')
    return [relative]


def edit(memory, scope, *, name, content, reference, request_id, check_current):
    filename = validate_name(name)
    if (not isinstance(content, str) or len(content.encode()) > SOURCE_LIMIT
            or not isinstance(reference, str) or re.fullmatch('[0-9a-f]{64}', reference) is None
            or not isinstance(request_id, str) or not 1 <= len(request_id) <= 256):
        raise ValueError('TELOS saves require bounded text, a current reference, and a request identifier')
    payload = {'operation': 'telos_file_edit', 'name': filename}
    publication_paths(memory, scope, payload)
    check_current()
    relative = PREFIX + filename
    data = content.encode()
    digest = hashlib.sha256(data).hexdigest()
    identity = {**payload, 'content': content, 'reference': reference, 'scope': scope.signature}
    with memory._transaction() as connection:
        prior = connection.execute('SELECT * FROM operations WHERE writer=? AND request_id=?',
            (scope.writer, request_id)).fetchone()
        if prior is not None:
            if prior['payload_digest'] != _digest(json.dumps(identity, sort_keys=True)):
                raise MemoryConflict('The TELOS request identifier names another edit')
            receipt = json.loads(prior['receipt'])
            current = _snapshot(memory, scope, connection, filename)
            if receipt.get('status') != 'committed' or receipt.get('reference') != current['reference']:
                raise MemoryConflict('The TELOS retry preserves a later source or policy change')
            check_current()
            return receipt['result']
        before = _snapshot(memory, scope, connection, filename)
        if before['reference'] != reference:
            raise MemoryConflict('The TELOS file changes after the owner opens it')
        if connection.execute("SELECT 1 FROM records WHERE path=? AND status='active' LIMIT 1", (relative,)).fetchone():
            raise MemoryUnavailable('A registered fact source requires explicit fact correction')
        checked = content + '\n' + relative
        if (memory._native('validate_source_batch', contents=[checked])['accepted'] != [True]
                or memory._filter_history(connection, scope, checked,
                    datetime.now(timezone.utc).isoformat(), reviewed=True)['excluded']):
            raise MemoryUnavailable('The TELOS edit contains private or known retired text')
        check_current()

    def apply(connection):
        check_current()
        if _snapshot(memory, scope, connection, filename) != before:
            raise MemoryConflict('The TELOS file changes before publication')
        publication_paths(memory, scope, payload)
        if connection.execute("SELECT 1 FROM records WHERE path=? AND status='active' LIMIT 1", (relative,)).fetchone():
            raise MemoryConflict('The TELOS source becomes a registered fact before publication')
        publish(_checked(memory, memory.root / relative), data)
        connection.execute('INSERT OR REPLACE INTO source_reviews VALUES (?,?,?,?,?,?)',
            (scope.principal, relative, _source_digest(memory, scope, relative, content),
             _retirement_digest(connection), scope.writer, datetime.now(timezone.utc).isoformat()))
        after = _snapshot(memory, scope, connection, filename)
        check_current()
        result = {'status': 200, 'body': {'ok': True, 'mtime': after['mtime'], 'reference': after['reference']}}
        return {'status': 'committed', 'reference': after['reference'], 'result': result}

    receipt = memory._operation(scope, request_id, payload, apply, identity_payload=identity,
        publication_digests={relative: digest})
    if receipt['status'] != 'committed':
        raise MemoryConflict('The TELOS edit does not complete its recoverable publication')
    with memory._transaction() as connection:
        if _snapshot(memory, scope, connection, filename)['reference'] != receipt['reference']:
            raise MemoryConflict('The TELOS save response preserves a later source or policy change')
        check_current()
        return receipt['result']
