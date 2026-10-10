# ABOUTME: Disposes current admitted Content items through recoverable fixed owner file moves.
# ABOUTME: Keeps media in native trash and removes isolated derivatives after the receipt commits.
import hashlib
import json
import os
from pathlib import Path
import re
from uuid import uuid4

from .memory_access import MemoryUnavailable
from .memory_content import EVENTS, validate_output
from .memory_moves import fingerprint, inventory
from .memory_source_review import _retirement_digest
from .memory_tab_freshness import _checked
from . import memory_operational_history as history


PIPELINE = 'LIFEOS/MEMORY/STATE/content-pipeline'


def resolve_move(memory, name):
    if not isinstance(name, str) or ':' not in name:
        raise MemoryUnavailable('Content disposal requires a declared owner path')
    kind, value = name.split(':', 1)
    if not value or len(os.fsencode(value)) > 255 or Path(value).name != value or value in {'.', '..'} or '\x00' in value:
        raise MemoryUnavailable('Content disposal requires a bounded owner filename')
    if kind in {'inbox', 'trash'}:
        inbox = memory.root.parent / 'Recordings/Inbox'
        path = inbox / ('.trash' if kind == 'trash' else '') / value
        if path.resolve() != path or path.is_symlink():
            raise MemoryUnavailable('Content disposal changes its physical owner inbox')
        for parent in (memory.root.parent/'Recordings', inbox, path.parent):
            if parent.exists() and (not parent.is_dir() or parent.is_symlink() or parent.stat().st_uid != os.getuid()):
                raise MemoryUnavailable('Content disposal changes its owner inbox directory')
        return path
    if kind not in {'artifacts', 'quarantine'} or re.fullmatch('[A-Za-z0-9]{1,200}', value) is None:
        raise MemoryUnavailable('Content disposal requires a fixed derivative directory')
    folder = 'artifacts' if kind == 'artifacts' else '.disposal'
    return _checked(memory, memory.root / PIPELINE / folder / value)


def moves_for(memory, plan, identifier):
    moves = []
    source = plan['path']
    if source:
        path = Path(source)
        if path != resolve_move(memory, 'inbox:' + path.name):
            raise MemoryUnavailable('Content disposal preserves media outside the fixed owner inbox')
        if path.exists():
            for selected in (path, Path(str(path) + '.md')):
                original = resolve_move(memory, 'inbox:' + selected.name)
                digest = fingerprint(original)
                if digest is not None:
                    moves.append({'source': 'inbox:' + selected.name, 'destination': 'trash:' + selected.name,
                                  'digest': digest, 'remove': False})
    artifacts = resolve_move(memory, 'artifacts:' + identifier)
    digest = fingerprint(artifacts)
    if digest is not None:
        if not artifacts.is_dir():
            raise MemoryUnavailable('Content disposal requires a selected derivative directory')
        moves.append({'source': 'artifacts:' + identifier, 'destination': 'quarantine:' + uuid4().hex,
                      'digest': digest, 'remove': True, 'inventory': inventory(artifacts)})
    memory.transaction.moves.before(moves)
    return moves


def dispose(memory, scope, identifier, *, check_current):
    check_current()
    streamed = {EVENTS: None}
    with memory._transaction() as connection:
        retired = _retirement_digest(connection)
        with history.snapshot(memory, scope, connection, check_current=check_current, sources=streamed,
                require_newline=False, objects_only=False, allow_unfinished_utf8=False,
                require_all_admitted=True) as (descriptor, fingerprints):
            plan = memory._native('content_delete_plan', id=identifier, history_descriptor=descriptor,
                source_descriptors=(descriptor,))
            check_current()
            if history.fingerprint(memory, EVENTS, sources=streamed) != fingerprints[0]:
                raise MemoryUnavailable('Content ledger changes during native disposal preparation')
        if (not isinstance(plan, dict) or set(plan) != {'status', 'body', 'event', 'path', 'live'}
                or type(plan['status']) is not int or plan['status'] not in {200, 404}
                or not isinstance(plan['body'], dict) or type(plan['live']) is not bool
                or not (plan['path'] is None or isinstance(plan['path'], str))
                or not (plan['event'] is None or isinstance(plan['event'], dict))):
            raise MemoryUnavailable('Native Content disposal changes its plan')
        validate_output(memory, scope, connection, plan)
        if plan['event'] is None:
            check_current()
            if _retirement_digest(connection) != retired or history.fingerprint(memory, EVENTS, sources=streamed) != fingerprints[0]:
                raise MemoryUnavailable('Content missing delivery preserves later authority and source changes')
            return {'status': plan['status'], 'body': plan['body']}
        if plan['live']:
            raise MemoryUnavailable('Live Content disposal requires governed runner cancellation')
        entries = moves_for(memory, plan, identifier)
        path = _checked(memory, memory._publication_path(EVENTS))
        raw = path.read_bytes()
        if raw and not raw.endswith(b'\n') or hashlib.sha256(raw).hexdigest() != fingerprints[0][2]:
            raise MemoryUnavailable('Content disposal requires the current terminated ledger')
        event = json.dumps(plan['event'], ensure_ascii=False, separators=(',', ':')).encode() + b'\n'
        expected = hashlib.sha256(raw + event).hexdigest()
    def remove(connection):
        check_current()
        if _retirement_digest(connection) != retired or history.fingerprint(memory, EVENTS, sources=streamed) != fingerprints[0]:
            raise MemoryUnavailable('Content disposal preserves a later ledger or retirement change')
        memory.transaction.prepare_moves(entries)
        result = memory._native('content_delete_append', event=plan['event'])
        path.chmod(0o600)
        if result != {'ok': True} or history.fingerprint(memory, EVENTS, sources=streamed)[2] != expected:
            raise MemoryUnavailable('Content disposal changes its native tombstone bytes')
        check_current()
        memory.transaction.moves.apply(entries)
        check_current()
        if _retirement_digest(connection) != retired or history.fingerprint(memory, EVENTS, sources=streamed)[2] != expected:
            raise MemoryUnavailable('Content disposal preserves later source and authority changes')
        response = {'ok': True, 'id': identifier, 'trashed': sum(not entry['remove'] for entry in entries),
                    'artifactsRemoved': True, 'runnerKicked': False}
        validate_output(memory, scope, connection, response)
        return {'status': 'committed', 'response': response}
    receipt = memory._operation(scope, 'content-delete-' + uuid4().hex, {'operation': 'content_delete'}, remove,
        publication_digests={EVENTS: expected})
    if receipt['status'] != 'committed':
        raise MemoryUnavailable('Content disposal needs owner recovery')
    with memory._transaction() as connection:
        check_current()
        if _retirement_digest(connection) != retired or history.fingerprint(memory, EVENTS, sources=streamed)[2] != expected:
            raise MemoryUnavailable('Content disposal delivery preserves later authority and ledger changes')
        validate_output(memory, scope, connection, receipt['response'])
        check_current()
    return {'status': 200, 'body': receipt['response']}
