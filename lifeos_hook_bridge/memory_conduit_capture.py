# ABOUTME: Runs native Conduit commands on isolated admitted work and activity sources.
# ABOUTME: Publishes their actual file effects under current owner authority and recoverable receipts.
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from uuid import uuid4

from .memory_access import MemoryUnavailable
from .memory_conduit import PREFIX, CONFIG, _directory
from .memory_operational_views import projection
from .memory_policy import CATEGORIES
from .memory_source_review import _retirement_digest
from .memory_sources import authorize, _admit, _source_time, SOURCE_LIMIT, SOURCE_COUNT_LIMIT
from .memory_tab_freshness import _checked
from .memory_transaction import publish
from . import memory_operational_history as history

WORK = 'LIFEOS/MEMORY/STATE/work-events.jsonl'
STATE = PREFIX + 'state.json'
MAX_SNAPSHOT = 32 * 1024 * 1024
COMMANDS = frozenset({'capture', 'rollup', 'today', 'status', 'init'})


def declared(path):
    return path in {CONFIG, STATE} or re.fullmatch(
        re.escape(PREFIX) + r'(?:events/\d{4}-\d{2}-\d{2}\.jsonl|daily/\d{4}-\d{2}-\d{2}\.(?:json|md))', path) is not None


def publication_paths(memory, scope, payload):
    authorize(scope)
    if not scope.principal or not CATEGORIES <= set(scope.write):
        raise MemoryUnavailable('Conduit publication requires the unrestricted owner writer')
    if (set(payload) != {'operation', 'paths'} or payload['operation'] != 'conduit_command'
            or not isinstance(payload['paths'], list) or len(payload['paths']) > SOURCE_COUNT_LIMIT
            or any(not isinstance(path, str) or not declared(path) for path in payload['paths'])
            or len(set(payload['paths'])) != len(payload['paths'])):
        raise MemoryUnavailable('Choose fixed Conduit publication paths')
    for path in payload['paths']:_checked(memory, memory._publication_path(path))
    return payload['paths']


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_mode)


def selection(memory, *, only_config=False):
    if only_config:return [CONFIG], []
    files = [CONFIG, STATE]
    directories = []
    for folder, expression in (('events', r'\d{4}-\d{2}-\d{2}\.jsonl'),
                               ('daily', r'\d{4}-\d{2}-\d{2}\.(?:json|md)')):
        names, observed = _directory(memory, folder)
        directories.append((folder, observed))
        files.extend(PREFIX + folder + '/' + name for name in sorted(names) if re.fullmatch(expression, name))
    if len(files) > SOURCE_COUNT_LIMIT:
        raise MemoryUnavailable('Conduit command source discovery exceeds its file limit')
    return files, directories


def _raw(memory, relative, limit):
    path = _checked(memory, memory.root / relative)
    if not path.exists():return None
    before = path.stat()
    if not path.is_file() or before.st_size > limit:
        raise MemoryUnavailable('Conduit command requires bounded regular owner files')
    with path.open('rb') as stream:data = stream.read(limit + 1)
    after = path.stat()
    _checked(memory, path)
    keys = lambda value:(value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)
    if len(data) > limit or keys(before) != keys(after):
        raise MemoryUnavailable('Conduit command sources change during collection')
    return data


def _execute(memory, home, command, date):
    root = home / '.claude'
    environment = dict(os.environ, HOME=str(home), CLAUDE_CONFIG_DIR=str(root),
        LIFEOS_DIR=str(root/'LIFEOS'), LIFEOS_CONFIG_DIR=str(root/'LIFEOS/USER/CONFIG'),
        LIFEOS_MEMORY_INTERNAL='1', BUN_CONFIG_NO_AUTO_INSTALL='1', LIFEOS_NOTIFICATION_CHANNEL='headless')
    environment.pop('LIFEOS_MEMORY_PUBLICATION_JOURNAL', None)
    arguments = [memory.bun, '--no-install', str(memory.root/'LIFEOS/PULSE/Conduit/conduit.ts'), command]
    if date is not None:arguments.append(date)
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
        process = subprocess.Popen(arguments, env=environment, cwd=home, stdout=output, stderr=errors,
            pass_fds=memory.transaction.inherited_descriptors())
        try:
            process.wait(timeout=20)
        finally:
            if process.poll() is None:process.kill()
            process.wait()
        output.seek(0); errors.seek(0)
        text = output.read(3*1024*1024 + 1)
        failure = errors.read(3*1024*1024 + 1)
        if process.returncode or failure or len(text) > 3*1024*1024:
            raise MemoryUnavailable('The isolated native Conduit command fails its execution contract')
    return text.decode('utf-8').replace(str(root/'LIFEOS/USER/CONDUIT'), str(memory.root/'LIFEOS/USER/CONDUIT'))


def _result_files(root):
    paths = {}
    total = 0
    base = root / PREFIX
    if not base.exists():return paths
    entries = list(base.rglob('*'))
    if len(entries) > SOURCE_COUNT_LIMIT + 4:
        raise MemoryUnavailable('Native Conduit output exceeds its fixed file inventory')
    for path in entries:
        if path.is_dir():continue
        relative = path.relative_to(root).as_posix()
        if not declared(relative) or path.is_symlink() or not path.is_file() or path.stat().st_uid != os.getuid():
            raise MemoryUnavailable('Native Conduit output changes its declared owner file')
        if path.stat().st_size > MAX_SNAPSHOT:
            raise MemoryUnavailable('Native Conduit output exceeds its file size limit')
        data = path.read_bytes()
        total += len(data)
        if total > MAX_SNAPSHOT:
            raise MemoryUnavailable('Native Conduit output exceeds its total snapshot limit')
        paths[relative] = data
    return paths


def _validate(memory, scope, connection, text):
    if (memory._native('validate_source_batch', contents=[text])['accepted'] != [True]
            or memory._filter_history(connection, scope, text, datetime.now(timezone.utc).isoformat())['excluded']):
        raise MemoryUnavailable('Conduit command output is excluded under the current owner policy')


def run(memory, scope, command, date, *, check_current):
    authorize(scope)
    if command not in COMMANDS or date is not None and (command != 'rollup' or not isinstance(date, str)
            or re.fullmatch(r'\d{4}-\d{2}-\d{2}', date) is None):
        raise ValueError('Choose a declared Conduit command and date')
    if command in {'capture', 'rollup', 'init'} and not CATEGORIES <= set(scope.write):
        raise MemoryUnavailable('Conduit command requires the unrestricted owner writer')
    with tempfile.TemporaryDirectory(prefix='lifeos-conduit-command-') as name:
        home = Path(name)
        root = home/'.claude'
        with memory._transaction() as connection:
            check_current()
            retired = _retirement_digest(connection)
            raw_config = _raw(memory, CONFIG, SOURCE_LIMIT)
            config = {} if raw_config is None else json.loads(raw_config)
            if not isinstance(config, dict):
                raise MemoryUnavailable('Conduit capture requires a native object configuration')
            only_config = command == 'capture' and config.get('enabled') is False
            names, directories = selection(memory, only_config=only_config)
            if command == 'capture' and config.get('enabled') is not False:
                sources = config.get('sources', {})
                if (raw_config is None or not isinstance(sources, dict) or sources.get('appFocus') is not False
                        or sources.get('git') is not False or sources.get('github') is True):
                    raise MemoryUnavailable('Conduit capture requires the selected headless source configuration')
            else:sources = {}
            originals = {}
            copied = {}
            fingerprints = []
            streamed = {path:None for path in names if path.endswith('.jsonl')}
            if command == 'capture' and config.get('enabled') is not False and sources.get('claudeSession') is not False:
                streamed[WORK] = None
            for relative in names:
                if relative in streamed:continue
                data = _raw(memory, relative, SOURCE_LIMIT)
                originals[relative] = data
                fingerprints.append(history.fingerprint(memory, relative, sources={relative:None}))
                if data is None:continue
                content = data.decode('utf-8')
                decoded = projection(content) if relative.endswith('.json') else content
                if decoded is None:
                    raise MemoryUnavailable('Conduit command metadata requires complete native content')
                _validate(memory, scope, connection, decoded+'\n'+relative)
                if _admit(memory, connection, scope, content, relative, _source_time((memory.root/relative).stat()),
                        projection=decoded)['excluded']:
                    raise MemoryUnavailable('Conduit command metadata is excluded under owner admission')
            with history.snapshot(memory, scope, connection, check_current=check_current, sources=streamed,
                    require_newline=False, objects_only=False, allow_unfinished_utf8=False,
                    require_all_admitted=True) as (_, event_fingerprints):
                fingerprints.extend(event_fingerprints)
                for relative in streamed:
                    originals[relative] = _raw(memory, relative, MAX_SNAPSHOT)
            if sum(len(data) for data in originals.values() if data is not None) > MAX_SNAPSHOT:
                raise MemoryUnavailable('Conduit command exceeds its total source snapshot limit')
            if selection(memory, only_config=only_config) != (names, directories):
                raise MemoryUnavailable('Conduit source discovery changes during admission')
            for relative, data in originals.items():
                if data is None:continue
                if relative.startswith(PREFIX+'events/') and data and not data.endswith(b'\n'):
                    raise MemoryUnavailable('Conduit capture requires a complete terminated event ledger')
                if hashlib.sha256(data).hexdigest() != next(item[2] for item in fingerprints if item[0]==relative):
                    raise MemoryUnavailable('Conduit sources change before isolated native execution')
                publish(root/relative, data)
                copied[relative] = _identity((root/relative).stat())
            check_current()
            output = _execute(memory, home, command, date)
            _validate(memory, scope, connection, output)
            generated = _result_files(root)
            for relative, data in generated.items():
                if data != originals.get(relative):
                    _validate(memory, scope, connection, data.decode('utf-8')+'\n'+relative)
            if command == 'capture' and config.get('enabled') is not False and sources.get('claudeSession') is not False:
                before = {} if originals.get(STATE) is None else json.loads(originals[STATE])
                after = {} if STATE not in generated else json.loads(generated[STATE])
                if not isinstance(before, dict):before = {}
                if not isinstance(after, dict):after = {}
                changed_events = any(path.startswith(PREFIX+'events/') and data != originals.get(path)
                    for path, data in generated.items())
                if before.get('lastClaudeCursor') != after.get('lastClaudeCursor') and not changed_events:
                    raise MemoryUnavailable('Conduit capture preserves activity when a native append fails')
            effects = {path:data for path,data in generated.items() if data != originals.get(path)
                or _identity((root/path).stat()) != copied.get(path)}
            effects.update({path:None for path,data in originals.items()
                if path != WORK and data is not None and path not in generated})
            expected = {path:None if data is None else hashlib.sha256(data).hexdigest() for path,data in effects.items()}
            def unchanged():
                check_current()
                if (_retirement_digest(connection) != retired or selection(memory, only_config=only_config) != (names, directories)
                        or [history.fingerprint(memory, item[0], sources={item[0]:None}) for item in fingerprints] != fingerprints):
                    raise MemoryUnavailable('Conduit sources or retirement change during native execution')
            unchanged()
        def publish_effects(connection):
            check_current()
            if (_retirement_digest(connection) != retired or selection(memory, only_config=only_config) != (names, directories)
                    or [history.fingerprint(memory,item[0],sources={item[0]:None}) for item in fingerprints] != fingerprints):
                raise MemoryUnavailable('Conduit publication preserves later source or authority changes')
            for relative in sorted(effects, key=lambda name:(name==STATE, effects[name] is None, name)):
                data = effects[relative]
                path = _checked(memory,memory._publication_path(relative))
                if data is None:path.unlink()
                else:publish(path,data)
            check_current()
            if _retirement_digest(connection) != retired:
                raise MemoryUnavailable('Conduit retirement changes during native publication')
            for relative,digest in expected.items():
                if history.fingerprint(memory,relative,sources={relative:None})[-1] != digest:
                    raise MemoryUnavailable('Conduit publication changes its native file bytes')
            for item in fingerprints:
                if item[0] not in effects and history.fingerprint(memory,item[0],sources={item[0]:None}) != item:
                    raise MemoryUnavailable('Conduit source changes during native file publication')
            _validate(memory,scope,connection,output)
            return {'status':'committed','output':output}
        if effects:
            receipt = memory._operation(scope,'conduit-command-'+uuid4().hex,
                {'operation':'conduit_command','paths':list(effects)},publish_effects,publication_digests=expected)
            if receipt['status'] != 'committed':
                raise MemoryUnavailable('Conduit command publication needs owner recovery')
        with memory._transaction() as connection:
            check_current()
            if _retirement_digest(connection) != retired:
                raise MemoryUnavailable('Conduit command authority changes before delivery')
            wanted = {path:data for path,data in originals.items() if path != WORK and data is not None}
            wanted.update(generated)
            for relative in effects:
                if effects[relative] is None:wanted.pop(relative,None)
            current_names,_ = selection(memory, only_config=only_config)
            present = {relative:_raw(memory,relative,MAX_SNAPSHOT) for relative in current_names}
            present = {relative:data for relative,data in present.items() if data is not None}
            if present != wanted or WORK in originals and _raw(memory,WORK,MAX_SNAPSHOT) != originals[WORK]:
                raise MemoryUnavailable('Conduit delivery preserves later work and activity changes')
            _validate(memory,scope,connection,output)
            check_current()
        return {'ok':True,'output':output}
