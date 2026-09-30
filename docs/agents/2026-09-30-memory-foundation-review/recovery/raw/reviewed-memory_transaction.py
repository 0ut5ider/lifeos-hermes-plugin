# ABOUTME: Journals native file publication so interrupted memory operations can recover.
# ABOUTME: Serializes cooperating writers and keeps temporary recovery copies private.

from contextlib import contextmanager
import base64
import fcntl
import json
import os
from pathlib import Path
import tempfile


def publish(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, name = tempfile.mkstemp(prefix=".memory-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
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
    def __init__(self, state: Path, resolve):
        self.state = state
        self.resolve = resolve
        self.journal = state / "memory-operation.json"

    @contextmanager
    def lock(self):
        self.state.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor = os.open(self.state / "memory-access.lock", os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        finally:
            os.close(descriptor)

    def prepare(self, writer: str, request_id: str, paths: list[str]) -> None:
        copies = []
        for name in sorted(set(paths)):
            path = self.resolve(name)
            copies.append({"path": name, "data": base64.b64encode(path.read_bytes()).decode() if path.exists() else None})
        publish(self.journal, json.dumps({"writer": writer, "request_id": request_id, "copies": copies}).encode())

    def recover(self, connection) -> None:
        if not self.journal.exists():
            return
        operation = json.loads(self.journal.read_text())
        row = connection.execute("SELECT receipt FROM operations WHERE writer=? AND request_id=?",
                                 (operation["writer"], operation["request_id"])).fetchone()
        if row is not None and json.loads(row["receipt"])["status"] != "unknown":
            self.journal.unlink()
            return
        for copy in operation["copies"]:
            path = self.resolve(copy["path"])
            if copy["data"] is None:
                path.unlink(missing_ok=True)
            else:
                publish(path, base64.b64decode(copy["data"], validate=True))
        connection.execute("DELETE FROM operations WHERE writer=? AND request_id=?",
                           (operation["writer"], operation["request_id"]))
        connection.commit()
        self.journal.unlink()

    def finish(self) -> None:
        self.journal.unlink(missing_ok=True)
