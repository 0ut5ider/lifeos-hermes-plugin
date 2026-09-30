# ABOUTME: Publishes native LifeOS proposals with distinct creation and approval permissions.
# ABOUTME: Reports queued and diverted outcomes without treating a proposal as a saved current fact.
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .memory_access import MemoryUnavailable, _digest, _now
from .memory_policy import CATEGORIES, MemoryScope

QUEUE = 'LIFEOS/MEMORY/OBSERVABILITY/pending-proposals.jsonl'
UPGRADES = 'LIFEOS/MEMORY/UPGRADES/records'


def enqueue(memory, scope: MemoryScope, item: dict[str, Any], request_id: str,
            source_session: str) -> dict[str, Any]:
    if 'create' not in scope.proposals or not CATEGORIES <= set(scope.read) or '*' not in scope.projects:
        return {'ok':False, 'code':'EINVAL_ITEM', 'message':'This context has no complete proposal creation grant'}
    checked = memory._native('validate', item=item)
    if not checked.get('ok') or checked.get('item') != item:
        return {'ok':False, 'code':'EINVAL_ITEM', 'message':checked.get('message', 'Native validation changed the proposal')}

    def save(connection):
        if memory._blocked(connection, item["edit"]):
            return {"status":"rejected", "reason":"This proposal needs explicit reactivation after correction or forgetting"}
        result = memory._native('add', item=item)
        if not result.get('ok'):
            return {'status':'rejected', 'reason':result.get('message', 'Native proposal creation failed')}
        identifier = result.get('detail', {}).get('id')
        if not isinstance(identifier, str) or not identifier or '/' in identifier or '..' in identifier:
            raise MemoryUnavailable('Native proposal creation did not return a bounded reference')
        queue = memory._path(QUEUE)
        rows = [json.loads(line) for line in queue.read_text().splitlines() if line.strip()] if queue.exists() else []
        matches = [row for row in rows if row.get('id') == identifier]
        if len(matches) == 1:
            row = matches[0]
            if row.get('edit') != item['edit'] or row.get('status') != 'pending':
                raise MemoryUnavailable('Native proposal did not queue the requested pending edit')
            target = Path(row['target_file'])
            if not target.is_absolute():
                target = memory.root / target
            relative = target.relative_to(memory.root).as_posix()
            memory._path(relative)
            connection.execute('INSERT INTO proposals VALUES (?,?,?,?,?,?,?,?,?,?)',
                               (identifier, QUEUE, relative, _digest(memory._path(relative).read_text()) if memory._path(relative).is_file() else '',
                                _digest(json.dumps(row, sort_keys=True)),
                                1, 'pending', scope.writer, source_session, _now()))
            return {'status':'pending', 'proposal_reference':{'id':identifier, 'revision':1},
                    'destination':str(queue), 'source':{'kind':'native-proposal', 'session':source_session},
                    'detail':result['detail']}
        if matches:
            raise MemoryUnavailable('The native proposal reference is ambiguous')
        destination = memory._path(UPGRADES + '/' + identifier + '.md')
        if not destination.is_file():
            raise MemoryUnavailable('Native proposal has neither a queued row nor an upgrade record')
        text = destination.read_text()
        claim = item['edit'].strip()[:1000]
        if '\n## Claim\n\n' + claim + '\n' not in text:
            raise MemoryUnavailable('Native upgrade diversion did not preserve the requested claim')
        return {'status':'diverted', 'destination':str(destination), 'upgrade_id':identifier,
                'source':{'kind':'native-proposal', 'session':source_session},
                'reason':'Native LifeOS routed this change to an upgrade record; it is not a queued memory edit'}

    receipt = memory._operation(scope, request_id, {'operation':'native_proposal', 'item':item,
                                                   'source_session':source_session}, save)
    if receipt['status'] not in ('pending', 'diverted'):
        return {'ok':False, 'code':'EWRITE_FAILED', 'message':receipt.get('reason', 'Proposal did not publish'), 'receipt':receipt}
    return {'ok':True, 'type':'proposal', 'path':receipt['destination'],
            'detail':receipt.get('detail', {'id':receipt.get('upgrade_id'), 'status':'diverted'}), 'receipt':receipt}


def _permitted(scope: MemoryScope, permission: str) -> bool:
    return permission in scope.proposals and CATEGORIES <= set(scope.read) and '*' in scope.projects


def _current_row(memory, record) -> dict[str, Any]:
    path = memory._path(record['path'])
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    matches = [row for row in rows if row.get('id') == record['id']]
    if len(matches) != 1 or _digest(json.dumps(matches[0], sort_keys=True)) != record['digest']:
        from .memory_access import MemoryConflict
        raise MemoryConflict('The native proposal changed outside its recorded revision')
    return matches[0]


def review(memory, scope: MemoryScope, *, include_resolved: bool = False) -> list[dict[str, Any]]:
    if not _permitted(scope, 'review'):
        return []
    with memory._transaction() as connection:
        rows = connection.execute("SELECT * FROM proposals ORDER BY updated" if include_resolved else
                                  "SELECT * FROM proposals WHERE status='pending' ORDER BY updated")
        return [{**_current_row(memory, row), 'reference':{'id':row['id'], 'revision':row['revision']},
                 'writer':row['writer'], 'source_session':row['source_session']}
                for row in rows]


def decision_row(memory, scope: MemoryScope, reference: dict[str, Any]) -> dict[str, Any]:
    if not (_permitted(scope, 'approve') or _permitted(scope, 'auto_apply')):
        raise MemoryUnavailable('This context cannot read a native proposal decision')
    with memory._transaction() as connection:
        record = connection.execute('SELECT * FROM proposals WHERE id=?', (reference['id'],)).fetchone()
        if record is None or record['revision'] != reference['revision'] or record['status'] == 'pending':
            raise MemoryUnavailable('The resolved native proposal revision is unavailable')
        return _current_row(memory, record)


def decide(memory, scope: MemoryScope, reference: dict[str, Any], decision: str,
           request_id: str, *, content: str = "", note: str = "",
           confidence_threshold: float | None = None) -> dict[str, Any]:
    permission = 'auto_apply' if decision == 'auto_apply' else 'approve'
    if not _permitted(scope, permission):
        return {'status':'rejected', 'reason':'This context has no proposal approval grant'}
    if (decision not in ('accept', 'reject', 'edit', 'applied_elsewhere', 'auto_apply') or not isinstance(reference, dict)
            or set(reference) != {'id', 'revision'} or not isinstance(reference['id'], str)
            or type(reference['revision']) is not int or reference['revision'] < 1):
        return {'status':'rejected', 'reason':'An exact pending proposal reference and supported native decision are required'}

    if (not isinstance(content, str) or not isinstance(note, str) or len(content) > 65536 or len(note) > 65536
            or (decision == 'edit' and not content.strip()) or (decision == 'applied_elsewhere' and not note.strip())
            or (decision != 'edit' and content) or (decision != 'applied_elsewhere' and note)
            or (decision == 'auto_apply' and (type(confidence_threshold) not in (int, float) or not 0 <= confidence_threshold <= 1))
            or (decision != 'auto_apply' and confidence_threshold is not None)):
        return {'status':'rejected', 'reason':'The native proposal decision arguments are invalid'}

    if note:
        note_item = {'type':'idea', 'title':'Proposal resolution', 'content':note}
        checked = memory._native('validate', item=note_item)
        if not checked.get('ok') or checked.get('item') != note_item:
            return {'status':'rejected', 'reason':'Native validation rejected the resolution note'}

    def resolve(connection):
        record = connection.execute('SELECT * FROM proposals WHERE id=?', (reference['id'],)).fetchone()
        if record is None or record['status'] != 'pending' or record['revision'] != reference['revision']:
            return {'status':'conflict', 'reason':'The proposal reference is no longer pending at this revision'}
        row = _current_row(memory, record)
        if decision in ('accept', 'edit', 'auto_apply'):
            target = memory._path(record['target'])
            if not target.is_file() or _digest(target.read_text()) != record['target_digest']:
                return {'status':'conflict', 'reason':'The proposal target changed before approval'}
            item = {'type':'proposal', 'target_file':row['target_file'], 'target_kind':row.get('target_kind', 'identity'),
                    'edit':content if decision == 'edit' else row['edit'], 'confidence':row['confidence'], 'rationale':row['rationale']}
            checked = memory._native('validate', item=item)
            if not checked.get('ok') or checked.get('item') != item:
                return {'status':'rejected', 'reason':'Native validation rejected the pending proposal'}
            if memory._blocked(connection, item['edit']):
                return {'status':'rejected', 'reason':'This proposal needs explicit reactivation after correction or forgetting'}
        result = memory._native('proposal_decision', identifier=reference['id'], decision=decision, content=content,
                                note=note, confidence_threshold=confidence_threshold)
        if not result.get('ok'):
            return {'status':'rejected', 'reason':result.get('reason', 'Native proposal decision failed')}
        row = result['row']
        expected = {'accept':'accepted', 'reject':'rejected', 'edit':'edited',
                    'applied_elsewhere':'applied-elsewhere', 'auto_apply':'auto-applied'}[decision]
        if row.get('status') != expected:
            raise MemoryUnavailable('Native proposal decision returned a different lifecycle outcome')
        connection.execute('UPDATE proposals SET digest=?,revision=revision+1,status=?,updated=? WHERE id=?',
                           (_digest(json.dumps(row, sort_keys=True)), expected, _now(), record['id']))
        return {'status':'committed', 'proposal_status':expected,
                'proposal_reference':{'id':record['id'], 'revision':record['revision'] + 1},
                'destination':str(memory._path(record['target'])), 'creator':record['writer']}

    return memory._operation(scope, request_id, {'operation':'proposal_decision', 'reference':reference,
                                                'decision':decision, 'content':content, 'note':note,
                                                'confidence_threshold':confidence_threshold}, resolve)
