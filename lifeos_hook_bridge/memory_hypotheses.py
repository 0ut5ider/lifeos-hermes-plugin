# ABOUTME: Admits current inputs for native hypothesis derivation.
# ABOUTME: Publishes notes, expiry moves, state, logs, and daily stamps in one recovery operation.
from datetime import datetime, timezone
from itertools import islice
import hashlib
import json
import os
from pathlib import Path
import re
import tomllib

from .memory_access import MemoryConflict, MemoryUnavailable
from .memory_sources import authorize, read_markdown, SOURCE_LIMIT, SOURCE_COUNT_LIMIT, CORPUS_LIMIT, json_projection
from .memory_learning import _collect as collect_ratings
from .memory_recurrence import _collect as collect_recurrence, _path, _entries, _authorize_write
from .memory_wisdom import _frames
from .memory_transaction import publish

PREFIX = 'LIFEOS/MEMORY/WISDOM/FRAMES/_hypotheses/'
LOG = 'LIFEOS/MEMORY/OBSERVABILITY/deriver.log'
STAMP = 'LIFEOS/MEMORY/OBSERVABILITY/deriver-lastrun.date'


def _read(memory, relative):
    target = _path(memory, relative)
    if not target.exists():
        return None
    if target.stat().st_size > SOURCE_LIMIT:
        raise MemoryUnavailable('The hypothesis source exceeds its byte limit')
    return target.read_text()


def _identity(memory, scope, connection):
    relative = 'LIFEOS/USER/PRINCIPAL/PRINCIPAL_IDENTITY.md'
    target = memory._path(relative)
    admitted = read_markdown(memory, scope, [str(target)], connection=connection) if target.exists() else []
    if target.exists() and len(admitted) != 1:
        raise MemoryUnavailable('The hypothesis principal identity is excluded')
    config_path = memory._path('LIFEOS/USER/CONFIG/LIFEOS_CONFIG.toml')
    configured = os.environ.get('LIFEOS_CONFIG_PATH')
    if configured and Path(configured).absolute() != config_path:
        raise MemoryUnavailable('Hypothesis identity requires its installed configuration')
    raw_config = None
    projected = []
    if config_path.exists():
        if config_path.is_symlink() or not config_path.is_file() or config_path.stat().st_uid != os.getuid() or config_path.stat().st_nlink != 1 or config_path.stat().st_size > SOURCE_LIMIT:
            raise MemoryUnavailable('Hypothesis identity configuration changes its fixed owner source')
        raw_config = config_path.read_text()
        try:
            value = tomllib.loads(raw_config)
            paths = value.get('paths', {})
            if not isinstance(paths, dict):
                raise MemoryUnavailable('Hypothesis identity requires a native path configuration table')
            user = paths.get('userDir', paths.get('user_dir'))
            if user:
                if not isinstance(user, str):
                    raise MemoryUnavailable('Hypothesis identity requires one native user path')
                selected = str(memory.root.parent) + user[1:] if user.startswith('~') else user
                selected_path = Path(selected) if Path(selected).is_absolute() else memory.root / selected
            if user and selected_path.resolve() != (memory.root / 'LIFEOS/USER').resolve():
                raise MemoryUnavailable('Hypothesis identity configuration redirects its user directory')
            projected.append(json_projection(json.dumps(value.get('principal', {}))) or '')
        except tomllib.TOMLDecodeError:
            pass
    settings_path = memory.root / 'settings.json'
    settings = None
    if settings_path.exists() or settings_path.is_symlink():
        if (settings_path.is_symlink() or not settings_path.is_file() or settings_path.stat().st_uid != os.getuid()
                or settings_path.stat().st_nlink != 1 or settings_path.stat().st_size > SOURCE_LIMIT):
            raise MemoryUnavailable('Hypothesis identity settings require their installed owner file')
        settings = settings_path.read_text()
    try:
        value = json.loads(settings or '{}')
        if isinstance(value, dict):
            projected.append(json_projection(json.dumps(value.get('principal', {}))) or '')
            environment = value.get('env', {})
            if isinstance(environment, dict):
                projected.append(json_projection(json.dumps(environment.get('PRINCIPAL', ''))) or '')
    except ValueError:
        pass
    name = memory._native('learning_principal')
    if set(name) != {'name'} or not isinstance(name['name'], str) or len(name['name']) > 256:
        raise MemoryUnavailable('The native hypothesis principal name is invalid')
    text = '\n'.join([name['name'], *projected])
    if (memory._native('validate_source_batch', contents=[text])['accepted'] != [True]
            or memory._filter_history(connection, scope, text,
                datetime.now(timezone.utc).isoformat(), reviewed=True)['excluded']):
        raise MemoryUnavailable('The hypothesis principal name is excluded')
    return {'name': name['name'], 'config': raw_config, 'settings': settings, 'identity': admitted}


def _collect(memory, scope, connection, arguments):
    authorize(scope)
    ratings = collect_ratings(memory, scope, connection, arguments['path'])
    recurrence = collect_recurrence(memory, scope, connection, str(memory.root / 'LIFEOS'))
    frames = _frames(memory, scope, connection, str(memory.root / 'LIFEOS'))
    budget = [0]
    hypotheses = []
    for path in _entries(memory, PREFIX.rstrip('/'), budget):
        if path.suffix == '.md' and path.name != 'README.md':
            relative = path.relative_to(memory.root).as_posix()
            content = _read(memory, relative)
            admitted = read_markdown(memory, scope, [str(path)], connection=connection)
            if len(admitted) != 1:
                raise MemoryUnavailable('An existing hypothesis is excluded by current memory policy')
            hypotheses.append({'name': path.name, 'content': content})
    state = _read(memory, PREFIX + '.state.json')
    try:
        decoded_state = json.loads(state) if state is not None else None
    except ValueError:
        decoded_state = None
    if decoded_state is not None and (not isinstance(decoded_state, dict)
            or not isinstance(decoded_state.get('claim_hashes'), dict)
            or any(not isinstance(row, dict) or not {'hash','archived_at','status'} <= set(row)
                   for row in decoded_state['claim_hashes'].values())):
        raise MemoryUnavailable('The hypothesis state has unsupported native fields')
    log = _read(memory, LOG) or ''
    stamp = _read(memory, STAMP)
    policy_text = '\n'.join([state or '', json_projection(state or '') or '', log, stamp or ''])
    if (memory._native('validate_source_batch', contents=[policy_text])['accepted'] != [True]
            or memory._filter_history(connection, scope, policy_text,
                datetime.now(timezone.utc).isoformat(), reviewed=True)['excluded']):
        raise MemoryUnavailable('The current hypothesis state or log is excluded')
    identity = _identity(memory, scope, connection)
    people_directory = 'LIFEOS/MEMORY/KNOWLEDGE/People'
    people = [path.stem.lower() for path in _entries(memory, people_directory, budget) if path.suffix == '.md']
    inputs = {'ratings': ratings['ratings'] or [], 'recurrence': recurrence['sources'],
        'frames': [{'name': Path(s['path']).stem, 'body': s['content']} for s in frames['sources']
                   if not Path(s['path']).name.startswith('_') and Path(s['path']).name.upper() != 'README.MD'],
        'people': people, 'hypotheses': hypotheses, 'state': decoded_state,
        'log': log, 'principal': identity['name']}
    if len(json.dumps(inputs).encode()) > CORPUS_LIMIT:
        raise MemoryUnavailable('The hypothesis input exceeds its corpus limit')
    return {'inputs': inputs, 'ratings': ratings, 'recurrence': recurrence, 'frames': frames,
            'state': state, 'stamp': stamp, 'identity': identity}


def _destination(memory, path):
    if not isinstance(path, str):
        raise MemoryUnavailable('Hypothesis publications require fixed native paths')
    try:
        relative = Path(path).relative_to(memory.root).as_posix()
    except ValueError as error:
        raise MemoryUnavailable('Hypothesis publication leaves the installed root') from error
    if (relative not in {LOG, STAMP, PREFIX + '.state.json'} and re.fullmatch(
            re.escape(PREFIX) + r'(?:_archive/)?[0-9]{4}-[0-9]{2}-[0-9]{2}_[a-z0-9-]{1,60}\.md', relative) is None):
        raise MemoryUnavailable('Hypothesis publication changes its fixed native destination')
    return _path(memory, relative)


def _digest(memory, path):
    target = _destination(memory, path)
    if target.exists() and target.stat().st_size > SOURCE_LIMIT:
        raise MemoryUnavailable('The hypothesis destination exceeds its source limit')
    return hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None


def _preserve_references(memory, connection, artifacts):
    for artifact in artifacts:
        target = _destination(memory, artifact['path'])
        relative = target.relative_to(memory.root).as_posix()
        if connection.execute("SELECT 1 FROM records WHERE path=? AND status='active' LIMIT 1", (relative,)).fetchone():
            if artifact['content'] is None or not target.exists() or target.read_text() != artifact['content']:
                raise MemoryUnavailable('Hypothesis derivation requires review before changing a registered fact source')


def publication_paths(memory, scope, payload):
    _authorize_write(scope)
    return [_destination(memory, path).relative_to(memory.root).as_posix() for path in payload['outputs']]


def derive(memory, scope, arguments, *, check_current):
    if (type(arguments['window']) is not int or not 1 <= arguments['window'] <= 365
            or any(type(arguments[k]) is not bool for k in ('dry_run','no_inference','once_daily'))):
        raise ValueError('Choose a bounded hypothesis window and native execution modes')
    writing = not arguments['dry_run']
    if writing:
        _authorize_write(scope)
    instant = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
    with memory._transaction() as connection:
        initial = _collect(memory, scope, connection, arguments)
        # Snapshot every existing fixed publication before the renderer returns.
        before = {str(memory.root / PREFIX / file['name']): hashlib.sha256(file['content'].encode()).hexdigest()
                  for file in initial['inputs']['hypotheses']}
        for relative in (PREFIX + '.state.json', LOG, STAMP):
            path = str(memory.root / relative)
            before[path] = _digest(memory, path)
        rendered = memory._native('learning_hypotheses', sources=initial['inputs'], now=instant,
            window=arguments['window'], dry_run=arguments['dry_run'], no_inference=arguments['no_inference'],
            once_daily=arguments['once_daily'], stamp=initial['stamp'])
        if (set(rendered) != {'result','publications','stdout'} or not isinstance(rendered['result'], dict)
                or set(rendered['result']) != {'emitted','updated','expired'}
                or any(type(n) is not int or not 0 <= n <= SOURCE_COUNT_LIMIT for n in rendered['result'].values())
                or not isinstance(rendered['stdout'], str) or not isinstance(rendered['publications'], list)
                or len(rendered['publications']) > SOURCE_COUNT_LIMIT
                or len(json.dumps(rendered).encode()) > CORPUS_LIMIT):
            raise MemoryUnavailable('Native hypothesis derivation returns invalid artifacts')
        paths = set()
        for artifact in rendered['publications']:
            if (not isinstance(artifact, dict) or set(artifact) != {'path','content'}
                    or artifact['content'] is not None and not isinstance(artifact['content'], str)):
                raise MemoryUnavailable('Native hypothesis publication contains unsupported fields')
            path = artifact['path']
            if path in paths:
                raise MemoryUnavailable('Native hypothesis derivation repeats a publication path')
            paths.add(path)
            _destination(memory, path)
            if path not in before:
                # New notes and archive targets must still be absent after rendering.
                before[path] = None
        generated = '\n'.join([rendered['stdout'], *(a['content'] or '' for a in rendered['publications'])])
        if (not writing and paths or memory._native('validate_source_batch', contents=[generated])['accepted'] != [True]
                or memory._filter_history(connection, scope, generated, instant, reviewed=True)['excluded']):
            raise MemoryUnavailable('Native hypothesis output is excluded by current memory policy')
        _preserve_references(memory, connection, rendered['publications'])
        check_current()
        if (_collect(memory, scope, connection, arguments) != initial
                or any(_digest(memory, p) != before[p] for p in paths)):
            raise MemoryConflict('Hypothesis sources or destinations change during derivation')
    if not writing:
        return {'ok': True, 'result': rendered['result'], 'stdout': rendered['stdout']}
    payload = {'operation': 'learning_hypotheses', **arguments, 'outputs': sorted(paths),
        'source_signature': hashlib.sha256(json.dumps(initial, sort_keys=True).encode()).hexdigest()}

    def apply(connection):
        try:
            check_current()
            if (_collect(memory, scope, connection, arguments) != initial
                    or any(_digest(memory, p) != before[p] for p in paths)):
                raise MemoryConflict('Hypothesis inputs change before publication')
        except (MemoryUnavailable, OSError) as error:
            raise MemoryConflict(str(error)) from error
        _preserve_references(memory, connection, rendered['publications'])
        for artifact in rendered['publications']:
            target = _destination(memory, artifact['path'])
            if artifact['content'] is None:
                target.unlink()
            else:
                publish(target, artifact['content'].encode())
        return {'status': 'committed', 'result': rendered['result'], 'stdout': rendered['stdout']}

    receipt = memory._operation(scope, arguments['request_id'], payload, apply,
                                identity_payload={'operation': 'learning_hypotheses', **arguments})
    return {'ok': receipt['status'] == 'committed', 'result': receipt.get('result'), 'stdout': receipt.get('stdout'), 'receipt': receipt}
