# ABOUTME: Supplies admitted fresh-store sources to native KnowledgeHarvester mining.
# ABOUTME: Journals staging and domain-preserving expiry with current owner authority.
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re

from .memory_access import MemoryUnavailable, _now
from .memory_adoption import _owner
from .memory_backup import _read
from .memory_canonical import corpus
from .memory_sources import authorize, _admit, json_projection, SOURCE_LIMIT, SOURCE_COUNT_LIMIT, CORPUS_LIMIT
from .memory_staging import KNOWLEDGE, STATE, DOMAINS, _path
from .memory_transaction import publish


ROOTS = ('LIFEOS/MEMORY/WORK', 'LIFEOS/MEMORY/RESEARCH', KNOWLEDGE+'/_harvest-queue',
         KNOWLEDGE+'/_archive', *(KNOWLEDGE+'/'+domain for domain in DOMAINS))
RATINGS = 'LIFEOS/MEMORY/LEARNING/SIGNALS/ratings.jsonl'


def _file(memory, relative):
    path = _path(memory, relative)
    if path.exists():
        info = path.stat()
        if info.st_uid != os.getuid() or info.st_nlink != 1 or info.st_mode & 0o022:
            raise MemoryUnavailable('Knowledge mining requires regular unshared owner files')
    return path


def _snapshot(memory):
    files = {}
    directories = {}
    total = 0
    def directory(relative):
        nonlocal total
        path = _path(memory, relative, file=False)
        if not path.exists():
            directories[relative] = None
            return
        info = path.stat()
        if not path.is_dir() or info.st_uid != os.getuid() or info.st_mode & 0o022:
            raise MemoryUnavailable('Knowledge mining requires physical owner directories')
        names = [child.name for child in path.iterdir()]
        directories[relative] = names
        if len(files)+len(directories)+len(names) > SOURCE_COUNT_LIMIT:
            raise MemoryUnavailable('Knowledge mining exceeds its source count limit')
        for name in names:
            child = _path(memory, relative+'/'+name, file=False)
            if child.is_dir():
                directory(relative+'/'+name)
            elif child.is_file():
                child = _file(memory, relative+'/'+name)
                data, stamp = _read(child)
                total += len(data)
                if len(data) > SOURCE_LIMIT or total > CORPUS_LIMIT:
                    raise MemoryUnavailable('Knowledge mining exceeds its source byte limit')
                files[relative+'/'+name] = {'content':data.decode('utf-8'), 'stamp':stamp}
            else:
                raise MemoryUnavailable('Knowledge mining refuses non-regular sources')
    for relative in ROOTS:
        directory(relative)
    for relative in (STATE, RATINGS):
        path = _file(memory, relative)
        if path.exists():
            data, stamp = _read(path)
            total += len(data)
            if len(data) > SOURCE_LIMIT or total > CORPUS_LIMIT:
                raise MemoryUnavailable('Knowledge mining exceeds its source byte limit')
            files[relative] = {'content':data.decode('utf-8'), 'stamp':stamp}
    return {'files':files, 'directories':directories}


def _state(text):
    value = json.loads(text)
    if (not isinstance(value, dict) or not isinstance(value.get('lastHarvest'), str)
            or not isinstance(value.get('harvestedPaths'), list)
            or not all(isinstance(item, str) for item in value['harvestedPaths'])
            or type(value.get('totalHarvested')) is not int or not 0 <= value['totalHarvested'] < 2**53):
        raise MemoryUnavailable('Knowledge mining requires valid native harvest state')
    if datetime.fromisoformat(value['lastHarvest'].replace('Z','+00:00')).tzinfo is None:
        raise MemoryUnavailable('Knowledge mining requires a timezone on its harvest clock')
    return value


def _collect(memory, connection, scope, snapshot, source):
    sources = []
    pending = []
    for relative, item in snapshot['files'].items():
        text = item['content']
        if relative == STATE:
            _state(text)
            sources.append({'path':str(memory.root/relative), 'content':text})
            continue
        selected = (relative.startswith('LIFEOS/MEMORY/WORK/') and source in (None, 'work') and relative.endswith('/ISA.md')
                    or relative.startswith('LIFEOS/MEMORY/RESEARCH/') and source in (None, 'research') and relative.endswith('.md')
                    or relative == RATINGS and source in (None, 'work')
                    or str(Path(relative).parent) == KNOWLEDGE+'/_harvest-queue' and relative.endswith('.json'))
        if not selected:
            continue
        projection = text
        if relative.endswith('.json'):
            projection = json_projection(text)
            if projection is None:
                continue
            value = json.loads(text)
            if (not isinstance(value, dict) or value.get('domain', 'Ideas') not in DOMAINS
                    or any(key in value and not isinstance(value[key], str) for key in ('sourcePath','title','content','type'))
                    or not isinstance(value.get('tags', []), list)
                    or not all(isinstance(tag, str) for tag in value.get('tags', []))):
                raise MemoryUnavailable('Knowledge mining requires declared native queue fields')
        elif relative == RATINGS:
            rows = [json_projection(line) for line in text.splitlines() if line.strip()]
            if any(row is None for row in rows):
                continue
            projection = '\n'.join(rows)
        timestamp = datetime.fromtimestamp((memory.root/relative).stat().st_mtime, timezone.utc).isoformat()
        if not _admit(memory, connection, scope, text, relative, timestamp, projection=projection)['excluded']:
            pending.append({'path':str(memory.root/relative), 'content':text, 'projection':projection})
    if pending:
        accepted = memory._native('validate_source_batch', contents=[item['projection']+'\n'+item['path'] for item in pending])['accepted']
        sources.extend({'path':item['path'], 'content':item['content']} for item, allowed in zip(pending, accepted, strict=True) if allowed is True)
    current = corpus(memory, scope, str(memory.root/'LIFEOS/MEMORY'), connection=connection)
    sources.extend({'path':str(memory.root/'LIFEOS/MEMORY'/Path(file).relative_to(current['root'])),
                    'content':record['content']} for file, record in zip(current['files'], current['records'], strict=True))
    return sources


def publication_paths(memory, scope, payload):
    if not _owner(scope):
        raise MemoryUnavailable('Knowledge publication requires unrestricted owner authority')
    plan = payload['plan']
    paths = [*plan['writes'], *plan['deletes']]
    if len(set(paths)) != len(paths) or len(paths) > SOURCE_COUNT_LIMIT:
        raise MemoryUnavailable('Knowledge publication repeats or exceeds its declared destinations')
    for relative in paths:
        if (relative not in (STATE, KNOWLEDGE+'/_index.md') and re.fullmatch(
                r'LIFEOS/MEMORY/KNOWLEDGE/(?:_harvest-queue/(?:People|Companies|Ideas|Research)/[a-z0-9][a-z0-9-]{0,59}\.md'
                r'|_harvest-queue/[A-Za-z0-9._-]{1,180}\.json|(?:People|Companies|Ideas|Research)/[^/]+\.md'
                r'|_archive/(?:People|Companies|Ideas|Research)/[^/]+\.md)', relative) is None):
            raise MemoryUnavailable('Knowledge publication changes its native destination set')
        _file(memory, relative)
    return paths


def run(memory, scope, *, source, dry_run, max_notes, request_id, source_session='', check_current=None):
    authorize(scope)
    if not scope.principal:
        raise MemoryUnavailable('Knowledge mining requires an authenticated owner')
    if (source not in (None, 'memory', 'work', 'reflections', 'research') or type(dry_run) is not bool
            or type(max_notes) is not int or not 1 <= max_notes <= 50
            or not isinstance(request_id, str) or not 1 <= len(request_id) <= 256):
        raise MemoryUnavailable('Choose bounded native Knowledge mining options')
    if not dry_run and not _owner(scope):
        raise MemoryUnavailable('Knowledge publication requires unrestricted owner authority')
    if check_current is not None:
        check_current()
    identity = {'operation':'knowledge_harvest', 'source':source, 'max_notes':max_notes, 'source_session':source_session}
    with memory._transaction() as connection:
        prior = connection.execute('SELECT 1 FROM operations WHERE writer=? AND request_id=?', (scope.writer,request_id)).fetchone()
    if prior is not None and not dry_run:
        receipt = memory._operation(scope, request_id, {**identity, 'plan':None}, lambda _: {}, identity_payload=identity)
        if check_current is not None:
            check_current()
        with memory._transaction() as connection:
            output = receipt.get('stdout','')
            projection = output+'\n'+output.replace('_',' ').replace('-',' ')
            if memory._filter_history(connection, scope, projection, datetime.now(timezone.utc).isoformat())['excluded']:
                raise MemoryUnavailable('The retained Knowledge receipt contains an excluded source label')
        return {'ok':receipt['status'] in ('committed','unchanged'), 'receipt':receipt}
    with memory._transaction() as connection:
        snapshot = _snapshot(memory)
        sources = _collect(memory, connection, scope, snapshot, source)
        if check_current is not None:
            check_current()
        plan = memory._native('knowledge_harvest', sources=sources, source=source, dry_run=dry_run,
                              max_notes=max_notes, occupied=[str(memory.root/name) for name in snapshot['files']],
                              ordering=[str(memory.root/name/child) for name,children in snapshot['directories'].items()
                                        for child in children or []])
        if check_current is not None:
            check_current()
        if _snapshot(memory) != snapshot:
            raise MemoryUnavailable('Knowledge sources change during native rendering')
        if (set(plan) != {'stdout','writes','deletes','moves'} or not isinstance(plan['stdout'], str)
                or not all(isinstance(plan[key], list) for key in ('writes','deletes','moves'))):
            raise MemoryUnavailable('Native Knowledge mining returns an invalid publication plan')
        if dry_run:
            if plan['writes'] or plan['deletes'] or plan['moves']:
                raise MemoryUnavailable('Native Knowledge preview attempts a publication')
            return {'ok':True, 'stdout':plan['stdout']}
        writes = {}
        for item in plan['writes']:
            if (not isinstance(item, dict) or set(item) != {'path','content'} or not isinstance(item['content'], str)
                    or len(item['content'].encode()) > SOURCE_LIMIT):
                raise MemoryUnavailable('Native Knowledge mining returns an invalid write')
            relative = Path(item['path']).relative_to(memory.root).as_posix()
            if relative in writes:
                raise MemoryUnavailable('Native Knowledge mining repeats a write')
            writes[relative] = item['content']
        deletes = [Path(file).relative_to(memory.root).as_posix() for file in plan['deletes']]
        moves = []
        admitted = {item['path'] for item in sources}
        for move in plan['moves']:
            if set(move) != {'source','path'} or move['source'] not in admitted:
                raise MemoryUnavailable('Native Knowledge expiry changes its admitted note set')
            original = Path(move['source']).relative_to(memory.root).as_posix()
            target = Path(move['path']).relative_to(memory.root).as_posix()
            expected = KNOWLEDGE+'/_archive/'+Path(original).parent.name+'/'+Path(original).name
            if target != expected or original not in deletes or target not in writes or target in snapshot['files']:
                raise MemoryUnavailable('Native Knowledge expiry changes its domain-preserving archive')
            if connection.execute("SELECT 1 FROM records WHERE path=? AND status='active'", (original,)).fetchone() is None:
                raise MemoryUnavailable('Native Knowledge expiry requires a registered current note')
            writes[target] = snapshot['files'][original]['content']
            moves.append({'source':original, 'path':target})
        queued = {str(memory.root/name) for name in snapshot['files'] if str(Path(name).parent) == KNOWLEDGE+'/_harvest-queue'
                  and name.endswith('.json') and str(memory.root/name) in admitted}
        if any(str(memory.root/name) not in queued and name not in {move['source'] for move in moves} for name in deletes):
            raise MemoryUnavailable('Native Knowledge mining changes its admitted deletions')
        staged = [name for name in writes if name.startswith(KNOWLEDGE+'/_harvest-queue/')]
        if any(name not in (STATE, KNOWLEDGE+'/_index.md') and name not in staged
               and name not in {move['path'] for move in moves} for name in writes):
            raise MemoryUnavailable('Native Knowledge mining changes its admitted writes')
        if any(name in snapshot['files'] for name in staged):
            raise MemoryUnavailable('Native Knowledge staging cannot replace an existing note')
        if STATE in writes:
            _state(writes[STATE])
        checked = memory._native('validate_source_batch', contents=[text+'\n'+name for name,text in writes.items()])['accepted']
        if not all(value is True for value in checked):
            raise MemoryUnavailable('Native validation refuses a generated Knowledge source')
        now = datetime.now(timezone.utc).isoformat()
        if any(memory._filter_history(connection, scope, text, now)['excluded'] for text in writes.values()):
            raise MemoryUnavailable('Native Knowledge output contains an excluded claim')
        publication = {'writes':writes, 'deletes':deletes, 'moves':moves}
        payload = {**identity, 'plan':publication}
        publication_paths(memory, scope, payload)
    def apply(connection):
        if check_current is not None:
            check_current()
        if _snapshot(memory) != snapshot:
            return {'status':'conflict', 'reason':'Knowledge sources change before publication'}
        for relative,text in writes.items():
            if check_current is not None:
                check_current()
            publish(_file(memory,relative), text.encode())
        for move in moves:
            if check_current is not None:
                check_current()
            connection.execute("UPDATE records SET path=?,status='superseded',revision=revision+1,updated=? WHERE path=? AND status='active'",
                               (move['path'],_now(),move['source']))
            if check_current is not None:
                check_current()
            connection.execute('UPDATE records SET path=? WHERE path=?', (move['path'],move['source']))
        for relative in deletes:
            if check_current is not None:
                check_current()
            _file(memory,relative).unlink()
        output = plan['stdout']
        projection = output+'\n'+output.replace('_',' ').replace('-',' ')
        if memory._filter_history(connection, scope, projection, datetime.now(timezone.utc).isoformat())['excluded']:
            output = 'Native Knowledge publication completes under current memory policy.\n'
        if check_current is not None:
            check_current()
        return {'status':'committed' if writes or deletes else 'unchanged', 'notes_staged':len(staged),
                'notes_archived':len(moves), 'stdout':output}
    receipt = memory._operation(scope, request_id, payload, apply, identity_payload=identity)
    return {'ok':receipt['status'] in ('committed','unchanged'), 'receipt':receipt}
