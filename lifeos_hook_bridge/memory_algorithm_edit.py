# ABOUTME: Runs native Algorithm edits in admitted snapshots before private owner publication.
# ABOUTME: Preserves source changes, immutable versions, and the current owner publication boundary.
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import subprocess
from uuid import uuid4

from .memory_access import MemoryConflict, MemoryUnavailable
from .memory_algorithm_summary import _output, _request
from .memory_algorithm_tab import _catalog, _collect, DIRECTORY, VERSION
from .memory_source_review import _retirement_digest
from .memory_sources import SOURCE_LIMIT, CORPUS_LIMIT
from .memory_tab_freshness import _checked
from .memory_transaction import publish as _publish


def publish(path, data):
    path = Path(path)
    if path.parts[-3:-1] != ('LIFEOS', 'ALGORITHM') or re.fullmatch('v' + VERSION + r'\.md', path.name) is None:
        _publish(path, data)
        return
    temporary = path.with_name('.memory-version-' + uuid4().hex)
    try:
        _publish(temporary, data)
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(descriptor)
    finally: os.close(descriptor)


def system_publication(name):
    return name in {'CLAUDE.md', 'LIFEOS/LIFEOS_SYSTEM_PROMPT.md', DIRECTORY + '/LATEST', DIRECTORY + '/changelog.md'} or (
        re.fullmatch(DIRECTORY + '/v' + VERSION + r'\.md', name) is not None
        or re.fullmatch(r'hooks/[A-Za-z][A-Za-z0-9-]{0,95}\.hook\.ts', name) is not None
        or name in {'LIFEOS/DOCUMENTATION/ISA/ISAFormat.md', 'LIFEOS/DOCUMENTATION/ISA/ISASystem.md',
            'skills/ISA/SKILL.md'})


def _target(target, body):
    if target not in {'/api/algorithm-tab/file', '/api/algorithm-tab/doctrine'}:
        raise LookupError('Choose a declared Algorithm edit route')
    fields = {'id', 'content', 'expectedMtime'} if target.endswith('/file') else {'content', 'bump', 'note'}
    required = fields - {'expectedMtime'}
    if (not isinstance(body, dict) or not required <= set(body) or set(body) - fields
            or any(not isinstance(value, str) for value in body.values())
            or len(json.dumps(body, ensure_ascii=False).encode()) > SOURCE_LIMIT
            or len(body['content'].encode()) > SOURCE_LIMIT):
        raise ValueError('Choose bounded native Algorithm edit fields')


def publication_paths(memory, scope, payload):
    _request(scope)
    if (set(payload) != {'operation', 'paths'} or payload['operation'] != 'algorithm_edit'
            or not isinstance(payload['paths'], list) or not 1 <= len(payload['paths']) <= 3
            or len(set(payload['paths'])) != len(payload['paths'])):
        raise ValueError('Choose fixed Algorithm edit publication paths')
    catalog = _catalog(memory)
    for name in payload['paths']:
        if not isinstance(name, str) or name not in catalog.values() and not system_publication(name):
            raise ValueError('Choose a fixed Algorithm edit publication path')
        _checked(memory, memory._publication_path(name))
    return payload['paths']


def _render(memory, target, body, admitted):
    sources, _, metadata, versions, _ = admitted
    with tempfile.TemporaryDirectory(prefix='lifeos-algorithm-edit-') as directory:
        home = Path(directory)
        root = home / '.claude'
        root.mkdir(mode=0o700)
        user = home / '.config/LIFEOS/USER'
        user.mkdir(parents=True, mode=0o700)
        (user / 'MEMORY').mkdir(mode=0o700)
        (root / 'LIFEOS').mkdir(mode=0o700)
        (root / 'LIFEOS/USER').symlink_to(user)
        (root / 'LIFEOS/MEMORY').symlink_to(user / 'MEMORY')
        for relative in ('LIFEOS/TOOLS', 'LIFEOS/PULSE'):
            (root / relative).symlink_to(memory.root / relative, target_is_directory=True)
        for row in sources:
            path = root / row['relative']
            publish(path, row['content'].encode())
            stamp = round(metadata[row['relative']]['modified'] * 1000000)
            os.utime(path, ns=(stamp, stamp))
        directory_path = root / DIRECTORY
        directory_path.mkdir(parents=True, exist_ok=True, mode=0o700)
        for name in versions:
            if not (directory_path / name).exists(): publish(directory_path / name, b'')
        environment = {key: value for key, value in os.environ.items() if not key.startswith(('GIT_',
            'LIFEOS_MEMORY_', 'HERMES_SESSION_', 'HERMES_CRON_'))}
        environment.pop('LIFEOS_CONFIG_PATH', None)
        environment.update(HOME=str(home), CLAUDE_CONFIG_DIR=str(root), LIFEOS_DIR=str(root / 'LIFEOS'),
            LIFEOS_CONFIG_DIR=str(user / 'CONFIG'), LIFEOS_MEMORY_INTERNAL='1', BUN_CONFIG_NO_AUTO_INSTALL='1',
            GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull, GIT_CEILING_DIRECTORIES=str(home))
        rendered = subprocess.run([memory.bun, '--no-install', str(memory.worker), str(root)],
            input=json.dumps({'action': 'algorithm_edit_render', 'target': target, 'body': body}),
            capture_output=True, text=True, timeout=30, env=environment, cwd=root)
        if rendered.returncode or len(rendered.stdout.encode()) > CORPUS_LIMIT:
            raise MemoryUnavailable('Native Algorithm editing refuses the admitted snapshot')
        try: result = json.loads(rendered.stdout)
        except ValueError as error:
            raise MemoryUnavailable('Native Algorithm editing returns an invalid snapshot response') from error
        if (not isinstance(result, dict) or set(result) != {'status', 'body'} or type(result['status']) is not int
                or result['status'] not in {200, 400, 403, 404, 409, 422} or not isinstance(result['body'], dict)):
            raise MemoryUnavailable('Native Algorithm editing changes its response fields')
        if result['status'] != 200: return result, {}
        if target.endswith('/file'):
            names = [_catalog(memory).get(body['id'])]
            if names[0] is None or '{LATEST}' in names[0]:
                raise MemoryUnavailable('Native Algorithm file editing changes its declared source')
        else:
            version = result['body'].get('version')
            if not isinstance(version, str) or re.fullmatch(VERSION, version) is None:
                raise MemoryUnavailable('Native Algorithm editing changes its version')
            names = [DIRECTORY + '/' + name for name in ('v' + version + '.md', 'changelog.md', 'LATEST')]
        changes = {name: (root / name).read_text(encoding='utf-8') for name in names}
        if any(len(text.encode()) > SOURCE_LIMIT for text in changes.values()) or len(json.dumps(changes).encode()) > CORPUS_LIMIT:
            raise MemoryUnavailable('Native Algorithm edits exceed their publication limit')
        return result, changes


def _matches(memory, admitted, changes):
    _, fingerprints, _, _, directory = admitted
    for row in fingerprints:
        name, expected = row[:2]
        if name in changes: continue
        path = _checked(memory, memory.root / name)
        if expected is None:
            if path.exists(): return False
        elif not path.is_file(): return False
        else:
            info = path.stat()
            keys = (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
            if keys != expected or len(row) > 2 and path.read_bytes() != row[2]: return False
    path = _checked(memory, memory.root / DIRECTORY)
    info = path.stat()
    expected_names = set(directory[3]) | {Path(name).name for name in changes if name.startswith(DIRECTORY + '/')}
    if (info.st_dev, info.st_ino) != directory[:2] or {item.name for item in path.iterdir()} != expected_names:
        return False
    if not any(name.startswith(DIRECTORY + '/') for name in changes) and info.st_mtime_ns != directory[2]: return False
    return all(_checked(memory, memory._publication_path(name)).read_bytes() == text.encode() for name, text in changes.items())


def edit(memory, scope, target, body, *, check_current):
    _target(target, body)
    _request(scope)
    check_current()
    with memory._transaction() as connection:
        catalog = _catalog(memory)
        admitted = _collect(memory, scope, connection, '/api/algorithm-tab', catalog)
        retired = _retirement_digest(connection)
        _output(memory, scope, connection, body)
        result, changes = _render(memory, target, body, admitted)
        _output(memory, scope, connection, result)
        _output(memory, scope, connection, changes)
        check_current()
        if _collect(memory, scope, connection, '/api/algorithm-tab', catalog) != admitted:
            raise MemoryConflict('Algorithm sources change during native edit rendering')
        if not changes: return result
        payload = {'operation': 'algorithm_edit', 'paths': sorted(changes)}
        publication_paths(memory, scope, payload)
    response = result['body']
    def apply(connection):
        check_current()
        if (_retirement_digest(connection) != retired
                or _collect(memory, scope, connection, '/api/algorithm-tab', catalog) != admitted):
            raise MemoryConflict('Algorithm sources change before native edit publication')
        publication_paths(memory, scope, payload)
        for name, text in changes.items():
            check_current()
            publish(memory._publication_path(name), text.encode())
        check_current()
        if not _matches(memory, admitted, changes):
            raise MemoryUnavailable('Algorithm publication preserves later source edits and requires recovery')
        if target.endswith('/file'):
            name = next(iter(changes))
            message = 'fix(algorithm): save file\n\nThe owner saves ' + name + '.'
        else:
            message = 'feat(algorithm): publish doctrine\n\nThe owner publishes version ' + response['version'] + '.\n' + body['note'].strip().split('\n')[0][:100]
        response['commit'] = memory._native('algorithm_edit_commit', paths=list(changes), message=message)
        check_current()
        if not _matches(memory, admitted, changes) or _retirement_digest(connection) != retired:
            raise MemoryUnavailable('Algorithm commit preserves later source and authority changes and requires recovery')
        if target.endswith('/file'):
            info = memory._publication_path(next(iter(changes))).stat()
            seconds, milliseconds = divmod(int(info.st_mtime_ns / 1000000), 1000)
            response['mtime'] = datetime.fromtimestamp(seconds, timezone.utc).isoformat(timespec='seconds').replace(
                '+00:00', f'.{milliseconds:03d}Z')
        _output(memory, scope, connection, response)
        return {'status': 'committed', 'response': response}
    receipt = memory._operation(scope, 'algorithm-edit-' + uuid4().hex, payload, apply,
        publication_digests={name: hashlib.sha256(text.encode()).hexdigest() for name, text in changes.items()})
    check_current()
    if receipt['status'] != 'committed': raise MemoryUnavailable('Algorithm edit publication needs recovery')
    with memory._transaction() as connection:
        check_current()
        if _retirement_digest(connection) != retired or not _matches(memory, admitted, changes):
            raise MemoryUnavailable('Algorithm delivery preserves later source and authority changes')
        _output(memory, scope, connection, receipt['response'])
        check_current()
    return {'status': 200, 'body': receipt['response']}
