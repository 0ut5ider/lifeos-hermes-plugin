# ABOUTME: Previews native source adoption and records approved identities without copying facts.
# ABOUTME: Rejects changed previews and preserves native history and forgotten source exclusions.
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any
from uuid import uuid4

from .memory_access import HOT_FILES, MemoryUnavailable, _claim_digest, _claim_words, _digest, _now
from .memory_policy import CATEGORIES, MemoryScope
from .memory_proposals import QUEUE
from .memory_sources import source_labels, source_projection


def _owner(scope: MemoryScope) -> bool:
    return bool(scope.principal) and CATEGORIES <= set(scope.read) and CATEGORIES <= set(scope.write) and '*' in scope.projects


def _body_source(text: str, discovered: str) -> tuple[int, str]:
    frontmatter = re.match(r'^---\n[\s\S]*?\n---', text)
    start = frontmatter.end() if frontmatter else 0
    raw = text[start:]
    expected = raw.strip() if frontmatter else raw
    if expected != discovered:
        raise MemoryUnavailable('Native discovery changed its source body')
    start += len(raw) - len(raw.lstrip('\r\n'))
    return start, text[start:].rstrip('\r\n')


def _sections(text: str, discovered: str) -> list[tuple[int, str]]:
    start, body = _body_source(text, discovered)
    initial = re.match(r'^# [^\n]+\n(?:[ \t]*\n)+', body)
    cursor = initial.end() if initial else 0
    markers = list(re.finditer(r'^## Appended [^\n]+\n<!-- source_session: [^\n]+ -->\n(?:[ \t]*\n)+', body, re.MULTILINE))
    sections = []
    for marker in markers:
        content = body[cursor:marker.start()].strip('\r\n')
        if content.strip():
            offset = body.find(content, cursor, marker.start())
            sections.append((start + offset, content))
        cursor = marker.end()
    content = body[cursor:].strip('\r\n')
    if content.strip():
        sections.append((start + body.find(content, cursor), content))
    return sections


def _snapshot(memory, connection, scope: MemoryScope) -> dict[str, Any]:
    records = [dict(row) for row in connection.execute('SELECT * FROM records ORDER BY id')]
    proposals = [dict(row) for row in connection.execute('SELECT * FROM proposals ORDER BY id')]
    paths: dict[str, str] = {}
    candidates, pending, excluded, items = [], [], [], []

    def add(path: str, position: int, content: str, category: str, kind: str, item: dict[str, Any]) -> None:
        existing = [row for row in records if row['path'] == path and row['digest'] == _digest(content)]
        if existing:
            return
        if memory._blocked(connection,content):
            excluded.append({'path':path,'reason':'This retained claim requires explicit reactivation'})
            return
        timestamp = (datetime.fromtimestamp(memory._path(path).stat().st_mtime,timezone.utc).isoformat()
                     if kind == 'learning' else _now())
        if memory._filter_history(connection,scope,content,timestamp)['excluded']:
            excluded.append({'path':path,'reason':'This source predates a correction or contains a removed claim'})
            return
        candidates.append({'path':path,'position':position,'content':content,'category':category,
                           'source_kind':kind,'project':''})
        items.append(item)

    for category, relative in HOT_FILES.items():
        path = memory._path(relative)
        if not path.is_file():
            continue
        text = path.read_text()
        paths[relative] = _digest(text)
        native = memory._native('read_hot',path=str(path))
        begin_marker, end_marker = '<!-- BEGIN ENTRIES -->', '<!-- END ENTRIES -->'
        if ('entries' not in native or native.get('dropped_invalid')
                or text.count(begin_marker) != 1 or text.count(end_marker) != 1
                or text.find(begin_marker) >= text.find(end_marker)):
            excluded.append({'path':relative,'reason':'The native hot-memory file needs repair'})
            continue
        start = text.index('<!-- BEGIN ENTRIES -->') + len('<!-- BEGIN ENTRIES -->')
        end = text.index('<!-- END ENTRIES -->',start)
        for content in native['entries']:
            position = text.find(content,start,end)
            if position < 0:
                raise MemoryUnavailable('Native hot-memory entries do not match the source file')
            add(relative,position,content,category,'adopted',{'type':'memory','actor':category,'content':content})

    for note in memory._native('discover')['notes']:
        if note['noteClass'] == 'memory':
            continue
        relative = Path(note['filePath']).relative_to(memory.root).as_posix()
        if not relative.startswith(('LIFEOS/MEMORY/KNOWLEDGE/','LIFEOS/MEMORY/LEARNING/')):
            raise MemoryUnavailable('Native discovery returned an unsupported source')
        path = memory._path(relative)
        text = path.read_text()
        paths[relative] = _digest(text)
        if not note['body']:
            continue
        kind = 'learning' if note['noteClass'] == 'learning' else 'adopted'
        sections = [_body_source(text,note['body'])] if kind == 'learning' else _sections(text,note['body'])
        for position, content in sections:
            if position < 0:
                raise MemoryUnavailable('Native discovery changed a learning source')
            add(relative,position,content,'project',kind,{'type':'idea','title':'Native source adoption','content':content})

    if items:
        checked = memory._native('validate_batch',items=items)['results']
        source_checked = memory._native('validate_source_batch', contents=[
            source_projection(memory, candidate['path'], candidate['content']) for candidate in candidates])['accepted']
        accepted = []
        for candidate, item, result, source_valid in zip(candidates,items,checked,source_checked,strict=True):
            labels_excluded = (candidate['category'] == 'project' and memory._filter_history(
                connection, scope, source_labels(candidate['path']), _now())['excluded'])
            if source_valid is not True or labels_excluded:
                excluded.append({'path':'[excluded source]','reason':'Source labels or metadata are excluded'})
            elif result.get('ok') and result.get('item') == item:
                accepted.append(candidate)
            else:
                excluded.append({'path':candidate['path'],'reason':'Native validation rejected this source text'})
        candidates = accepted

    queue = memory._path(QUEUE)
    if queue.is_file():
        text = queue.read_text()
        paths[QUEUE] = _digest(text)
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
        identifiers = set()
        for row in rows:
            identifier = row.get('id')
            if not isinstance(identifier,str) or not identifier or identifier in identifiers or '/' in identifier or '..' in identifier:
                raise MemoryUnavailable('The native queue has invalid or duplicate proposal references')
            identifiers.add(identifier)
            if any(record['id'] == identifier for record in proposals):
                continue
            if row.get('status') not in ('pending','sent'):
                continue
            try:
                item = {key:row[key] for key in ('target_file','edit','confidence','rationale')}
                item.update(type='proposal',target_kind=row.get('target_kind','identity'))
                result = memory._native('validate',item=item)
                if not result.get('ok') or result.get('item') != item:
                    raise ValueError('Native validation rejected this proposal')
                target = Path(row['target_file'])
                if not target.is_absolute():
                    target = memory.root / target
                relative = target.relative_to(memory.root).as_posix()
                target = memory._path(relative)
                if not target.is_file() or memory._blocked(connection,row['edit']):
                    raise ValueError('The proposal target is missing or the claim requires reactivation')
                paths[relative] = _digest(target.read_text())
                pending.append({'reference':{'id':identifier,'revision':1},'row':row,
                                'target':relative,'target_digest':paths[relative]})
            except (KeyError, ValueError, MemoryUnavailable):
                excluded.append({'path':QUEUE,'reference':identifier,
                    'reason':'The native proposal target or content is not eligible for adoption'})

    if excluded:
        checked_labels = memory._native('validate_source_batch',
            contents=[item['path'] for item in excluded])['accepted']
        for item, valid in zip(excluded, checked_labels, strict=True):
            if valid is not True or memory._filter_history(connection, scope,
                    source_labels(item['path']), _now())['excluded']:
                item['path'] = '[excluded source]'

    signature = _digest(json.dumps({'root':str(memory.root),'principal':scope.principal,
                                     'files':paths,'mtimes':{name:memory._path(name).stat().st_mtime_ns for name in paths},
                                     'records':records,'proposals':proposals,'candidates':candidates,
                                     'pending':pending,'excluded':excluded},sort_keys=True))
    return {'signature':signature,'records':candidates,'proposals':pending,'excluded':excluded,'scanned_files':len(paths)}


def preview(memory, scope: MemoryScope) -> dict[str, Any]:
    if not _owner(scope):
        raise MemoryUnavailable('Native source adoption requires an unrestricted owner context')
    with memory._transaction() as connection:
        return _snapshot(memory,connection,scope)


def adopt(memory, scope: MemoryScope, signature: str, projects: dict[str,str], request_id: str) -> dict[str, Any]:
    if not _owner(scope):
        return {'status':'rejected','reason':'Native source adoption requires an unrestricted owner context'}
    if (not isinstance(signature,str) or not re.fullmatch(r'[0-9a-f]{64}',signature)
            or not isinstance(projects,dict) or any(not isinstance(path,str) or not isinstance(project,str)
                                                    or not project.strip() or project == '*' for path,project in projects.items())):
        return {'status':'rejected','reason':'An exact native source preview and project assignments are required'}

    def apply(connection):
        snapshot = _snapshot(memory,connection,scope)
        if snapshot['signature'] != signature:
            return {'status':'conflict','reason':'The native source preview changed. Review a fresh preview before adoption.'}
        eligible = {row['path'] for row in snapshot['records'] if row['category']=='project'}
        if set(projects)-eligible:
            return {'status':'rejected','reason':'Project assignments must name a previewed native archive or learning file'}
        references = []
        for row in snapshot['records']:
            identifier = uuid4().hex
            content = row['content']
            connection.execute('INSERT INTO records VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(
                identifier,row['path'],row['category'],projects.get(row['path'],''),_digest(content),len(content),
                row['position'],1,'active','native:unattributed','',row['source_kind'],_now(),
                _claim_digest(content),len(_claim_words(content))))
            references.append({'id':identifier,'revision':1})
        for item in snapshot['proposals']:
            row = item['row']
            connection.execute('INSERT INTO proposals VALUES (?,?,?,?,?,?,?,?,?,?)',(
                row['id'],QUEUE,item['target'],item['target_digest'],_digest(json.dumps(row,sort_keys=True)),
                1,'pending','native:unattributed','',_now()))
        return {'status':'committed','facts_adopted':len(references),'proposals_adopted':len(snapshot['proposals']),
                'references':references,'excluded_sources':len(snapshot['excluded']),'native_files_changed':False}

    return memory._operation(scope,request_id,{'operation':'adopt','signature':signature,'projects':projects},apply)
