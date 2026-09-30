# ABOUTME: Governs native LifeOS memory writes and reads with stable references and permissions.
# ABOUTME: Keeps operation metadata separate from authoritative native fact contents.

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
from typing import Any, Callable
from uuid import uuid4

from .memory_policy import CATEGORIES, MemoryScope


SCHEMA_VERSION = 1
HOT_FILES = {
    "principal": "LIFEOS/USER/PRINCIPAL/PRINCIPAL_MEMORY.md",
    "assistant": "LIFEOS/USER/DIGITAL_ASSISTANT/DA_MEMORY.md",
}


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MemoryUnavailable(RuntimeError):
    pass


class NativeMemory:
    def __init__(self, installed_root: Path, *, bun: str | None = None):
        self.root = Path(installed_root).absolute()
        self.bun = bun or shutil.which("bun") or "bun"
        self.database = self.root / "LIFEOS/MEMORY/STATE/memory-access.sqlite"
        self.worker = Path(__file__).with_name("memory_native.ts")

    def _boundary(self) -> None:
        user = self.root.parent / ".config/LIFEOS/USER"
        if not user.is_dir():
            raise MemoryUnavailable("The native USER_DATA boundary is missing")
        for name in ("USER", "MEMORY"):
            path = self.root / "LIFEOS" / name
            if not path.is_symlink() or not path.is_dir() or not path.resolve().is_relative_to(user.resolve()):
                raise MemoryUnavailable(f"LifeOS {name} is outside the physical USER_DATA boundary")
        if not (self.root / "LIFEOS/TOOLS/MemorySystem.ts").is_file():
            raise MemoryUnavailable("The native LifeOS memory tools are unavailable")

    def _connect(self) -> sqlite3.Connection:
        self._boundary()
        self.database.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        connection = sqlite3.connect(self.database, timeout=30, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("BEGIN IMMEDIATE")
        try:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, SCHEMA_VERSION):
                raise MemoryUnavailable("The memory metadata schema is unsupported")
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS records (
                    id TEXT PRIMARY KEY, path TEXT NOT NULL, category TEXT NOT NULL, project TEXT NOT NULL,
                    digest TEXT NOT NULL, chars INTEGER NOT NULL, position INTEGER NOT NULL,
                    revision INTEGER NOT NULL, status TEXT NOT NULL, writer TEXT NOT NULL,
                    source_session TEXT NOT NULL, source_kind TEXT NOT NULL, updated TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS operations (
                    writer TEXT NOT NULL, request_id TEXT NOT NULL, payload_digest TEXT NOT NULL,
                    receipt TEXT NOT NULL, PRIMARY KEY(writer, request_id)
                );
            """)
            connection.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
            connection.commit()
            os.chmod(self.database, 0o600)
            return connection
        except BaseException:
            connection.close()
            raise

    @contextmanager
    def _transaction(self):
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _native(self, action: str, **values: Any) -> dict[str, Any]:
        environment = dict(os.environ)
        environment["HOME"] = str(self.root.parent)
        environment["LIFEOS_MEMORY_INTERNAL"] = "1"
        environment["BUN_CONFIG_NO_AUTO_INSTALL"] = "1"
        result = subprocess.run([self.bun, "--no-install", str(self.worker), str(self.root)],
                                input=json.dumps({"action": action, **values}), text=True,
                                capture_output=True, timeout=30, env=environment, cwd=self.root)
        if result.returncode:
            raise MemoryUnavailable("Native memory operation failed: " + result.stderr.strip()[:500])
        try:
            response = json.loads(result.stdout)
        except ValueError as error:
            raise MemoryUnavailable("Native memory returned an invalid response") from error
        if not isinstance(response, dict):
            raise MemoryUnavailable("Native memory returned an invalid result")
        return response

    def _path(self, name: str) -> Path:
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts or not name.startswith(("LIFEOS/USER/", "LIFEOS/MEMORY/")):
            raise MemoryUnavailable("Invalid native memory reference")
        path = self.root / relative
        user = (self.root.parent / ".config/LIFEOS/USER").resolve()
        if not path.resolve().is_relative_to(user):
            raise MemoryUnavailable("Native memory reference leaves the user boundary")
        return path

    @staticmethod
    def _allowed(scope: MemoryScope, record: sqlite3.Row, *, write: bool = False) -> bool:
        if record["category"] not in (scope.write if write else scope.read):
            return False
        return record["category"] != "project" or "*" in scope.projects or record["project"] in scope.projects

    def _content(self, record: sqlite3.Row) -> str:
        path = self._path(record["path"])
        if not path.is_file():
            raise MemoryUnavailable("The referenced native memory file is missing")
        text = path.read_text(encoding="utf-8")
        length = record["chars"]
        position = record["position"]
        candidate = text[position:position + length]
        if _digest(candidate) == record["digest"]:
            return candidate
        for offset in range(max(0, len(text) - length + 1)):
            candidate = text[offset:offset + length]
            if _digest(candidate) == record["digest"]:
                return candidate
        raise MemoryUnavailable("The referenced fact changed outside its recorded revision")

    def _record(self, connection: sqlite3.Connection, scope: MemoryScope, path: Path,
                content: str, category: str, project: str, source: dict[str, str]) -> dict[str, Any]:
        relative = path.relative_to(self.root).as_posix()
        text = self._path(relative).read_text(encoding="utf-8")
        position = text.find(content)
        if position < 0:
            raise MemoryUnavailable("The native writer did not save the requested fact")
        identifier = uuid4().hex
        connection.execute("INSERT INTO records VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            identifier, relative, category, project, _digest(content), len(content), position,
            1, "active", scope.writer, source.get("session", ""), source.get("kind", "explicit"), _now(),
        ))
        return {"id": identifier, "revision": 1}

    def _operation(self, scope: MemoryScope, request_id: str, payload: dict[str, Any],
                   callback: Callable[[sqlite3.Connection], dict[str, Any]]) -> dict[str, Any]:
        if not isinstance(request_id, str) or not request_id or len(request_id) > 256:
            return {"status": "rejected", "reason": "A bounded request identifier is required"}
        payload_digest = _digest(json.dumps(payload, sort_keys=True))
        reserved = False
        try:
            with self._transaction() as connection:
                prior = connection.execute("SELECT * FROM operations WHERE writer=? AND request_id=?",
                                           (scope.writer, request_id)).fetchone()
                if prior is not None:
                    if prior["payload_digest"] != payload_digest:
                        return {"status": "conflict", "reason": "This request identifier names another operation"}
                    return json.loads(prior["receipt"])
                unknown = {"status": "unknown", "reason": "The operation outcome needs recovery before retry",
                           "writer": scope.writer, "request_id": request_id}
                connection.execute("INSERT INTO operations VALUES (?,?,?,?)",
                                   (scope.writer, request_id, payload_digest, json.dumps(unknown)))
            reserved = True
            with self._transaction() as connection:
                receipt = callback(connection)
                receipt.setdefault("writer", scope.writer)
                receipt.setdefault("request_id", request_id)
                connection.execute("UPDATE operations SET receipt=? WHERE writer=? AND request_id=?",
                                   (json.dumps(receipt), scope.writer, request_id))
                return receipt
        except (MemoryUnavailable, OSError, sqlite3.Error, subprocess.TimeoutExpired) as error:
            return {"status": "unknown" if reserved else "rejected",
                    "reason": str(error), "writer": scope.writer, "request_id": request_id}

    def remember(self, scope: MemoryScope, *, category: str, content: str, title: str, project: str,
                 request_id: str, source: dict[str, str] | None = None) -> dict[str, Any]:
        source = source or {"kind": "explicit", "session": ""}
        if category not in CATEGORIES or category not in scope.write or not isinstance(content, str) or not content.strip():
            return {"status": "rejected", "reason": "The fact or write permission is invalid"}
        if category == "project" and (not project or ("*" not in scope.projects and project not in scope.projects)):
            return {"status": "rejected", "reason": "The project has no write grant"}
        content = content.strip()
        if category != "project" and not re.match(r"^(NAME|ROLE|RELATION|PREFERENCE|RULE): ", content):
            content = ("PREFERENCE: " if category == "principal" else "RULE: ") + content
        item = ({"type": "knowledge", "entity_type": "research", "name": title, "content": content,
                 "source_session": source.get("session", "") or "none"} if category == "project" else
                {"type": "memory", "actor": "principal" if category == "principal" else "assistant", "content": content})

        def save(connection):
            checked = self._native("validate", item=item)
            if not checked.get("ok"):
                return {"status": "rejected", "reason": checked.get("message", "Native validation rejected the fact")}
            if checked["item"].get("content") != content:
                return {"status": "rejected", "reason": "Native validation changed the requested content"}
            if category != "project" and len(content.split(": ", 1)[-1]) > 256:
                return {"status": "rejected", "reason": "The native hot-memory entry exceeds its 256-character limit"}
            blocked = connection.execute("SELECT id FROM records WHERE digest=? AND status IN ('forgotten','superseded')",
                                         (_digest(content),)).fetchone()
            if blocked:
                return {"status": "rejected", "reason": "This fact needs explicit reactivation after correction or forgetting"}
            existing = connection.execute("SELECT * FROM records WHERE digest=? AND category=? AND project=? AND status='active'",
                                          (_digest(content), category, project)).fetchone()
            if existing:
                return {"status": "unchanged", "reference": {"id": existing["id"], "revision": existing["revision"]}, "source": source}
            result = self._native("add", item=item)
            if not result.get("ok"):
                return {"status": "rejected", "reason": result.get("message", "Native memory rejected the fact")}
            reference = self._record(connection, scope, Path(result["path"]), content, category, project, source)
            return {"status": "committed", "reference": reference, "source": source}

        return self._operation(scope, request_id, {"operation": "remember", "item": item, "project": project, "source": source}, save)

    def recall(self, scope: MemoryScope, query: str, *, limit: int = 20) -> list[dict[str, Any]]:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("A memory query is required")
        terms = re.findall(r"\w+", query.casefold())
        results = []
        with self._transaction() as connection:
            for row in connection.execute("SELECT * FROM records WHERE status='active' ORDER BY updated DESC"):
                if not self._allowed(scope, row):
                    continue
                content = self._content(row)
                score = sum(content.casefold().count(term) for term in terms)
                if score:
                    results.append({"reference": {"id": row["id"], "revision": row["revision"]},
                                    "content": content, "category": row["category"], "project": row["project"],
                                    "writer": row["writer"], "status": row["status"], "score": score})
        return sorted(results, key=lambda item: item["score"], reverse=True)[:max(1, min(limit, 100))]

    def _target(self, connection: sqlite3.Connection, scope: MemoryScope, reference: dict[str, Any]):
        if not isinstance(reference, dict) or not isinstance(reference.get("id"), str) or type(reference.get("revision")) is not int:
            return None
        row = connection.execute("SELECT * FROM records WHERE id=?", (reference["id"],)).fetchone()
        if row is None or not self._allowed(scope, row, write=True):
            return None
        return row

    def correct(self, scope: MemoryScope, reference: dict[str, Any], content: str, request_id: str) -> dict[str, Any]:
        def change(connection):
            row = self._target(connection, scope, reference)
            if row is None:
                return {"status": "rejected", "reason": "The memory reference is unavailable or has no write grant"}
            if row["status"] != "active" or row["revision"] != reference["revision"]:
                return {"status": "conflict", "reason": "The referenced revision is no longer current"}
            if not isinstance(content, str) or not content.strip():
                return {"status": "rejected", "reason": "A replacement fact is required"}
            old = self._content(row)
            replacement = content.strip()
            path = self._path(row["path"])
            if row["category"] == "project":
                item = {"type": "knowledge", "entity_type": "research", "name": path.stem,
                        "content": replacement, "source_session": row["source_session"] or "none"}
                # Native path slugs must remain unchanged for section references.
                result = self._native("add", item=item)
                if not result.get("ok"):
                    return {"status": "rejected", "reason": result.get("message", "Native correction rejected")}
                path = Path(result["path"])
            else:
                if not re.match(r"^(NAME|ROLE|RELATION|PREFERENCE|RULE): ", replacement):
                    replacement = old.split(": ", 1)[0] + ": " + replacement
                if len(replacement.split(": ", 1)[-1]) > 256:
                    return {"status": "rejected", "reason": "The replacement exceeds the native entry limit"}
                current = self._native("read_hot", path=str(path))
                entries = current.get("entries", [])
                if old not in entries:
                    return {"status": "conflict", "reason": "The native fact changed before correction"}
                result = self._native("set_hot", path=str(path), entries=[replacement if value == old else value for value in entries], writer=scope.writer)
                if not result.get("ok"):
                    return {"status": "rejected", "reason": result.get("message", "Native correction rejected")}
            new_reference = self._record(connection, scope, path, replacement, row["category"], row["project"],
                                         {"session": row["source_session"], "kind": "correction"})
            connection.execute("UPDATE records SET status='superseded',revision=revision+1,updated=? WHERE id=?", (_now(), row["id"]))
            return {"status": "committed", "reference": new_reference, "supersedes": reference}
        return self._operation(scope, request_id, {"operation": "correct", "reference": reference, "content": content}, change)

    def forget(self, scope: MemoryScope, reference: dict[str, Any], request_id: str) -> dict[str, Any]:
        def remove(connection):
            row = self._target(connection, scope, reference)
            if row is None:
                return {"status": "rejected", "reason": "The memory reference is unavailable or has no write grant"}
            if row["status"] != "active" or row["revision"] != reference["revision"]:
                return {"status": "conflict", "reason": "The referenced revision is no longer current"}
            if row["category"] != "project":
                content = self._content(row)
                path = self._path(row["path"])
                current = self._native("read_hot", path=str(path))
                if content not in current.get("entries", []):
                    return {"status": "conflict", "reason": "The native fact changed before forgetting"}
                result = self._native("set_hot", path=str(path), entries=[value for value in current["entries"] if value != content],
                                      writer=scope.writer, allowDrastic=True)
                if not result.get("ok"):
                    return {"status": "rejected", "reason": result.get("message", "Native forgetting rejected")}
            connection.execute("UPDATE records SET status='forgotten',revision=revision+1,updated=? WHERE id=?", (_now(), row["id"]))
            return {"status": "committed", "reference": {"id": row["id"], "revision": row["revision"] + 1},
                    "retained": ["native history", "audit evidence", "backups", "conversation history", "development logs"]}
        return self._operation(scope, request_id, {"operation": "forget", "reference": reference}, remove)
