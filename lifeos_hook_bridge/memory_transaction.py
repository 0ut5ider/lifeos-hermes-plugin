# ABOUTME: Journals native file publication so interrupted memory operations can recover.
# ABOUTME: Serializes cooperating writers and keeps temporary recovery copies private.

from contextlib import contextmanager
from contextvars import ContextVar
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile


def publish(path: Path, data: bytes, *, mode: int = 0o600) -> None:
    if type(mode) is not int or not 0 <= mode <= 0o777:
        raise ValueError('Atomic publication requires a supported file mode')
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, name = tempfile.mkstemp(prefix=".memory-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fchmod(stream.fileno(), mode)
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        temporary.unlink(missing_ok=True)


class MemoryTransaction:
    def __init__(self, state: Path, resolve, *, moves=None):
        self.state = state
        self.resolve = resolve
        self.moves = moves
        self.journal = state / "memory-operation.json"
        self._descriptor = ContextVar("memory_lock_descriptor", default=None)

    @contextmanager
    def lock(self):
        self.state.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor = os.open(self.state / "memory-access.lock", os.O_CREAT | os.O_RDWR, 0o600)
        token = self._descriptor.set(descriptor)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        finally:
            self._descriptor.reset(token)
            os.close(descriptor)

    def inherited_descriptors(self) -> tuple[int, ...]:
        descriptor = self._descriptor.get()
        return () if descriptor is None else (descriptor,)

    def flush_publication(self) -> None:
        if not self.journal.exists():
            return
        for copy in json.loads(self.journal.read_text())["copies"]:
            path = self.resolve(copy["path"])
            if path.exists():
                descriptor = os.open(path, os.O_RDONLY)
                try:
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
            if path.parent.exists():
                descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)

    def prepare(self, writer: str, request_id: str, paths: list[str], *, expected=None) -> None:
        if expected is not None and (not isinstance(expected, dict) or set(expected) != set(paths)
                or any(value is not None and (not isinstance(value, str) or re.fullmatch('[0-9a-f]{64}', value) is None)
                       for value in expected.values())):
            raise ValueError('Expected publications require one exact digest for each destination')
        copies = []
        for name in sorted(set(paths)):
            path = self.resolve(name)
            present = path.exists()
            copies.append({"path": name, "data": base64.b64encode(path.read_bytes()).decode() if present else None,
                           "mode": stat.S_IMODE(path.stat().st_mode) if present else None})
            if expected is not None:
                copies[-1]['after_digest'] = expected[name]
        publish(self.journal, json.dumps({"writer": writer, "request_id": request_id, "copies": copies}).encode())

    @staticmethod
    def _move_publications(operation) -> None:
        from .memory_access import MemoryUnavailable
        copies = operation.get('copies')
        if (not isinstance(copies, list) or not copies
                or any(not isinstance(copy, dict) or not isinstance(copy.get('after_digest'), str)
                       or re.fullmatch('[0-9a-f]{64}', copy['after_digest']) is None for copy in copies)):
            raise MemoryUnavailable('Content move recovery requires expected ledger publications')

    def prepare_moves(self, entries) -> None:
        from .memory_access import MemoryUnavailable
        if self.moves is None or not self.journal.exists():
            raise MemoryUnavailable('Content moves require a reserved owner publication')
        operation = json.loads(self.journal.read_text())
        if 'moves' in operation:
            raise MemoryUnavailable('Content moves already have a recovery reservation')
        self._move_publications(operation)
        self.moves.before(entries)
        operation['moves'] = entries
        publish(self.journal, json.dumps(operation).encode())

    def _check_restore(self, copy):
        from .memory_access import MemoryUnavailable
        if (not isinstance(copy, dict) or set(copy) not in ({'path', 'data', 'after_digest'}, {'path', 'data', 'mode', 'after_digest'})
                or not isinstance(copy['path'], str) or not copy['path']
                or copy['after_digest'] is not None and (not isinstance(copy['after_digest'], str)
                    or re.fullmatch('[0-9a-f]{64}', copy['after_digest']) is None)
                or copy['data'] is not None and not isinstance(copy['data'], str)):
            raise MemoryUnavailable('The expected publication journal has invalid artifact metadata')
        try:
            original = None if copy['data'] is None else hashlib.sha256(
                base64.b64decode(copy['data'], validate=True)).hexdigest()
        except ValueError as error:
            raise MemoryUnavailable('The expected publication journal has invalid recovery bytes') from error
        path = self.resolve(copy['path'])
        current = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
        if current not in {original, copy['after_digest']}:
            raise MemoryUnavailable('Publication recovery preserves a later artifact edit')

    def _preserve_current(self, operation) -> None:
        # Recovery cannot tell an interrupted write from a later owner edit, so it keeps
        # every destination whose bytes differ from the journal original before it restores.
        kept = {}
        for copy in operation['copies']:
            path = self.resolve(copy['path'])
            if not path.is_file():
                continue
            current = path.read_bytes()
            original = None if copy['data'] is None else base64.b64decode(copy['data'], validate=True)
            if current != original:
                kept[copy['path']] = current
        if not kept:
            return
        identity = hashlib.sha256(json.dumps([operation['writer'], operation['request_id']]).encode()).hexdigest()[:32]
        folder = self.state / 'recovery-preserved' / identity
        files = {}
        for name, data in kept.items():
            digest = hashlib.sha256(data).hexdigest()
            publish(folder / digest, data)
            files[name] = digest
        publish(folder / 'preserved.json', (json.dumps({
            'writer': operation['writer'], 'request_id': operation['request_id'], 'files': files},
            sort_keys=True, indent=2) + '\n').encode())

    def recover(self, connection) -> None:
        from .memory_access import MemoryUnavailable
        if not self.journal.exists():
            return
        try:
            operation = json.loads(self.journal.read_text())
        except (ValueError, UnicodeError, RecursionError) as error:
            raise MemoryUnavailable('The publication recovery journal has invalid content') from error
        if (not isinstance(operation, dict) or set(operation) not in ({'writer', 'request_id', 'copies'}, {'writer', 'request_id', 'copies', 'moves'})
                or not isinstance(operation['writer'], str) or not operation['writer']
                or not isinstance(operation['request_id'], str) or not 1 <= len(operation['request_id']) <= 256
                or not isinstance(operation['copies'], list)):
            raise MemoryUnavailable('The publication recovery journal has invalid operation metadata')
        if 'moves' in operation:
            self._move_publications(operation)
            if self.moves is None:
                raise MemoryUnavailable('This owner cannot recover Content moves')
            self.moves.validate(operation['moves'])
        names = set()
        for copy in operation['copies']:
            if (not isinstance(copy, dict) or set(copy) not in ({'path', 'data'}, {'path', 'data', 'after_digest'},
                    {'path', 'data', 'mode'}, {'path', 'data', 'mode', 'after_digest'})
                    or not isinstance(copy['path'], str) or not copy['path'] or copy['path'] in names
                    or copy['data'] is not None and not isinstance(copy['data'], str)):
                raise MemoryUnavailable('The publication recovery journal has invalid recovery targets')
            if 'mode' in copy and (copy['mode'] is not None if copy['data'] is None else
                    type(copy['mode']) is not int or not 0 <= copy['mode'] <= 0o777):
                raise MemoryUnavailable('The publication recovery journal has invalid original permissions')
            names.add(copy['path'])
            try:
                if copy['data'] is not None:
                    base64.b64decode(copy['data'], validate=True)
            except ValueError as error:
                raise MemoryUnavailable('The publication recovery journal has invalid recovery bytes') from error
            self.resolve(copy['path'])
        row = connection.execute("SELECT receipt FROM operations WHERE writer=? AND request_id=?",
                                 (operation["writer"], operation["request_id"])).fetchone()
        if row is not None and json.loads(row["receipt"])["status"] != "unknown":
            if 'moves' in operation:
                self.moves.finish(operation['moves'])
            self.journal.unlink()
            return
        expected = any('after_digest' in copy for copy in operation['copies'])
        if expected:
            for copy in operation['copies']:
                self._check_restore(copy)
        if 'moves' in operation:
            self.moves.recovery_check(operation['moves'])
        self._preserve_current(operation)
        if 'moves' in operation:
            self.moves.recover(operation['moves'])
        for copy in operation["copies"]:
            if expected:
                self._check_restore(copy)
            path = self.resolve(copy["path"])
            if copy["data"] is None:
                path.unlink(missing_ok=True)
            else:
                publish(path, base64.b64decode(copy["data"], validate=True), mode=copy.get('mode', 0o600))
        connection.execute("DELETE FROM operations WHERE writer=? AND request_id=?",
                           (operation["writer"], operation["request_id"]))
        connection.commit()
        self.journal.unlink()

    def finish(self) -> None:
        if self.journal.exists():
            operation = json.loads(self.journal.read_text())
            if 'moves' in operation:
                self.moves.finish(operation['moves'])
        self.journal.unlink(missing_ok=True)
