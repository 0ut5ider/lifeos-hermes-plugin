# ABOUTME: Governs retained native source reads before startup summaries reach a model.
# ABOUTME: Excludes restricted, invalid, forgotten, and superseded source text without copying files.
from datetime import datetime, timedelta, timezone
from contextlib import nullcontext
import json
from pathlib import Path
import re
from typing import Any

from .memory_access import HOT_FILES, MemoryUnavailable
from .memory_policy import CATEGORIES, MemoryScope


PREFIXES = ('LIFEOS/MEMORY/LEARNING/', 'LIFEOS/MEMORY/WISDOM/FRAMES/',
            'LIFEOS/MEMORY/WISDOM/PRINCIPLES/', 'LIFEOS/MEMORY/WISDOM/META/', 'LIFEOS/MEMORY/RESEARCH/',
            'LIFEOS/MEMORY/RELATIONSHIP/', 'LIFEOS/MEMORY/WORK/', 'LIFEOS/MEMORY/STATE/progress/')
FILES = {'LIFEOS/MEMORY/STATE/learning-cache.sh', 'LIFEOS/MEMORY/STATE/session-names.json',
         'LIFEOS/MEMORY/STATE/events.jsonl'}
LOG_FILES = {'LIFEOS/MEMORY/OBSERVABILITY/memory-writes.jsonl',
             'LIFEOS/MEMORY/OBSERVABILITY/memory-health.jsonl'}
CACHE_FILES = {'LIFEOS/USER/CACHE/freshness.json'}
CONTEXT_FILES = {'LIFEOS/USER/DIGITAL_ASSISTANT/DA_IDENTITY.md',
                 'LIFEOS/USER/PRINCIPAL/PRINCIPAL_IDENTITY.md',
                 'LIFEOS/USER/TELOS/PRINCIPAL_TELOS.md', 'LIFEOS/USER/PROJECTS.md'}
STATE_SOURCES = frozenset('LIFEOS/USER/TELOS/' + directory + '/' + name + '.md'
    for directory in ('IDEAL_STATE', 'CURRENT_STATE')
    for name in ('HEALTH', 'MONEY', 'FREEDOM', 'CREATIVE', 'RELATIONSHIPS', 'RHYTHMS', 'INFRASTRUCTURE'))
TELOS_SOURCES = frozenset('LIFEOS/USER/TELOS/' + name + '.md' for name in
    ('TELOS', 'MISSION', 'GOALS', 'PROBLEMS', 'STRATEGIES', 'PROJECTS', 'CHALLENGES',
     'NARRATIVES', 'TRAUMAS', 'WRONG', 'MODELS', 'WISDOM'))
FRESHNESS_TELOS_SOURCES = frozenset('LIFEOS/USER/TELOS/' + name + '.md' for name in
    ('TELOS', 'MISSION', 'GOALS', 'PROBLEMS', 'STRATEGIES', 'CHALLENGES', 'NARRATIVES',
     'TRAUMAS', 'WRONG', 'MODELS', 'BELIEFS', 'FRAMES', 'WISDOM', 'PREDICTIONS', 'IDEAS',
     'SPARKS', 'BOOKS', 'AUTHORS', 'BANDS', 'MOVIES', 'RESTAURANTS', 'FOOD_PREFERENCES',
     'MEETUPS', 'CIVIC', 'LEARNING', 'TEAM'))
SYSTEM_PREFIXES = ('LIFEOS/DOCUMENTATION/', 'LIFEOS/ALGORITHM/')
SYSTEM_FILES = {'LIFEOS/LIFEOS_SYSTEM_PROMPT.md'}
SOURCE_LIMIT = 256 * 1024
CORPUS_LIMIT = 3 * 1024 * 1024
SOURCE_COUNT_LIMIT = 2048
EVIDENCE_FILES = frozenset({'LIFEOS/USER/HEALTH/current.json', 'LIFEOS/USER/FINANCES/expenses.json',
                            'LIFEOS/MEMORY/STATE/work.json'})
EVIDENCE_DIRECTORIES = frozenset({'LIFEOS/USER/HEALTH/DATA/oura', 'LIFEOS/USER/CONDUIT/daily'})


def is_evidence_source(relative):
    return relative in EVIDENCE_FILES or (str(Path(relative).parent) in EVIDENCE_DIRECTORIES
        and re.fullmatch(r'\d{4}-\d{2}-\d{2}\.json', Path(relative).name) is not None)


def json_projection(content):
    try:
        value = json.loads(content)
        normalized = json.dumps(value, ensure_ascii=False, allow_nan=False)
        normalized.encode()
        strings = []
        pending = [value]
        while pending:
            item = pending.pop()
            if isinstance(item, str):
                strings.append(item)
            elif isinstance(item, dict):
                pending.extend(item.keys())
                pending.extend(item.values())
            elif isinstance(item, list):
                pending.extend(item)
        return '\n'.join((normalized, *strings))
    except (ValueError, RecursionError, UnicodeError):
        return None


def is_state_source(relative: str) -> bool:
    return (re.fullmatch(r'LIFEOS/USER/TELOS/(?:CURRENT_STATE|IDEAL_STATE)/[^/]+\.md', relative) is not None
            and Path(relative).name not in ('README.md', 'INDEX.md'))


def authorize(scope: MemoryScope) -> dict[str, Any]:
    if not CATEGORIES <= set(scope.read) or '*' not in scope.projects:
        raise MemoryUnavailable('This unclassified native source requires unrestricted owner recall')
    return {'ok':True}


def _source_path(memory, scope: MemoryScope, path: str, *, diagnostic: bool = False,
                 require_file: bool = True, evidence: bool = False) -> tuple[Path, str]:
    authorize(scope)
    if not isinstance(path,str):
        raise MemoryUnavailable('A supported native source path is required')
    relative = Path(path).relative_to(memory.root).as_posix()
    if '..' in Path(relative).parts:
        raise MemoryUnavailable('The native source cannot leave its installed root')
    system = (relative in SYSTEM_FILES or relative.startswith(SYSTEM_PREFIXES)
              or re.fullmatch(r'skills/[^/.][^/]*/SKILL\.md', relative) is not None)
    if evidence:
        directory = False
        permitted = is_evidence_source(relative)
    elif diagnostic:
        from .memory_diagnostics import DIAGNOSTIC_FILES, DIAGNOSTIC_DIRECTORIES
        directory = not require_file and relative in DIAGNOSTIC_DIRECTORIES
        report = not require_file and re.fullmatch(
            r'LIFEOS/MEMORY/OBSERVABILITY/reports/[A-Za-z0-9][A-Za-z0-9_-]*\.json', relative)
        permitted = relative in DIAGNOSTIC_FILES or directory or report
    else:
        directory = False
        permitted = (relative in FILES | LOG_FILES | CACHE_FILES | CONTEXT_FILES | TELOS_SOURCES | FRESHNESS_TELOS_SOURCES
                     or is_state_source(relative)
                     or relative.startswith(PREFIXES) or system)
    if not permitted:
        raise MemoryUnavailable('This is not a supported native history or context source')
    source = memory.root / relative if system else memory._path(relative)
    physical = source.absolute() if system else memory.root.parent/'.config/LIFEOS/USER'/Path(relative).relative_to(
        'LIFEOS/USER' if relative.startswith('LIFEOS/USER/') else 'LIFEOS')
    if (source.resolve() != physical.absolute() or (require_file and not source.is_file())
            or (not require_file and source.exists() and not (source.is_dir() if directory else source.is_file()))):
        raise MemoryUnavailable('The native source is missing or changes its permitted physical path')
    # Closing another descriptor for the SQLite inode releases this process's transaction locks.
    if system and source.exists() and memory.database.exists() and source.samefile(memory.database):
        raise MemoryUnavailable('Native memory content cannot alias its SQLite registry')
    return source, relative


def _source_time(info, *, milliseconds: bool = False) -> str:
    # Native Bun displays floating-point millisecond Dates. Admission preserves integer microseconds.
    microseconds = (int(info.st_mtime_ns / 1_000_000) * 1000 if milliseconds else info.st_mtime_ns // 1000)
    return (datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=microseconds)).isoformat()


def _text_source(memory, scope: MemoryScope, path: str, *, suffix='.md', evidence=False):
    source, relative = _source_path(memory, scope, path, evidence=evidence)
    if source.suffix != suffix:
        raise MemoryUnavailable('The declared wiki source must be native Markdown')
    before = source.stat()
    if before.st_size > SOURCE_LIMIT:
        raise MemoryUnavailable('The native wiki source exceeds the 256 KiB limit')
    try:
        content = source.read_text(encoding='utf-8')
    except UnicodeError as error:
        raise MemoryUnavailable('The native wiki source is not valid UTF-8') from error
    after = source.stat()
    if ((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)):
        raise MemoryUnavailable('The native wiki source changed during collection')
    _source_path(memory, scope, path, evidence=evidence)
    if len(content.encode()) > SOURCE_LIMIT:
        raise MemoryUnavailable('The native wiki source exceeds the 256 KiB limit')
    return ({'path': path, 'relative': relative, 'content': content,
             'lastModified': _source_time(after, milliseconds=True)}, _source_time(after))


def _markdown_source(memory, scope: MemoryScope, path: str):
    return _text_source(memory, scope, path)


def _admit(memory, connection, scope, content, relative, timestamp, *, projection=None):
    from .memory_source_review import is_reviewed
    labels = re.sub(r'(^|/)\d{8}-\d{6}_', r'\1', relative).replace('-', ' ').replace('_', ' ')
    return memory._filter_history(connection, scope, '\n'.join((content if projection is None else projection,
                                                              relative, labels)), timestamp,
                                  reviewed=is_reviewed(memory, connection, scope, relative, content))


def source_labels(relative: str) -> str:
    parts = Path(relative).parts
    # Knowledge type directories name native formats, not user claims.
    start = 4 if parts[:3] == ('LIFEOS', 'MEMORY', 'KNOWLEDGE') else 3
    dynamic = '/'.join(parts[start:])
    normalized = re.sub(r'(^|/)\d{8}-\d{6}_', r'\1', dynamic).replace('-', ' ').replace('_', ' ')
    return '\n'.join((dynamic, normalized))


def source_projection(memory, relative: str, content: str) -> str:
    path = memory._path(relative)
    text = path.read_text(encoding='utf-8')
    front = re.match(r'^---\n.*?\n---\n', text, re.DOTALL)
    return '\n'.join((front.group() if front else '', content, str(path)))


def read_markdown(memory, scope: MemoryScope, paths: list[str], *, connection=None) -> list[dict[str, Any]]:
    authorize(scope)
    if len(paths) > SOURCE_COUNT_LIMIT or len(set(paths)) != len(paths):
        raise MemoryUnavailable('The declared native sources exceed their count limit or repeat a path')
    with (memory._transaction() if connection is None else nullcontext(connection)) as connection:
        sources = []
        timestamps = {}
        total = 0
        for path in paths:
            source, timestamp = _markdown_source(memory, scope, path)
            size = len(source['content'].encode())
            total += size
            if total > CORPUS_LIMIT:
                raise MemoryUnavailable('The declared native wiki sources exceed their transport limit')
            timestamps[path] = timestamp
            sources.append(source)
        if not sources:
            return []
        checked = memory._native('validate_source_batch',
            contents=[source['content'] + '\n' + source['path'] for source in sources])['accepted']
        admitted = []
        for source, accepted in zip(sources, checked, strict=True):
            if accepted is not True:
                continue
            relative = source['relative']
            if not _admit(memory, connection, scope, source['content'], relative, timestamps[source['path']])['excluded']:
                admitted.append(source)
        return admitted


def check(memory, scope: MemoryScope, path: str) -> dict[str, Any]:
    with memory._transaction():
        _source_path(memory,scope,path)
    return {'ok':True}


def _strings(value: Any) -> list[str]:
    if isinstance(value,str):
        return [value]
    if isinstance(value,list):
        return [text for item in value for text in _strings(item)]
    if isinstance(value,dict):
        return [text for key,item in value.items() for text in [key,*_strings(item)]]
    return []


def _valid_log_row(row: dict[str, Any], relative: str) -> bool:
    if relative.endswith('/memory-writes.jsonl'):
        if not isinstance(row.get('ts'),str) or not isinstance(row.get('file'),str):
            return False
        try:
            if datetime.fromisoformat(row['ts'].replace('Z','+00:00')).tzinfo is None:
                return False
        except ValueError:
            return False
        return all(isinstance(row.get(key,[]),list) and all(isinstance(item,str) for item in row.get(key,[]))
                   for key in ('additions','evictions'))
    return (row.get('overall') in ('ok','warn','critical') and isinstance(row.get('findings',[]),list)
            and all(isinstance(finding,dict) and finding.get('severity') in ('ok','warn','critical')
                    and isinstance(finding.get('message'),str) for finding in row.get('findings',[])))


def _health_status(row: dict[str, Any]) -> str:
    status = {'overall':row['overall'], 'findings':[]}
    if row['overall'] == 'critical':
        status['findings'] = [{'severity':'critical',
                              'message':'Memory diagnostic details are unavailable under the current policy.'}]
    return json.dumps(status)


def _read_log(memory, connection, scope: MemoryScope, relative: str, content: str, timestamp: str) -> str:
    health = relative.endswith('/memory-health.jsonl')
    lines = [line for line in content.splitlines() if line.strip()][-1 if health else -500:]
    candidates, items = [], []
    for line in lines:
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if not isinstance(row,dict) or not _valid_log_row(row,relative):
            continue
        text = line + '\n' + '\n'.join(_strings(row))
        candidates.append((line,row,text))
        items.append({'type':'idea','title':'Native retained log','content':text})
    if not items:
        return ''
    checked = memory._native('validate_batch',items=items)['results']
    rows = []
    hot_categories = {path: category for category, path in HOT_FILES.items()}
    current_additions = {}
    for (line,row,text),item,result in zip(candidates,items,checked,strict=True):
        row_timestamp = row.get('ts') if isinstance(row.get('ts'),str) else timestamp
        if (result.get('ok') and result.get('item') == item
                and not memory._filter_history(connection,scope,text,row_timestamp)['excluded']):
            if health:
                rows.append(line)
            elif row.get('updated_by') == 'MemorySystem.add':
                additions, evictions = row.get('additions',[]), row.get('evictions',[])
                if any(re.search(r'SmokeTest|smoke-test',entry,re.IGNORECASE) for entry in additions):
                    continue
                if row['file'] not in hot_categories:
                    continue
                if row['file'] not in current_additions:
                    # Check the whole registry/file invariant once per category, not once per fact.
                    snapshot = memory._hot_snapshot(connection, hot_categories[row['file']])
                    current_additions[row['file']] = set(snapshot['entries'])
                confirmed = [entry for entry in additions if entry in current_additions[row['file']]]
                # Retained audit rows cannot establish that an uncommitted fact was learned.
                if additions and not confirmed:
                    continue
                additions = confirmed
                rows.append(json.dumps({'ts':row['ts'], 'file':row['file'], 'updated_by':row['updated_by'],
                                        'additions':additions[:2], 'evictions':evictions[:1],
                                        'additions_count':len(additions), 'evictions_count':len(evictions)}))
        elif health:
            rows.append(_health_status(row))
    return '\n'.join(rows)


def read(memory, scope: MemoryScope, path: str) -> dict[str, Any]:
    rejected = {'ok':False, 'content':'', 'excluded':True}
    with memory._transaction() as connection:
        source, relative = _source_path(memory,scope,path)
        if relative in CONTEXT_FILES and source.stat().st_size > 256 * 1024:
            raise MemoryUnavailable('The native identity source exceeds the 256 KiB limit')
        content = source.read_text(encoding='utf-8')
        if relative in CONTEXT_FILES and len(content.encode('utf-8')) > 256 * 1024:
            raise MemoryUnavailable('The native identity source exceeds the 256 KiB limit')
        timestamp = _source_time(source.stat())
        if relative in LOG_FILES:
            return {'ok':True, 'content':_read_log(memory,connection,scope,relative,content,timestamp),
                    'excluded':False, 'historical':True}
        decoded = ''
        if source.suffix in ('.json','.jsonl'):
            values = ([json.loads(line) for line in content.splitlines() if line.strip()]
                      if source.suffix == '.jsonl' else [json.loads(content)])
            decoded = '\n'.join(text for value in values for text in _strings(value))
        for text in (content,decoded) if decoded else (content,):
            checked = memory._validate({'type':'idea','title':'Native retained source','content':text},text,'project')
            if checked:
                return {**rejected, 'reason':'Native validation rejected this source text'}
        filtered = _admit(memory, connection, scope, '\n'.join((content, decoded)) if decoded else content,
                          relative, timestamp)
        if filtered['excluded']:
            return {**rejected, 'reason':'This retained source predates a correction or contains a removed claim'}
        return {'ok':True, 'content':content, 'excluded':False, 'historical':relative.startswith('LIFEOS/MEMORY/LEARNING/')}


def filter_content(memory, scope: MemoryScope, content: str, timestamp: str) -> dict[str, Any]:
    if (not CATEGORIES <= set(scope.read) or '*' not in scope.projects
            or not isinstance(content,str) or not isinstance(timestamp,str)):
        return {'content':'', 'excluded':True}
    if memory._validate({'type':'idea','title':'Native retained context','content':content},content,'project'):
        return {'content':'', 'excluded':True}
    return memory.filter_history(scope,content,timestamp)
