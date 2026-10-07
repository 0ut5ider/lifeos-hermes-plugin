# ABOUTME: Records owner review of exact native system and identity source contents.
# ABOUTME: Keeps source approvals bound to current retirement state without storing another fact body.
import hashlib
import json
from pathlib import Path
import re

from .memory_access import MemoryUnavailable, _now
from .memory_policy import CATEGORIES
from .memory_sources import (CONTEXT_FILES, TELOS_SOURCES, FRESHNESS_TELOS_SOURCES, is_state_source,
                             SYSTEM_FILES, SYSTEM_PREFIXES, CORPUS_LIMIT,
                             SOURCE_COUNT_LIMIT, _markdown_source, _text_source, authorize,
                             is_evidence_source, json_projection, markdown_projection, INTERVIEW_SETUP_FILES, is_deny_source, is_sync_source)


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _source_digest(memory, scope, relative, content):
    return _digest({'root': str(memory.root), 'principal': scope.principal,
                    'path': relative, 'content': content})


def _classification(relative):
    if relative in INTERVIEW_SETUP_FILES:
        return 'interview_setup'
    if is_evidence_source(relative):
        return 'evidence'
    if relative in CONTEXT_FILES | TELOS_SOURCES | FRESHNESS_TELOS_SOURCES or is_state_source(relative):
        return 'owner_context'
    if is_deny_source(relative):
        return 'deny_hashes'
    if is_sync_source(relative):
        return 'derived_sync'
    if (relative in SYSTEM_FILES or relative.startswith(SYSTEM_PREFIXES)
            or re.fullmatch(r'skills/[^/.][^/]*/SKILL\.md', relative)):
        return 'system'
    raise ValueError('Source review supports installed system Markdown, owner identity, and TELOS sources')


def _retirement_digest(connection):
    rows = connection.execute("""SELECT id, claim_digest, claim_words, category, project, revision, status, updated
        FROM records AS retained WHERE status IN ('forgotten','superseded')
        AND NOT EXISTS (SELECT 1 FROM records AS current WHERE current.status='active'
            AND current.claim_digest=retained.claim_digest AND current.category=retained.category
            AND current.project=retained.project) ORDER BY id""").fetchall()
    return _digest([dict(row) for row in rows])


def is_reviewed(memory, connection, scope, relative, content):
    row = connection.execute('SELECT * FROM source_reviews WHERE principal=? AND path=?',
                             (scope.principal, relative)).fetchone()
    if row is None:
        return False
    _classification(relative)
    return (row['digest'] == _source_digest(memory, scope, relative, content)
            and row['retirement_digest'] == _retirement_digest(connection))


def _snapshot(memory, connection, scope, paths):
    authorize(scope)
    if not CATEGORIES <= set(scope.write):
        raise MemoryUnavailable('Source review requires unrestricted owner write access')
    if (not isinstance(paths, list) or not paths or len(paths) > SOURCE_COUNT_LIMIT
            or any(not isinstance(path, str) for path in paths) or len(set(paths)) != len(paths)):
        raise ValueError('Choose distinct installed source paths within the review limit')
    sources = []
    total = 0
    for relative in paths:
        if relative.startswith('/') or any(part in ('.', '..', '') for part in relative.split('/')):
            raise ValueError('Source review needs exact installation-relative paths')
        classification = _classification(relative)
        source, timestamp = (_text_source(memory, scope, str(memory.root / relative),
                                         suffix=Path(relative).suffix, interview_setup=True)
                             if classification == 'interview_setup' else
                             _text_source(memory, scope, str(memory.root / relative), suffix='.json', evidence=True)
                             if classification == 'evidence' else
                             _text_source(memory, scope, str(memory.root / relative),
                                          suffix=Path(relative).suffix, deny_hashes=True)
                             if classification == 'deny_hashes' else
                             _text_source(memory, scope, str(memory.root / relative), suffix=Path(relative).suffix, derived_sync=True)
                             if classification == 'derived_sync' else
                             _markdown_source(memory, scope, str(memory.root / relative)))
        projection = (json_projection(source['content']) if classification == 'evidence' or classification in {'deny_hashes', 'derived_sync'} and relative.endswith('.json') else
                      markdown_projection(memory, relative, source['content']))
        total += len(source['content'].encode())
        if total > CORPUS_LIMIT:
            raise MemoryUnavailable('The reviewed sources exceed their transport limit')
        sources.append({**source, 'classification': classification, 'timestamp': timestamp, 'projection': projection})
    checked = memory._native('validate_source_batch',
        contents=[(source['projection'] or '') + '\n' + source['path'] for source in sources])['accepted']
    result = []
    for source, valid in zip(sources, checked, strict=True):
        relative = source['relative']
        labels = relative.replace('-', ' ').replace('_', ' ')
        accepted = (valid is True and source['projection'] is not None and not memory._filter_history(connection, scope,
            '\n'.join((source['projection'], relative, labels)), source['timestamp'], reviewed=True)['excluded'])
        result.append({'path': relative, 'classification': source['classification'],
                       'digest': _source_digest(memory, scope, relative, source['content']),
                       'lastModified': source['lastModified'],
                       'accepted': accepted, 'content': source['content'] if accepted else ''})
    retirement = _retirement_digest(connection)
    signature = _digest({'root': str(memory.root), 'scope': scope.signature,
                         'retirement': retirement, 'sources': result})
    return {'sources': result, 'signature': signature, 'retirement_digest': retirement}


def preview(memory, scope, paths):
    with memory._transaction() as connection:
        return _snapshot(memory, connection, scope, paths)


def approve(memory, scope, paths, signature, *, check_current=None):
    if not isinstance(signature, str) or re.fullmatch('[0-9a-f]{64}', signature) is None:
        raise ValueError('Provide the exact reviewed source signature')
    with memory._transaction() as connection:
        snapshot = _snapshot(memory, connection, scope, paths)
        if check_current is not None:
            check_current()
        if signature != snapshot['signature']:
            return {'status': 'conflict', 'reason': 'Sources or retirement state changed. Review a fresh preview.'}
        if not all(source['accepted'] for source in snapshot['sources']):
            return {'status': 'rejected', 'reason': 'Source review cannot admit private or known retired content.'}
        unchanged = True
        for source in snapshot['sources']:
            row = connection.execute('SELECT digest, retirement_digest FROM source_reviews WHERE principal=? AND path=?',
                                     (scope.principal, source['path'])).fetchone()
            if row is not None and tuple(row) == (source['digest'], snapshot['retirement_digest']):
                continue
            unchanged = False
            connection.execute('INSERT OR REPLACE INTO source_reviews VALUES (?,?,?,?,?,?)',
                (scope.principal, source['path'], source['digest'], snapshot['retirement_digest'], scope.writer, _now()))
        return {'status': 'unchanged' if unchanged else 'committed', 'reviewed_sources': len(snapshot['sources'])}
