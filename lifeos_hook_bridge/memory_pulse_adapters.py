# ABOUTME: Admits native PULSE adapter sources and fixed data-plane operations.
# ABOUTME: Keeps cached data, errors, indexes, and adapter logs under current owner authority.
import hashlib
import json
import os
from pathlib import Path
import re
import time
from uuid import uuid4

from .memory_access import MemoryUnavailable, MemoryConflict, _now
from .memory_evidence import _signature
from .memory_sources import (authorize, _text_source, _admit, json_projection, markdown_projection,
    is_sync_source, is_evidence_source, is_deny_source, SOURCE_LIMIT, SOURCE_COUNT_LIMIT, CORPUS_LIMIT)
from .memory_transaction import publish


LOG = 'LIFEOS/MEMORY/OBSERVABILITY/adapter-runs.jsonl'
DATA = 'LIFEOS/MEMORY/PULSE_DATA/'


def _id(value):
    if not isinstance(value, str) or re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,127}', value) is None:
        raise ValueError('Choose a bounded native PULSE page identifier')
    return value


def _target(memory, relative):
    path = memory._publication_path(relative)
    physical = memory.root.parent / '.config/LIFEOS/USER' / Path(relative).relative_to('LIFEOS')
    if (path.resolve() != physical.absolute() or path.is_symlink()
            or path.exists() and (not path.is_file() or path.stat().st_uid != os.getuid()
                                 or path.stat().st_nlink != 1 or path.stat().st_size > CORPUS_LIMIT)):
        raise MemoryUnavailable('PULSE data changes its fixed owner destination')
    return path


def _write(scope):
    authorize(scope)
    if not {'principal', 'assistant', 'project'} <= set(scope.write):
        raise MemoryUnavailable('PULSE publication requires unrestricted owner write access')


def _source(memory, scope, connection, path):
    relative = Path(path).relative_to(memory.root).as_posix()
    source, timestamp = _text_source(memory, scope, str(path), suffix=Path(path).suffix,
        derived_sync=is_sync_source(relative), evidence=is_evidence_source(relative),
        deny_hashes=is_deny_source(relative) and not is_sync_source(relative), preserve_newlines=True)
    if Path(path).stat().st_uid != os.getuid() or Path(path).stat().st_nlink != 1:
        raise MemoryUnavailable('PULSE inputs require regular owner sources')
    projection = (json_projection(source['content']) if relative.endswith('.json') else
                  markdown_projection(memory, relative, source['content']))
    accepted = memory._native('validate_source_batch', contents=[(projection or '') + '\n' + source['path']])['accepted']
    admitted = projection is not None and accepted == [True] and not _admit(memory, connection, scope,
        source['content'], relative, timestamp, projection=projection)['excluded']
    return source, admitted


def _manifests(memory, scope, connection):
    authorize(scope)
    directory = memory.root / 'LIFEOS/PULSE/pages'
    if directory.is_symlink() or directory.resolve() != memory.physical_root / 'LIFEOS/PULSE/pages':
        raise MemoryUnavailable('PULSE manifests change their installed directory')
    files = list(directory.glob('*.manifest.toml')) if directory.exists() else []
    if len(files) > SOURCE_COUNT_LIMIT:
        raise MemoryUnavailable('PULSE manifests exceed their count limit')
    result = []
    for path in sorted(files):
        source, accepted = _source(memory, scope, connection, path)
        if accepted:
            value = memory._native('pulse_manifest', content=source['content'])['manifest']
            _id(value.get('id'))
            if (not isinstance(value.get('order'), (int, float))
                    or not isinstance(value.get('sourceGlobs'), list)
                    or any(not isinstance(glob, str) for glob in value['sourceGlobs'])):
                raise MemoryUnavailable('The native PULSE manifest has invalid ordering or source globs')
            result.append((source, value))
    return result


def _manifest(memory, scope, connection, manifest):
    if not isinstance(manifest, dict):
        raise ValueError('PULSE adapter input needs its installed manifest')
    identifier = _id(manifest.get('id'))
    matches = [(source, value) for source, value in _manifests(memory, scope, connection) if value['id'] == identifier]
    if len(matches) != 1 or matches[0][1] != manifest:
        raise MemoryUnavailable('The PULSE request changes its current installed manifest')
    return matches[0][0]


def manifests(memory, scope, *, path=None, check_current):
    with memory._transaction() as connection:
        current = _manifests(memory, scope, connection)
        check_current()
        if _manifests(memory, scope, connection) != current:
            raise MemoryConflict('PULSE manifests changed during collection')
        if path is not None:
            selected = [value for source, value in current if source['path'] == path]
            if len(selected) != 1:
                raise MemoryUnavailable('The PULSE manifest is not an admitted installed file')
            return {'ok': True, 'manifest': selected[0]}
        return {'ok': True, 'manifests': sorted([value for _, value in current], key=lambda value: value['order'])}


def _inputs(memory, scope, connection, manifest):
    authorize(scope)
    source_manifest = _manifest(memory, scope, connection, manifest)
    globs = manifest.get('sourceGlobs')
    if not isinstance(globs, list) or len(globs) > SOURCE_COUNT_LIMIT:
        raise ValueError('PULSE manifests need bounded native source globs')
    for pattern in globs:
        if (not isinstance(pattern, str) or len(pattern) > 4096 or Path(pattern).is_absolute()
                or '..' in Path(pattern).parts or not pattern.startswith(('LIFEOS/USER/', 'LIFEOS/MEMORY/'))):
            raise MemoryUnavailable('PULSE source globs leave their user boundary')
        parent = Path(pattern).parent.as_posix()
        if '*' in parent:
            raise MemoryUnavailable('PULSE source globs require a declared physical parent')
        directory = memory._path(parent)
        physical = memory.root.parent / '.config/LIFEOS/USER' / Path(parent).relative_to(
            'LIFEOS/USER' if parent.startswith('LIFEOS/USER/') else 'LIFEOS')
        if directory.resolve() != physical or directory.is_symlink():
            raise MemoryUnavailable('PULSE source globs change their physical parent')
    paths = memory._native('pulse_sources', manifest=manifest)['paths']
    if (not isinstance(paths, list) or len(paths) > SOURCE_COUNT_LIMIT
            or any(not isinstance(path, str) for path in paths) or len(set(paths)) != len(paths)):
        raise MemoryUnavailable('PULSE sources exceed their declared count limit')
    rows = []
    admitted = {}
    total = 0
    for path in paths:
        source, accepted = _source(memory, scope, connection, Path(path))
        rows.append(source)
        total += len(source['content'].encode())
        if total > CORPUS_LIMIT:
            raise MemoryUnavailable('PULSE source bytes exceed their corpus limit')
        if accepted:
            admitted[source['path']] = source['content']
    prompt_name = manifest.get('adapterPromptFile')
    if (not isinstance(prompt_name, str) or re.fullmatch(r'LIFEOS/PULSE/pages/[^/]+\.adapter\.md', prompt_name) is None):
        raise MemoryUnavailable('PULSE prompts require their installed page template')
    prompt_path = memory.root / prompt_name
    prompt = None
    prompt_source = None
    if prompt_path.exists() or prompt_path.is_symlink():
        if (prompt_path.resolve() != memory.physical_root / prompt_name or prompt_path.is_symlink()
                or not prompt_path.is_file() or prompt_path.stat().st_uid != os.getuid()
                or prompt_path.stat().st_nlink != 1 or prompt_path.stat().st_size > SOURCE_LIMIT):
            raise MemoryUnavailable('PULSE prompt changes its regular owner template')
        before = prompt_path.stat()
        prompt = prompt_path.read_text(encoding='utf-8')
        after = prompt_path.stat()
        if (before.st_dev, before.st_ino, before.st_mtime_ns, before.st_size) != (after.st_dev, after.st_ino, after.st_mtime_ns, after.st_size):
            raise MemoryUnavailable('The PULSE prompt changed during collection')
        projection = prompt + '\n' + prompt_name
        if (memory._native('validate_source_batch', contents=[projection])['accepted'] != [True]
                or memory._filter_history(connection, scope, projection, _now(), reviewed=True)['excluded']):
            raise MemoryUnavailable('The PULSE prompt is excluded by current policy')
        prompt_source = {'content': prompt, 'modified': after.st_mtime_ns, 'inode': after.st_ino}
    for relative in (_id(manifest['id']) + '.json', manifest['id'] + '.meta.json', manifest['id'] + '.error.json', '_index.json'):
        _target(memory, DATA + relative)
    _target(memory, LOG)
    return {'sources': admitted, 'prompt': prompt, 'raw_signature': _signature(rows),
            'manifest': source_manifest, 'prompt_source': prompt_source, 'root_binding': str(memory.physical_root)}


def inputs(memory, scope, manifest, force, *, signature=None, check_current):
    _write(scope)
    if type(force) is not bool:
        raise ValueError('PULSE adapter force mode must be a boolean')
    with memory._transaction() as connection:
        current = _inputs(memory, scope, connection, manifest)
        check_current()
        if _inputs(memory, scope, connection, manifest) != current:
            raise MemoryConflict('PULSE adapter inputs changed during collection')
        digest = _signature({'inputs': current, 'scope': scope.signature, 'force': force})
        if signature is not None and signature != digest:
            raise MemoryConflict('PULSE adapter inputs changed before execution')
        result = {'ok': True, 'sources': current['sources'], 'prompt': current['prompt'], 'signature': digest}
        if len(json.dumps(result).encode()) > CORPUS_LIMIT:
            raise MemoryUnavailable('PULSE inputs exceed their serialized transport limit')
        return result


def _admitted(memory, scope, connection, value):
    content = json.dumps(value, ensure_ascii=False, allow_nan=False)
    projection = json_projection(content)
    if len(content.encode()) > CORPUS_LIMIT:
        raise MemoryUnavailable('PULSE data exceeds its publication limit')
    return (projection is not None and memory._native('validate_source_batch', contents=[projection])['accepted'] == [True]
            and not memory._filter_history(connection, scope, projection, _now(), reviewed=True)['excluded'])


def _source_binding(memory, scope, connection, value, identifier, *, page):
    meta = value.get('_meta') if page and isinstance(value, dict) else value
    if not isinstance(meta, dict) or meta.get('pageId') != identifier or not isinstance(meta.get('sourceHashes'), dict):
        return False
    if len(meta['sourceHashes']) > SOURCE_COUNT_LIMIT:
        raise MemoryUnavailable('PULSE cache sources exceed their count limit')
    for path, digest in meta['sourceHashes'].items():
        if not isinstance(path, str) or not isinstance(digest, str) or re.fullmatch('[0-9a-f]{64}', digest) is None:
            return False
        source, accepted = _source(memory, scope, connection, Path(path))
        if not accepted or hashlib.sha256(source['content'].encode()).hexdigest() != digest:
            return False
    return True


def publication_paths(memory, scope, payload):
    _write(scope)
    for relative in payload['paths']:
        if relative != LOG and not re.fullmatch(r'LIFEOS/MEMORY/PULSE_DATA/(?:[A-Za-z0-9][A-Za-z0-9_-]{0,127}(?:\.meta|\.error)?|_index)\.json', relative):
            raise MemoryUnavailable('PULSE publication leaves its fixed data plane')
        _target(memory, relative)
    return payload['paths']


def _publish(memory, scope, values, check_current, *, check_inputs=None):
    paths = sorted(values)
    publication_paths(memory, scope, {'paths': paths})
    before = {relative: _target(memory, relative).read_bytes() if _target(memory, relative).exists() else None for relative in paths}

    def apply(connection):
        try:
            check_current()
            publication_paths(memory, scope, {'paths': paths})
            if check_inputs is not None:
                check_inputs(connection)
        except (MemoryUnavailable, OSError) as error:
            raise MemoryConflict('PULSE publication authority or destinations changed') from error
        if any((_target(memory, relative).read_bytes() if _target(memory, relative).exists() else None) != before[relative] for relative in paths):
            raise MemoryConflict('PULSE publication preserves a later destination edit')
        for relative, content in values.items():
            if content is None:
                _target(memory, relative).unlink(missing_ok=True)
            else:
                publish(_target(memory, relative), content)
        return {'status': 'committed', 'artifacts': len(paths)}

    receipt = memory._operation(scope, 'pulse-' + uuid4().hex, {'operation': 'pulse_data', 'paths': paths}, apply)
    return {'ok': receipt['status'] == 'committed', 'value': None}


def data(memory, scope, action, identifier, value, *, check_current):
    authorize(scope)
    if action == 'stale':
        if type(value) not in (int, float) or not 0 < value < 1000000:
            raise ValueError('PULSE age requires a bounded positive stale interval')
        with memory._transaction() as connection:
            path = _target(memory, DATA + _id(identifier) + '.meta.json')
            meta = json.loads(path.read_bytes()) if path.exists() else None
            if (meta is None or not _admitted(memory, scope, connection, meta)
                    or not _source_binding(memory, scope, connection, meta, identifier, page=False)):
                result = {'missing': True}
            else:
                age = (time.time_ns() - path.stat().st_mtime_ns) / (1000000000 * 3600)
                result = {'stale': age > value, 'ageHours': age}
            check_current()
            return {'ok': True, 'value': result}
    if action not in {'read_page', 'read_meta', 'read_index', 'write_page', 'write_error', 'clear_error', 'write_index'}:
        raise ValueError('Choose a supported fixed PULSE data action')
    relative = DATA + ('_index.json' if action.endswith('index') else _id(identifier) +
        ('.meta.json' if action == 'read_meta' else '.error.json' if action in {'write_error', 'clear_error'} else '.json'))
    if action.startswith('write') or action == 'clear_error':
        _write(scope)
    with memory._transaction() as connection:
        path = _target(memory, relative)
        if action.startswith('read'):
            result = json.loads(path.read_bytes()) if path.exists() else None
            if result is not None and not _admitted(memory, scope, connection, result):
                result = None
            if result is not None and action in {'read_page', 'read_meta'} and not _source_binding(
                    memory, scope, connection, result, identifier, page=action == 'read_page'):
                result = None
            check_current()
            return {'ok': True, 'value': result}
        if action != 'clear_error' and not _admitted(memory, scope, connection, value):
            raise MemoryUnavailable('PULSE output is excluded by current policy')
        if action == 'write_page':
            if memory._native('pulse_validate_page', page=value).get('valid') is not True:
                raise MemoryUnavailable('PULSE page does not match the native schema')
            if not _source_binding(memory, scope, connection, value, identifier, page=True):
                raise MemoryConflict('PULSE page sources changed before publication')
            values = {relative: (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode(),
                      DATA + identifier + '.meta.json': (json.dumps(value['_meta'], indent=2, ensure_ascii=False) + '\n').encode()}
        elif action == 'write_error':
            if not isinstance(value, dict) or set(value) - {'kind', 'message', 'details'} or any(not isinstance(value.get(key), str) for key in ('kind', 'message')):
                raise ValueError('PULSE errors require their native kind and message')
            error = {'schemaVersion': '1.0.0', 'pageId': identifier, 'occurredAt': _now(), **value}
            values = {relative: (json.dumps(error, indent=2, ensure_ascii=False) + '\n').encode()}
        elif action == 'clear_error':
            values = {relative: None}
        else:
            if not isinstance(value, list) or any(not isinstance(row, dict) or not isinstance(row.get('id'), str) for row in value):
                raise ValueError('PULSE index requires native page entries')
            index = {'schemaVersion': '1.0.0', 'generatedAt': _now(), 'pages': sorted(value, key=lambda row: row['id'])}
            values = {relative: (json.dumps(index, indent=2, ensure_ascii=False) + '\n').encode()}
        check_current()
    def check_inputs(connection):
        if action == 'write_page' and not _source_binding(memory, scope, connection, value, identifier, page=True):
            raise MemoryConflict('PULSE page sources changed before publication')

    return _publish(memory, scope, values, check_current, check_inputs=check_inputs)


def log(memory, scope, entry, *, check_current):
    _write(scope)
    with memory._transaction() as connection:
        if not isinstance(entry, dict) or not _admitted(memory, scope, connection, entry):
            raise MemoryUnavailable('PULSE adapter log is excluded by current policy')
        path = _target(memory, LOG)
        previous = path.read_bytes() if path.exists() else b''
        content = previous + (json.dumps(entry, ensure_ascii=False, separators=(',', ':')) + '\n').encode()
        if len(content) > CORPUS_LIMIT:
            raise MemoryUnavailable('PULSE adapter log exceeds its publication limit')
        check_current()
    return _publish(memory, scope, {LOG: content}, check_current)
