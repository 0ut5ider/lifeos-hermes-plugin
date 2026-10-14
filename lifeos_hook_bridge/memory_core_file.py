# ABOUTME: Reads declared Pulse core files under current installation owner authority.
# ABOUTME: Binds private recoverable saves to current file references and preserves registered fact revisions.
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from urllib.parse import urlsplit

from .memory_access import MemoryConflict, MemoryUnavailable, _digest
from .memory_policy import CATEGORIES
from .memory_source_review import _retirement_digest
from .memory_sources import authorize, _admit, _source_time, json_projection, markdown_projection
from .memory_tab_freshness import _checked
from .memory_transaction import publish

LIMIT = 1_000_000
PROFILE_FILES = {'soul': 'SOUL.md', 'config': 'config.yaml', 'policy': 'plugins/lifeos/policy.json',
    'guard-installed': 'plugins/lifeos/guard.py', 'plugin-manifest': 'plugins/lifeos/plugin.yaml',
    'cron-jobs': 'cron/jobs.json', 'hermes-env': '.env', 'hermes-auth': 'auth.json'}
SOURCE_FILES = {'system-prompt': 'LIFEOS/LIFEOS_SYSTEM_PROMPT.md',
    'da-identity': 'LIFEOS/USER/DIGITAL_ASSISTANT/DA_IDENTITY.md',
    'da-memory': 'LIFEOS/USER/DIGITAL_ASSISTANT/DA_MEMORY.md',
    'principal-identity': 'LIFEOS/USER/PRINCIPAL/PRINCIPAL_IDENTITY.md',
    'principal-memory': 'LIFEOS/USER/PRINCIPAL/PRINCIPAL_MEMORY.md',
    'telos': 'LIFEOS/USER/TELOS/PRINCIPAL_TELOS.md', 'projects': 'LIFEOS/USER/PROJECTS.md'}
CODE_FILES = {'render-soul': 'RenderSoul.ts', 'mount': 'Mount.ts', 'policy-src': 'Policy.ts',
    'health': 'Health.ts', 'guard-src': 'plugin/guard.py', 'plugin-manifest-src': 'plugin/plugin.yaml',
    'plugin-init': 'plugin/__init__.py', 'bunker-config': 'bunker.config.ts', 'isa': 'ISA.md'}
IDS = frozenset(PROFILE_FILES) | frozenset(SOURCE_FILES) | frozenset(CODE_FILES)


def request_target(value):
    if not isinstance(value, str) or len(value) > 256:
        raise ValueError('Choose a bounded core file route')
    url = urlsplit(value)
    if url.scheme or url.netloc or url.query or url.fragment:
        raise ValueError('Core files require their fixed installed route')
    if url.path in ('/api/hermes', '/api/hermes/'):
        return '/api/hermes'
    prefix = '/api/hermes/file/'
    if not url.path.startswith(prefix) or url.path.removeprefix(prefix) not in IDS:
        raise LookupError('Choose one declared core file')
    return url.path


def _path(memory, identifier):
    if identifier in PROFILE_FILES:
        path = memory.profile / PROFILE_FILES[identifier]
        if memory.profile.resolve() != memory.physical_profile or path.parent.resolve() != path.parent:
            raise MemoryUnavailable('The core file changes its profile boundary')
        if path.is_symlink() or path.exists() and (not path.is_file() or path.stat().st_uid != os.getuid()
                or path.stat().st_nlink != 1 or memory.database.exists() and path.samefile(memory.database)):
            raise MemoryUnavailable('The core file changes its fixed owner source')
        return path
    if identifier in SOURCE_FILES:
        return _checked(memory, memory.root / SOURCE_FILES[identifier])
    if identifier in CODE_FILES:
        return _checked(memory, memory.root / 'LIFEOS/HERMES' / CODE_FILES[identifier])
    raise LookupError('Choose one declared core file')


def _registry(memory):
    value = memory._native('core_file_registry')
    rows = value.get('files')
    if not isinstance(rows, list) or len(rows) != len(IDS) or any(not isinstance(row, dict) for row in rows):
        raise MemoryUnavailable('The native core file registry changes')
    if {row.get('id') for row in rows} != IDS:
        raise MemoryUnavailable('The native core file registry changes')
    for row in rows:
        identifier = row['id']
        plane = 'runtime' if identifier in PROFILE_FILES else 'source' if identifier in SOURCE_FILES else 'code'
        if row.get('plane') != plane or row.get('path') != str(_path(memory, identifier)):
            raise MemoryUnavailable('The native core file registry changes its declared path')
        if any(not isinstance(row.get(key), str) for key in ('label', 'language', 'role')):
            raise MemoryUnavailable('The native core file metadata changes')
        if bool(row.get('sealed')) != (identifier in {'hermes-env', 'hermes-auth'}):
            raise MemoryUnavailable('The native credential boundary changes')
        if bool(row.get('generatedBy')) != (identifier in {'soul', 'policy', 'guard-installed', 'plugin-manifest', 'telos'}):
            raise MemoryUnavailable('The native generated file boundary changes')
    return {row['id']: row for row in rows}


def _display(memory, path):
    home = str(memory.root.parent)
    return str(path).replace(home + '/', '~/')


def _snapshot(memory, scope, connection, identifier, *, catalog=None):
    authorize(scope)
    if not scope.principal:
        raise MemoryUnavailable('Core files require a bound owner')
    catalog = catalog or _registry(memory)
    row = catalog[identifier]
    path = _path(memory, identifier)
    content = None
    stamp = None
    info = path.stat() if path.exists() else None
    if info is not None:
        stamp = [info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns]
        if not row.get('sealed'):
            if info.st_size > LIMIT:
                raise MemoryUnavailable('The core file exceeds its native byte limit')
            with path.open('rb') as stream:
                raw = stream.read(LIMIT + 1)
            if len(raw) > LIMIT:
                raise MemoryUnavailable('The core file exceeds its native byte limit')
            try: content = raw.decode('utf-8')
            except UnicodeError as error: raise MemoryUnavailable('The core file must contain UTF-8 text') from error
            after = _path(memory, identifier).stat()
            if stamp != [after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns]:
                raise MemoryConflict('The core file changes during review')
            _admit_content(memory, scope, connection, identifier, row, content, _source_time(info))
    relative = SOURCE_FILES.get(identifier)
    registered = bool(relative and connection.execute('SELECT 1 FROM records WHERE path=? AND status=\'active\' LIMIT 1', (relative,)).fetchone())
    meta = {key: row[key] for key in ('id', 'label', 'plane', 'language', 'role')}
    meta.update(displayPath=_display(memory, path), exists=info is not None, sealed=bool(row.get('sealed')),
        editable=info is not None and not row.get('sealed') and not row.get('generatedBy') and not registered,
        generatedBy=row.get('generatedBy'), sourceIds=row.get('sourceIds', []),
        bytes=info.st_size if info else None, lines=len(content.split('\n')) if content is not None else None,
        modified=datetime.fromtimestamp(info.st_mtime_ns / 1e9, timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z') if info else None)
    if registered: meta['editReason'] = 'Use memory correction tools to preserve registered fact references.'
    reference = _digest(json.dumps({'root': str(memory.root), 'profile': str(memory.profile),
        'principal': scope.principal, 'scope': scope.signature, 'id': identifier, 'meta': meta,
        'content': content, 'stamp': stamp, 'retirement': _retirement_digest(connection)}, sort_keys=True))
    return {'meta': meta, 'content': content, 'reference': reference}


def _admit_content(memory, scope, connection, identifier, row, content, timestamp):
    relative = SOURCE_FILES.get(identifier, 'core-file/' + identifier)
    projection = json_projection(content) if row['language'] == 'json' else markdown_projection(memory, relative, content)
    if row['language'] == 'yaml':
        from ruamel.yaml import YAML
        try:
            decoded = YAML(typ='safe').load(content)
            projection = json_projection(json.dumps(decoded)) if isinstance(decoded, dict) else None
        except Exception as error:
            raise MemoryUnavailable('The core configuration requires complete safe YAML') from error
    checked = memory._native('validate_source_batch', contents=[content, (projection or '') + '\n' + relative])
    if projection is None or checked.get('accepted') != [True, True] or _admit(memory, connection, scope,
            content, relative, timestamp, projection=projection, source_reviewed=True)['excluded']:
        raise MemoryUnavailable('The core file requires current safe owner review')


def view(memory, scope, target, *, check_current):
    target = request_target(target)
    check_current()
    with memory._transaction() as connection:
        if target == '/api/hermes':
            catalog = _registry(memory)
            before = [_snapshot(memory, scope, connection, identifier, catalog=catalog) for identifier in catalog]
            check_current()
            after = [_snapshot(memory, scope, connection, identifier, catalog=catalog) for identifier in catalog]
            if before != after: raise MemoryConflict('The core manifest changes before delivery')
            return {'status': 200, 'body': {'files': [row['meta'] for row in before], 'hermesHome': _display(memory, memory.profile),
                'health': None, 'mount': {'stale': False, 'detail': 'Use the authenticated remount action to refresh the install.', 'probed': False},
                'planes': {'runtime': 'The installed Hermes profile.', 'source': 'Current admitted owner sources.', 'code': 'Installed program files. Edits change release verification.'}}}
        identifier = target.removeprefix('/api/hermes/file/')
        if identifier in {'hermes-env', 'hermes-auth'}:
            return {'status': 403, 'body': {'error': 'Credential material is sealed.'}}
        before = _snapshot(memory, scope, connection, identifier)
        check_current()
        if before != _snapshot(memory, scope, connection, identifier):
            raise MemoryConflict('The core file changes before delivery')
        check_current()
        return {'status': 200 if before['meta']['exists'] else 404, 'body': before}


def publication_path(memory, name):
    identifier = name.removeprefix('core-file/')
    if not name.startswith('core-file/') or identifier not in IDS or identifier in {'hermes-env', 'hermes-auth', 'soul', 'policy', 'guard-installed', 'plugin-manifest', 'telos'}:
        raise MemoryUnavailable('Choose one editable declared core file')
    path = _path(memory, identifier)
    if not path.is_file() or path.stat().st_size > LIMIT:
        raise MemoryUnavailable('The core edit requires a bounded existing owner file')
    return path


def publication_paths(memory, scope, payload):
    authorize(scope)
    if not scope.principal or not CATEGORIES <= set(scope.write):
        raise MemoryUnavailable('Core saves require unrestricted owner write authority')
    identifier = payload['identifier']
    publication_path(memory, 'core-file/' + identifier)
    backup = payload['backup']
    if not isinstance(backup, str) or re.fullmatch(r'LIFEOS/MEMORY/STATE/hermes-edits/[a-z-]+\.[0-9a-f]{64}\.bak', backup) is None:
        raise MemoryUnavailable('The core backup changes its fixed private destination')
    _checked(memory, memory.root / backup)
    return ['core-file/' + identifier, backup]


def edit(memory, scope, *, identifier, content, reference, request_id, check_current):
    if identifier not in IDS or not isinstance(content, str) or len(content.encode()) > LIMIT or not isinstance(reference, str) or re.fullmatch('[0-9a-f]{64}', reference) is None or not isinstance(request_id, str) or not 1 <= len(request_id) <= 256:
        raise ValueError('Choose bounded core content, its reviewed reference, and a request identifier')
    if identifier in {'hermes-env', 'hermes-auth'}: return {'status': 403, 'body': {'error': 'Credential material is sealed.'}}
    payload = {'operation': 'core_file_edit', 'identifier': identifier,
        'backup': 'LIFEOS/MEMORY/STATE/hermes-edits/' + identifier + '.' + _digest(scope.writer + '\n' + request_id) + '.bak'}
    publication_paths(memory, scope, payload)
    check_current()
    identity = {**payload, 'content': content, 'reference': reference, 'scope': scope.signature}
    with memory._transaction() as connection:
        prior = connection.execute('SELECT * FROM operations WHERE writer=? AND request_id=?', (scope.writer, request_id)).fetchone()
        before = _snapshot(memory, scope, connection, identifier)
        if prior is not None:
            receipt = json.loads(prior['receipt'])
            if prior['payload_digest'] != _digest(json.dumps(identity, sort_keys=True)) or receipt.get('status') != 'committed' or receipt.get('reference') != before['reference']:
                raise MemoryConflict('The core retry preserves a later source or policy change')
            check_current()
            return receipt['result']
        if not before['meta']['editable']: raise MemoryUnavailable('This core file requires its governed generator or memory correction tools')
        if before['reference'] != reference: raise MemoryConflict('The core file changes after review')
        _admit_content(memory, scope, connection, identifier, before['meta'], content, datetime.now(timezone.utc).isoformat())
        if identifier in CODE_FILES and not memory._native('core_file_validate', content=content, label=before['meta']['label']).get('accepted'):
            return {'status': 422, 'body': {'error': 'Program edits must contain install-generic text.'}}
        check_current()

    def apply(connection):
        check_current()
        if _snapshot(memory, scope, connection, identifier) != before: raise MemoryConflict('The core file changes before publication')
        publication_paths(memory, scope, payload)
        publish(_checked(memory, memory.root / payload['backup']), before['content'].encode())
        publish(_path(memory, identifier), content.encode())
        after = _snapshot(memory, scope, connection, identifier)
        check_current()
        result = {'status': 200, 'body': {'ok': True, 'meta': after['meta'], 'reference': after['reference'],
            'backup': _display(memory, memory.root / payload['backup']), 'written': datetime.now(timezone.utc).isoformat(),
            'releaseModified': identifier in CODE_FILES or identifier == 'system-prompt'}}
        return {'status': 'committed', 'reference': after['reference'], 'result': result}

    receipt = memory._operation(scope, request_id, payload, apply, identity_payload=identity,
        publication_digests={'core-file/' + identifier: hashlib.sha256(content.encode()).hexdigest(),
            payload['backup']: hashlib.sha256(before['content'].encode()).hexdigest()})
    if receipt['status'] != 'committed': raise MemoryConflict('The core edit does not complete its recoverable publication')
    with memory._transaction() as connection:
        if _snapshot(memory, scope, connection, identifier)['reference'] != receipt['reference']:
            raise MemoryConflict('The core save response preserves a later source or policy change')
        check_current()
        return receipt['result']
