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
from .memory_transaction import MemoryTransaction


SCHEMA_VERSION = 4
HOT_FILES = {
    "principal": "LIFEOS/USER/PRINCIPAL/PRINCIPAL_MEMORY.md",
    "assistant": "LIFEOS/USER/DIGITAL_ASSISTANT/DA_MEMORY.md",
}
HOT_WRITE_LOG = 'LIFEOS/MEMORY/OBSERVABILITY/memory-writes.jsonl'


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _claim_words(text: str) -> list[str]:
    body = re.sub(r"^(NAME|ROLE|RELATION|PREFERENCE|RULE):\s*", "", text)
    body = re.sub(r"\s+~(?:explicit|deduced|inferred)\s*$", "", body)
    return re.findall(r"\w+", body.casefold())


def _claim_digest(text: str) -> str:
    return _digest(" ".join(_claim_words(text)))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MemoryUnavailable(RuntimeError):
    pass


class MemoryConflict(MemoryUnavailable):
    pass


class NativeMemory:
    def __init__(self, installed_root: Path, *, bun: str | None = None, profile: Path | None = None):
        self.root = Path(installed_root).absolute()
        self.physical_root = self.root.resolve()
        self.profile = Path(profile or self.root.parent / ".hermes").absolute()
        self.physical_profile = self.profile.resolve()
        self.bun = bun or shutil.which("bun") or "bun"
        self.database = self.root / "LIFEOS/MEMORY/STATE/memory-access.sqlite"
        self.worker = Path(__file__).with_name("memory_native.ts")
        self.transaction = MemoryTransaction(self.database.parent, self._publication_path)

    def _boundary(self) -> None:
        if self.root.resolve() != self.physical_root:
            raise MemoryUnavailable("The installed root alias changed during the memory operation")
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
        try:
            connection.execute("PRAGMA busy_timeout=30000")
            connection.execute("BEGIN IMMEDIATE")
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 3, SCHEMA_VERSION):
                raise MemoryUnavailable("The memory metadata schema is unsupported")
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS records (
                    id TEXT PRIMARY KEY, path TEXT NOT NULL, category TEXT NOT NULL, project TEXT NOT NULL,
                    digest TEXT NOT NULL, chars INTEGER NOT NULL, position INTEGER NOT NULL,
                    revision INTEGER NOT NULL, status TEXT NOT NULL, writer TEXT NOT NULL,
                    source_session TEXT NOT NULL, source_kind TEXT NOT NULL, updated TEXT NOT NULL,
                    claim_digest TEXT NOT NULL, claim_words INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS proposals (
                    id TEXT PRIMARY KEY, path TEXT NOT NULL, target TEXT NOT NULL, target_digest TEXT NOT NULL, digest TEXT NOT NULL,
                    revision INTEGER NOT NULL, status TEXT NOT NULL, writer TEXT NOT NULL,
                    source_session TEXT NOT NULL, updated TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS operations (
                    writer TEXT NOT NULL, request_id TEXT NOT NULL, payload_digest TEXT NOT NULL,
                    receipt TEXT NOT NULL, PRIMARY KEY(writer, request_id)
                );
                CREATE TABLE IF NOT EXISTS source_reviews (
                    principal TEXT NOT NULL, path TEXT NOT NULL, digest TEXT NOT NULL,
                    retirement_digest TEXT NOT NULL, writer TEXT NOT NULL, reviewed_at TEXT NOT NULL,
                    PRIMARY KEY(principal, path)
                );
            """)
            if version != SCHEMA_VERSION:
                connection.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
            connection.commit()
            os.chmod(self.database, 0o600)
            return connection
        except BaseException:
            connection.close()
            raise

    @contextmanager
    def _transaction(self):
        self._boundary()
        with self.transaction.lock():
            connection = self._connect()
            try:
                self.transaction.recover(connection)
                connection.execute("BEGIN IMMEDIATE")
                yield connection
                connection.commit()
                self.transaction.finish()
            except BaseException:
                connection.rollback()
                raise
            finally:
                connection.close()

    def _native(self, action: str, *, source_descriptors: tuple[int, ...] = (), **values: Any) -> dict[str, Any]:
        if (len(source_descriptors) > 1 or any(type(value) is not int or value < 3 for value in source_descriptors)):
            raise MemoryUnavailable('Native snapshots require a declared source descriptor')
        environment = dict(os.environ)
        environment["HOME"] = str(self.root.parent)
        environment["LIFEOS_DIR"] = str(self.root / "LIFEOS")
        environment["LIFEOS_CONFIG_DIR"] = str(self.root / "LIFEOS/USER/CONFIG")
        environment.pop("LIFEOS_MEMORY_PUBLICATION_JOURNAL", None)
        if self.transaction.inherited_descriptors():
            environment["LIFEOS_MEMORY_PUBLICATION_JOURNAL"] = str(self.transaction.journal)
        environment["LIFEOS_MEMORY_INTERNAL"] = "1"
        environment["BUN_CONFIG_NO_AUTO_INSTALL"] = "1"
        result = subprocess.run([self.bun, "--no-install", str(self.worker), str(self.root)],
                                input=json.dumps({"action": action, **values}), text=True,
                                capture_output=True, timeout=30, env=environment, cwd=self.root,
                                pass_fds=(*self.transaction.inherited_descriptors(), *source_descriptors))
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
        if path.exists() and self.database.exists() and path.samefile(self.database):
            raise MemoryUnavailable("Native memory content cannot alias its SQLite registry")
        return path

    def _publication_path(self, name: str) -> Path:
        if name.startswith(("LIFEOS/USER/", "LIFEOS/MEMORY/")):
            return self._path(name)
        from .memory_freshness import SYSTEM_PUBLICATIONS
        from .memory_freshness_migration import is_system_backup
        from .memory_deny_hashes import SYSTEM_PUBLICATIONS as DENY_PUBLICATIONS
        from .memory_user_index_publish import PUBLICATIONS as INDEX_PUBLICATIONS
        from .memory_manual_state import SYSTEM_PUBLICATIONS as MANUAL_PUBLICATIONS
        if name not in SYSTEM_PUBLICATIONS | DENY_PUBLICATIONS | INDEX_PUBLICATIONS | MANUAL_PUBLICATIONS and not is_system_backup(name):
            raise MemoryUnavailable("This is not a journaled native system publication")
        path = self.root / name
        if (path.resolve() != self.physical_root / name or path.is_symlink()
                or path.exists() and (not path.is_file() or path.stat().st_uid != os.getuid()
                                      or self.database.exists() and path.samefile(self.database))):
            raise MemoryUnavailable("The system publication changes its permitted owner path")
        return path

    @staticmethod
    def _allowed(scope: MemoryScope, record: sqlite3.Row, *, write: bool = False) -> bool:
        permissions = scope.write if write else scope.read
        if record["category"] not in permissions:
            return False
        if NativeMemory._private_entity(record["path"]) and "principal" not in permissions:
            return False
        if record['category'] == 'project' and not record['project'] and not CATEGORIES <= set(permissions):
            return False
        return record["category"] != "project" or "*" in scope.projects or record["project"] in scope.projects

    def _content(self, record: sqlite3.Row, hot_entries: dict[Path, list[str]] | None = None) -> str:
        path = self._path(record["path"])
        if not path.is_file():
            raise MemoryUnavailable("The referenced native memory file is missing")
        text = path.read_text(encoding="utf-8")
        length = record["chars"]
        position = record["position"]
        candidate = text[position:position + length]
        if record["category"] == "project":
            boundary = re.search(r"\n## Appended \d{4}-\d{2}-\d{2}T[^\n]+Z\n<!-- source_session: [^\n]* -->\n", text[position:])
            end = position + boundary.start() if boundary else len(text)
            section = text[position:end].rstrip("\r\n")
            if section == candidate and _digest(candidate) == record["digest"]:
                return candidate
        if record["category"] != "project":
            if hot_entries is None:
                entries = self._native("read_hot", path=str(path)).get("entries", [])
            else:
                if path not in hot_entries:
                    hot_entries[path] = self._native("read_hot", path=str(path)).get("entries", [])
                entries = hot_entries[path]
            matches = [entry for entry in entries if _digest(entry) == record["digest"]]
            if len(matches) == 1:
                return matches[0]
        raise MemoryConflict("The referenced fact changed outside its recorded revision")

    def _validate(self, item: dict[str, Any], content: str, category: str) -> str | None:
        checked = self._native("validate", item=item)
        if not checked.get("ok"):
            return checked.get("message", "Native validation rejected the fact")
        if checked["item"] != item:
            return "Native validation changed the requested fact or metadata"
        if category != "project" and (len(content.split(": ", 1)[-1].encode("utf-16-le")) // 2 > 256 or "\n" in content or "\r" in content):
            return "A native hot-memory entry requires one line of at most 256 characters"
        return None

    @staticmethod
    def _blocked(connection: sqlite3.Connection, content: str) -> bool:
        return connection.execute("""SELECT id FROM records AS retained WHERE claim_digest=? AND status IN ('forgotten','superseded')
                                  AND NOT EXISTS (SELECT 1 FROM records AS current WHERE current.status='active'
                                  AND current.claim_digest=retained.claim_digest AND current.category=retained.category
                                  AND current.project=retained.project)""",
                                  (_claim_digest(content),)).fetchone() is not None

    def _archive_write(self, connection: sqlite3.Connection, item: dict[str, Any], *, check_current=None) -> dict[str, Any]:
        path = Path(self._native("route", item=item)["path"])
        relative = path.relative_to(self.root).as_posix()
        path = self._path(relative)
        rows = connection.execute("SELECT * FROM records WHERE path=? AND status='active'", (relative,)).fetchall()
        old_text = path.read_text(encoding="utf-8") if path.exists() else ""
        for row in rows:
            self._content(row)
        if check_current is not None:
            check_current(connection)
        result = self._native("add", item=item)
        if not result.get("ok"):
            return result
        if Path(result["path"]) != path:
            raise MemoryUnavailable("Native publication changed its declared archive destination")
        if rows:
            text = path.read_text(encoding="utf-8")
            old_frontmatter = re.match(r"^---\n.*?\n---\n", old_text, re.DOTALL)
            frontmatter = re.match(r"^---\n.*?\n---\n", text, re.DOTALL)
            if old_frontmatter is None or frontmatter is None or not text[frontmatter.end():].startswith(old_text[old_frontmatter.end():].rstrip("\r\n")):
                raise MemoryUnavailable("Native archive publication changed an earlier section; recovery is required")
            delta = frontmatter.end() - old_frontmatter.end()
            for row in rows:
                connection.execute("UPDATE records SET position=position+? WHERE id=?", (delta, row["id"]))
                updated = connection.execute("SELECT * FROM records WHERE id=?", (row["id"],)).fetchone()
                self._content(updated)
        return result

    @staticmethod
    def _archive_item(path: Path, content: str, source_session: str) -> dict[str, Any]:
        common = {"content": content, "source_session": source_session or "none"}
        if 'LEARNING' in path.parts:
            return {**common, 'type':'knowledge', 'entity_type':'research', 'name':path.stem}
        if path.parent.name == "Ideas":
            return {**common, "type": "idea", "title": path.stem}
        entity = {"People": "person", "Companies": "company", "Research": "research"}.get(path.parent.name)
        if entity is None:
            raise MemoryUnavailable("The archive reference has no supported native routing type")
        return {**common, "type": "knowledge", "entity_type": entity, "name": path.stem}

    @staticmethod
    def _private_entity(path: str) -> bool:
        return path.startswith(("LIFEOS/MEMORY/KNOWLEDGE/People/", "LIFEOS/MEMORY/KNOWLEDGE/Companies/",
                                "LIFEOS/MEMORY/KNOWLEDGE/_archive/People/", "LIFEOS/MEMORY/KNOWLEDGE/_archive/Companies/"))

    def _duplicate(self, connection: sqlite3.Connection, scope: MemoryScope, content: str,
                   category: str, project: str, destination: str) -> sqlite3.Row | None:
        candidates = connection.execute("SELECT * FROM records WHERE digest=? AND category=? AND project=? AND status='active'",
                                        (_digest(content), category, project)).fetchall()
        for candidate in candidates:
            if self._allowed(scope, candidate, write=True) and self._private_entity(candidate["path"]) == self._private_entity(destination):
                self._content(candidate)
                return candidate
        return None

    def _record(self, connection: sqlite3.Connection, scope: MemoryScope, path: Path,
                content: str, category: str, project: str, source: dict[str, str]) -> dict[str, Any]:
        relative = path.relative_to(self.root).as_posix()
        text = self._path(relative).read_text(encoding="utf-8")
        if category == "project":
            position = len(text.rstrip("\r\n")) - len(content)
        else:
            start = text.index("<!-- BEGIN ENTRIES -->") + len("<!-- BEGIN ENTRIES -->")
            position = text.find(content, start, text.index("<!-- END ENTRIES -->"))
        if position < 0 or text[position:position + len(content)] != content:
            raise MemoryUnavailable("The native writer did not save the requested fact")
        identifier = uuid4().hex
        connection.execute("INSERT INTO records VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            identifier, relative, category, project, _digest(content), len(content), position,
            1, "active", scope.writer, source.get("session", ""), source.get("kind", "explicit"), _now(), _claim_digest(content), len(_claim_words(content)),
        ))
        return {"id": identifier, "revision": 1}

    def _operation(self, scope: MemoryScope, request_id: str, payload: dict[str, Any],
                   callback: Callable[[sqlite3.Connection], dict[str, Any]], *,
                   identity_payload: dict[str, Any] | None = None, publication_digests=None) -> dict[str, Any]:
        if not isinstance(request_id, str) or not request_id or len(request_id) > 256:
            return {"status": "rejected", "reason": "A bounded request identifier is required"}
        payload_digest = _digest(json.dumps(payload if identity_payload is None else identity_payload, sort_keys=True))
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
                paths = self._publication_paths(connection, scope, payload)
                self.transaction.prepare(scope.writer, request_id, paths, expected=publication_digests)
                connection.execute("INSERT INTO operations VALUES (?,?,?,?)",
                                   (scope.writer, request_id, payload_digest, json.dumps(unknown)))
                connection.commit()
                reserved = True
                connection.execute("BEGIN IMMEDIATE")
                try:
                    receipt = callback(connection)
                except MemoryConflict as error:
                    receipt = {"status": "conflict", "reason": str(error)}
                receipt.setdefault("writer", scope.writer)
                receipt.setdefault("request_id", request_id)
                connection.execute("UPDATE operations SET receipt=? WHERE writer=? AND request_id=?",
                                   (json.dumps(receipt), scope.writer, request_id))
                self.transaction.flush_publication()
                return receipt
        except MemoryConflict as error:
            return {"status": "conflict", "reason": str(error), "writer": scope.writer, "request_id": request_id}
        except (MemoryUnavailable, OSError, sqlite3.Error, subprocess.TimeoutExpired) as error:
            return {"status": "unknown" if reserved else "rejected",
                    "reason": str(error), "writer": scope.writer, "request_id": request_id}

    def _publication_paths(self, connection: sqlite3.Connection, scope: MemoryScope,
                           payload: dict[str, Any]) -> list[str]:
        if payload['operation'] == 'local_run':
            from .memory_local_runs import publication_paths
            return publication_paths(self, scope, payload)
        if payload['operation'] == 'local_refresh':
            from .memory_local_refresh import publication_paths
            return publication_paths(self, scope, payload)
        if payload['operation'] == 'atlas_insight':
            from .memory_atlas_insight import publication_paths
            return publication_paths(self, scope, payload)
        if payload['operation'] == 'conduit_insight':
            from .memory_conduit_insight import publication_paths
            return publication_paths(self, scope, payload)
        if payload['operation'] == 'conduit_initialize':
            from .memory_conduit import publication_paths
            return publication_paths(self, scope, payload)
        if payload['operation'] == 'manual_state':
            from .memory_manual_state import publication_paths
            return publication_paths(self, scope, payload['tool'], paths=payload['paths'])
        if payload['operation'] == 'telos_file_edit':
            from .memory_telos_file import publication_paths
            return publication_paths(self, scope, payload)
        if payload['operation'] == 'user_index_publish':
            from .memory_user_index_publish import publication_paths
            return publication_paths(self, connection, scope, payload)
        if payload['operation'] == 'upgrade_store':
            from .memory_upgrades import publication_paths
            return publication_paths(self,scope,payload)
        if payload['operation'] == 'hypothesis_review':
            from .memory_hypothesis_review import publication_paths
            return publication_paths(self, scope, payload)
        if payload['operation'] == 'event_append':
            from .memory_events import publication_paths
            return publication_paths(self, scope, payload)
        if payload['operation'] == 'knowledge_conformance':
            from .memory_knowledge_conformance import publication_paths
            return publication_paths(self, scope, payload)
        if payload['operation'] == 'knowledge_view':
            from .memory_knowledge_views import publication_paths
            return publication_paths(self, scope, payload)
        if payload['operation'] == 'knowledge_harvest':
            from .memory_knowledge_harvest import publication_paths
            return publication_paths(self, scope, payload)
        if payload['operation'] == 'session_harvest':
            from .memory_session_harvest import publication_paths
            return publication_paths(self, scope, payload)
        if payload['operation'] == 'proposal_gc':
            from .memory_proposal_gc import publication_paths
            return publication_paths(self, scope, payload)
        if payload['operation'] == 'context_audit':
            from .memory_context_audit import publication_paths
            return publication_paths(self, scope)
        if payload['operation'] == 'seed_pulse':
            from .memory_seed import publication_paths
            return publication_paths(self, scope, payload)
        if payload['operation'] == 'learning_hypotheses':
            from .memory_hypotheses import publication_paths
            return publication_paths(self, scope, payload)
        if payload['operation'] == 'recurrence_append':
            from .memory_recurrence import publication_paths
            return publication_paths(self, scope)
        if payload['operation'] == 'learning_ratings':
            from .memory_learning import publication_paths
            return publication_paths(self, scope, payload)
        if payload['operation'] in {'wisdom_frame_update', 'wisdom_synthesis'}:
            from .memory_wisdom import publication_paths
            return publication_paths(self, scope, payload)
        if payload['operation'] == 'distill_synthesis':
            from .memory_distill import synthesis_paths
            return synthesis_paths(self, scope, payload['date'])
        if payload['operation'] == 'distill_mark':
            from .memory_distill import publication_paths
            return publication_paths(self, scope)
        if payload['operation'] == 'pulse_data':
            from .memory_pulse_adapters import publication_paths
            return publication_paths(self, scope, payload)
        if payload['operation'] == 'derived_sync':
            from .memory_derived_sync import publication_paths
            return publication_paths(self, scope)
        if payload['operation'] == 'deny_hashes':
            from .memory_deny_hashes import publication_paths
            return publication_paths(self, scope)
        if payload['operation'] in {'interview_due_cache_write', 'interview_due_mark'}:
            from .memory_interview import publication_paths
            return publication_paths(self, scope, payload)
        if payload['operation'] == 'state_evidence_cache':
            from .memory_evidence import publication_paths
            return publication_paths(self, scope)
        if payload['operation'] == 'freshness_migration':
            from .memory_freshness_migration import publication_paths
            return publication_paths(self, connection, scope, payload)
        if payload['operation'] == 'freshness_cache':
            from .memory_freshness_cache import publication_paths
            return publication_paths(self, scope)
        if payload['operation'] == 'freshness_write':
            from .memory_freshness import publication_paths
            return publication_paths(self, connection, scope, payload)
        if payload['operation'] == 'telos_summary':
            from .memory_telos import publication_paths
            return publication_paths(self, scope)
        if payload['operation'] == 'lifeos_state':
            from .memory_state import publication_paths
            return publication_paths(self, scope)
        if payload['operation'] == 'memory_graph':
            from .memory_graph import publication_paths
            return publication_paths(self, scope)
        if payload['operation'] == 'restore':
            from .memory_restore import publication_paths
            return publication_paths(self,connection,scope,payload)
        if payload['operation'] == 'staged_promote':
            from .memory_staging import publication_paths
            return publication_paths(self,connection,scope,payload)
        if payload['operation'] == 'staged_reject':
            from .memory_staging import rejection_paths
            return rejection_paths(self,scope,payload)
        if payload["operation"] == "proposal_decision":
            from .memory_proposals import _permitted
            permission = 'auto_apply' if payload['decision'] == 'auto_apply' else 'approve'
            if not _permitted(scope, permission):
                return []
            row = connection.execute("SELECT * FROM proposals WHERE id=?", (payload['reference']['id'],)).fetchone()
            if row is None or row['status'] != 'pending' or row['revision'] != payload['reference']['revision']:
                return []
            return [row['path'], row['target'], "LIFEOS/MEMORY/OBSERVABILITY/identity-proposals.jsonl"]
        if payload["operation"] == "native_proposal":
            return ["LIFEOS/MEMORY/OBSERVABILITY/pending-proposals.jsonl"]
        if payload["operation"] == "native_set":
            return self._hot_publication_paths(payload['category'])
        if payload["operation"] in ("remember", "native_add"):
            checked = self._native("validate", item=payload["item"])
            if not checked.get("ok") or checked["item"] != payload["item"]:
                return []
            result = self._native("route", item=checked["item"])
            relative = Path(result["path"]).relative_to(self.root).as_posix()
            category = next((category for category, path in HOT_FILES.items() if path == relative), None)
            return self._hot_publication_paths(category) if category else [relative]
        reference = payload.get("reference")
        if not isinstance(reference, dict) or not isinstance(reference.get("id"), str):
            return []
        row = self._target(connection, scope, reference)
        if row is None or row['status'] != 'active' or row['revision'] != reference['revision']:
            return []
        if row['category'] in HOT_FILES:
            if row['category'] not in scope.read:
                return []
            # Refuse drift before the recovery journal copies the whole source file.
            self._hot_snapshot(connection, row['category'])
        paths = self._hot_publication_paths(row['category']) if row['category'] in HOT_FILES else [row['path']]
        if payload['operation'] == 'correct' and row['category'] == 'project' and isinstance(payload['content'],str):
            item = self._archive_item(self._path(row['path']),payload['content'],row['source_session'])
            checked = self._native('validate',item=item)
            if checked.get('ok') and checked.get('item') == item:
                target = Path(self._native('route',item=item)['path']).relative_to(self.root).as_posix()
                self._path(target)
                paths.append(target)
        return paths

    def _hot_publication_paths(self, category: str) -> list[str]:
        log = self._path(HOT_WRITE_LOG)
        expected = self.root.parent / '.config/LIFEOS/USER/MEMORY/OBSERVABILITY/memory-writes.jsonl'
        if log.resolve() != expected.absolute() or (log.exists() and not log.is_file()):
            raise MemoryUnavailable('The native hot-write log changes its permitted physical path')
        # Native append evidence must recover with the fact publication it describes.
        return [HOT_FILES[category], HOT_WRITE_LOG]

    @staticmethod
    def _native_receipt(receipt: dict[str, Any], *, category: str, path: Path) -> dict[str, Any]:
        if receipt["status"] not in ("committed", "unchanged"):
            return {"ok": False, "code": "EINVAL_ITEM", "message": receipt.get("reason", "Memory operation did not commit"),
                    "receipt": receipt}
        return {"ok": True, "type": "memory" if category != "project" else "knowledge", "path": str(path),
                "detail": receipt.get("detail", {}), "receipt": receipt}

    def _hot_snapshot(self, connection: sqlite3.Connection, category: str) -> dict[str, Any]:
        path = self._path(HOT_FILES[category])
        snapshot = self._native("read_hot", path=str(path))
        if "entries" not in snapshot or snapshot.get("dropped_invalid"):
            raise MemoryUnavailable("Native hot memory needs repair before governed curation")
        indexed = connection.execute("SELECT * FROM records WHERE category=? AND status='active'", (category,)).fetchall()
        entries = snapshot["entries"]
        if sorted(_digest(entry) for entry in entries) != sorted(row["digest"] for row in indexed):
            raise MemoryConflict("Native hot memory changed outside governed publication; review it before adoption")
        return {**snapshot, "revision": _digest(path.read_text(encoding="utf-8"))}

    def read_hot(self, scope: MemoryScope, category: str) -> dict[str, Any]:
        if category not in HOT_FILES or category not in scope.read:
            return {"ok": False, "code": "EINVAL_PATH", "message": "This hot-memory file has no read grant"}
        with self._transaction() as connection:
            return self._hot_snapshot(connection, category)

    def _curate_hot(self, connection: sqlite3.Connection, scope: MemoryScope, category: str,
                    entries: list[str], observed_revision: str, *, allow_drastic: bool = False,
                    source: dict[str, str] | None = None, native_writer: str | None = None,
                    check_current=None) -> dict[str, Any]:
        current = self._hot_snapshot(connection, category)
        if not observed_revision or observed_revision != current["revision"]:
            return {"status": "conflict", "reason": "The native memory revision changed after the reviewer read it"}
        desired = list(dict.fromkeys(entries))
        prior = connection.execute("SELECT * FROM records WHERE category=? AND status='active'", (category,)).fetchall()
        by_digest = {row["digest"]: row for row in prior}
        by_claim: dict[str, list[sqlite3.Row]] = {}
        for row in prior:
            by_claim.setdefault(row["claim_digest"], []).append(row)
        assignments = []
        preserved = set()
        desired_digests = {_digest(entry) for entry in desired}
        for entry in desired:
            item = {"type": "memory", "actor": category, "content": entry}
            if not re.match(r"^(NAME|ROLE|RELATION|PREFERENCE|RULE): ", entry):
                return {"status": "rejected", "reason": "Every native hot entry requires a recognized prefix"}
            invalid = self._validate(item, entry, category)
            if invalid:
                return {"status": "rejected", "reason": invalid}
            if entry not in current["entries"] and self._blocked(connection, entry):
                return {"status": "rejected", "reason": "This fact needs explicit reactivation after correction or forgetting"}
            row = by_digest.get(_digest(entry))
            equivalent = by_claim.get(_claim_digest(entry), [])
            if row is None and len(equivalent) == 1 and equivalent[0]["digest"] not in desired_digests:
                row = equivalent[0]
            if row is not None:
                if row["id"] in preserved:
                    return {"status": "conflict", "reason": "Curation maps several replacements to one native fact"}
                preserved.add(row["id"])
            assignments.append(row)
        path = self._path(HOT_FILES[category])
        if check_current is not None:
            check_current(connection)
        # Native summaries recognize the addition label; registry authorship stays in scope.writer.
        result = self._native("set_hot", path=str(path), entries=desired,
                              writer=native_writer or scope.writer, allowDrastic=allow_drastic)
        if not result.get("ok"):
            return {"status": "rejected", "reason": result.get("message", "Native curation rejected the update")}
        if result.get("dropped_malformed") or result.get("dropped_overlength"):
            raise MemoryUnavailable("Native curation dropped submitted facts; publication requires recovery")
        actual = self._native("read_hot", path=str(path)).get("entries")
        if actual != desired:
            raise MemoryUnavailable("Native curation did not publish the complete requested snapshot")
        references = []
        for row in prior:
            if row["id"] not in preserved:
                connection.execute("UPDATE records SET status='superseded',revision=revision+1,updated=? WHERE id=?", (_now(), row["id"]))
        for entry, row in zip(desired, assignments):
            if row is None:
                references.append(self._record(connection, scope, path, entry, category, "",
                                               source if source is not None else {"kind": "native-curation"}))
            elif row["digest"] == _digest(entry):
                references.append({"id": row["id"], "revision": row["revision"]})
            else:
                text = path.read_text(encoding="utf-8")
                start = text.index("<!-- BEGIN ENTRIES -->") + len("<!-- BEGIN ENTRIES -->")
                position = text.find(entry, start, text.index("<!-- END ENTRIES -->"))
                if position < 0:
                    raise MemoryUnavailable("Native curation did not save the replacement fact")
                connection.execute("UPDATE records SET digest=?,chars=?,position=?,revision=revision+1,updated=? WHERE id=?",
                                   (_digest(entry), len(entry), position, _now(), row["id"]))
                references.append({"id": row["id"], "revision": row["revision"] + 1})
        return {"status": "committed", "references": references, "detail": result}

    def native_set(self, scope: MemoryScope, category: str, entries: list[str], request_id: str,
                   observed_revision: str, *, allow_drastic: bool = False, source_session: str = '',
                   check_current=None) -> dict[str, Any]:
        if category not in HOT_FILES or category not in scope.read or category not in scope.write:
            return {"ok": False, "code": "EINVAL_PATH", "message": "Native curation needs read and write grants for the whole file"}
        if not isinstance(entries, list) or any(not isinstance(entry, str) for entry in entries) or type(allow_drastic) is not bool:
            return {"ok": False, "code": "EINVAL_ITEM", "message": "Native curation requires a validated entry list"}
        payload = {"operation": "native_set", "category": category, "entries": entries,
                   "observed_revision": observed_revision, "allow_drastic": allow_drastic, 'source_session': source_session}
        receipt = self._operation(scope, request_id, payload, lambda connection:
                                  self._curate_hot(connection, scope, category, entries, observed_revision, allow_drastic=allow_drastic,
                                                   source={'kind': 'native-curation', 'session': source_session},
                                                   check_current=check_current))
        result = self._native_receipt(receipt, category=category, path=self._path(HOT_FILES[category]))
        return {**receipt["detail"], "receipt": receipt} if result["ok"] else {**result, "code": "EWRITE_FAILED"}

    def review_proposals(self, scope: MemoryScope, *, include_resolved: bool = False) -> list[dict[str, Any]]:
        from .memory_proposals import review
        return review(self, scope, include_resolved=include_resolved)

    def decide_proposal(self, scope: MemoryScope, reference: dict[str, Any], decision: str,
                        request_id: str, *, content: str = "", note: str = "",
                        confidence_threshold: float | None = None, check_current=None) -> dict[str, Any]:
        from .memory_proposals import decide
        return decide(self, scope, reference, decision, request_id, content=content, note=note,
                      confidence_threshold=confidence_threshold, check_current=check_current)

    def proposal_decision_row(self, scope: MemoryScope, reference: dict[str, Any]) -> dict[str, Any]:
        from .memory_proposals import decision_row
        return decision_row(self, scope, reference)

    def preview_adoption(self, scope: MemoryScope) -> dict[str, Any]:
        from .memory_adoption import preview
        return preview(self, scope)

    def adopt(self, scope: MemoryScope, signature: str, projects: dict[str, str], request_id: str) -> dict[str, Any]:
        from .memory_adoption import adopt
        return adopt(self, scope, signature, projects, request_id)

    def native_add(self, scope: MemoryScope, item: dict[str, Any], *, request_id: str, project: str,
                   observed_revision: str = "", source_session: str = "", check_current=None) -> dict[str, Any]:
        if not isinstance(item, dict):
            return {"ok": False, "code": "EINVAL_ITEM", "message": "A native memory item is required"}
        if item.get("type") == "proposal":
            from .memory_proposals import enqueue
            return enqueue(self, scope, item, request_id, source_session, check_current=check_current)
        category = item.get("actor") if item.get("type") == "memory" else "project"
        if not isinstance(category, str) or item.get("type") not in ("memory", "knowledge", "idea") or category not in CATEGORIES:
            return {"ok": False, "code": "EINVAL_ITEM", "message": "This native memory item needs a supported governed operation"}
        if category not in scope.write or (category == "project" and (not project or ("*" not in scope.projects and project not in scope.projects))):
            return {"ok": False, "code": "EINVAL_ITEM", "message": "This native memory item has no write grant"}
        if category != "project" and category not in scope.read:
            return {"ok": False, "code": "EINVAL_ITEM", "message": "Native curation requires a read grant for the current hot file"}
        if item.get("type") == "knowledge" and item.get("entity_type") in ("person", "company") and "principal" not in scope.write:
            return {"ok": False, "code": "EINVAL_ITEM", "message": "Native private entity notes need principal write permission"}
        checked = self._native("validate", item=item)
        if not checked.get("ok") or checked["item"] != item:
            return {"ok": False, "code": "EINVAL_ITEM", "message": checked.get("message", "Native validation changed the requested item")}
        if category != "project" and item.get("op") == "set":
            result = self.native_set(scope, category, item.get("entries"), request_id, observed_revision,
                                     source_session=source_session, check_current=check_current)
            if not result.get("ok"):
                return result
            return {"ok": True, "type": "memory", "path": str(self._path(HOT_FILES[category])), "detail": result, "receipt": result["receipt"]}
        project = project if category == "project" else ""
        content = item.get("content")
        if not isinstance(content, str) or not content.strip():
            return {"ok": False, "code": "EINVAL_ITEM", "message": "A native fact requires content"}
        def save(connection):
            invalid = self._validate(item, content, category)
            if invalid:
                return {"status": "rejected", "reason": invalid}
            if category != "project":
                snapshot = self._hot_snapshot(connection, category)
                return self._curate_hot(connection, scope, category, [*snapshot["entries"], content], snapshot["revision"],
                                        native_writer='MemorySystem.add', source={'kind': 'native', 'session': source_session},
                                        check_current=check_current)
            if self._blocked(connection, content):
                return {"status": "rejected", "reason": "This fact needs explicit reactivation after correction or forgetting"}
            result = self._archive_write(connection, item, check_current=check_current)
            if not result.get("ok"):
                return {"status": "rejected", "reason": result.get("message", "Native memory rejected the fact")}
            reference = self._record(connection, scope, Path(result["path"]), content, category, project,
                                     {"kind": "native", "session": source_session})
            return {"status": "committed", "reference": reference, "detail": result["detail"]}
        receipt = self._operation(scope, request_id, {"operation": "native_add", "item": item, "project": project,
                                                    "source_session": source_session}, save)
        path = self._path(HOT_FILES[category]) if category in HOT_FILES else self.root / "LIFEOS/MEMORY"
        result = self._native_receipt(receipt, category=category, path=path)
        if result["ok"] and category == "project":
            result["type"] = item["type"]
            with self._transaction() as connection:
                row = connection.execute("SELECT path FROM records WHERE id=?", (receipt["reference"]["id"],)).fetchone()
                result["path"] = str(self._path(row["path"]))
        return result

    def remember(self, scope: MemoryScope, *, category: str, content: str, title: str, project: str,
                 request_id: str, source: dict[str, str] | None = None,
                 check_current=None, record_result=None) -> dict[str, Any]:
        if any(callback is not None and not callable(callback) for callback in (check_current, record_result)):
            raise ValueError('Memory publication requires callable review and receipt checks')
        source = source or {"kind": "explicit", "session": ""}
        if category not in CATEGORIES or category not in scope.write or not isinstance(content, str) or not content.strip():
            return {"status": "rejected", "reason": "The fact or write permission is invalid"}
        if category == "project" and (not project or ("*" not in scope.projects and project not in scope.projects)):
            return {"status": "rejected", "reason": "The project has no write grant"}
        if category in HOT_FILES and category not in scope.read:
            return {"status": "rejected", "reason": "Hot-memory publication requires a read grant for the current file"}
        if category != "project":
            project = ""
        content = content.strip()
        if category != "project" and not re.match(r"^(NAME|ROLE|RELATION|PREFERENCE|RULE): ", content):
            content = ("PREFERENCE: " if category == "principal" else "RULE: ") + content
        item = ({"type": "knowledge", "entity_type": "research", "name": title, "content": content,
                 "source_session": source.get("session", "") or "none"} if category == "project" else
                {"type": "memory", "actor": "principal" if category == "principal" else "assistant", "content": content})

        def save_fact(connection):
            invalid = self._validate(item, content, category)
            if invalid:
                return {"status": "rejected", "reason": invalid}
            snapshot = self._hot_snapshot(connection, category) if category in HOT_FILES else None
            if self._blocked(connection, content):
                return {"status": "rejected", "reason": "This fact needs explicit reactivation after correction or forgetting"}
            destination = Path(self._native("route", item=item)["path"]).relative_to(self.root).as_posix()
            existing = self._duplicate(connection, scope, content, category, project, destination)
            if existing:
                return {"status": "unchanged", "reference": {"id": existing["id"], "revision": existing["revision"]}, "source": source}
            if snapshot is not None:
                result = self._curate_hot(connection, scope, category, [*snapshot['entries'], content],
                                          snapshot['revision'], source=source, native_writer='MemorySystem.add',
                                          check_current=check_current)
                if result['status'] != 'committed':
                    return result
                return {'status': 'committed', 'reference': result['references'][-1], 'source': source}
            result = self._archive_write(connection, item, check_current=check_current)
            if not result.get("ok"):
                return {"status": "rejected", "reason": result.get("message", "Native memory rejected the fact")}
            reference = self._record(connection, scope, Path(result["path"]), content, category, project, source)
            return {"status": "committed", "reference": reference, "source": source}

        def save(connection):
            if check_current is not None:
                check_current(connection)
            receipt = save_fact(connection)
            if record_result is not None:
                receipt.setdefault('writer', scope.writer)
                receipt.setdefault('request_id', request_id)
                record_result(connection, receipt)
            return receipt

        return self._operation(scope, request_id, {"operation": "remember", "item": item, "project": project, "source": source}, save)

    def recall(self, scope: MemoryScope, query: str, *, limit: int = 20) -> list[dict[str, Any]]:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("A memory query is required")
        if type(limit) is not int:
            raise ValueError("The memory result limit must be an integer")
        with self._transaction() as connection:
            records, corpus = self._corpus(connection, scope)
            if not corpus:
                return []
            ranked = self._native("rank", query=query, corpus=corpus, limit=max(1, min(limit, 100)))
            return [{**records[item["path"]], "score": item["score"]} for item in ranked["results"]]

    def _corpus(self, connection: sqlite3.Connection, scope: MemoryScope) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        from .memory_sources import source_labels, source_projection
        records = {}
        corpus = []
        declared = []
        hot_entries = {}
        for row in connection.execute("SELECT * FROM records WHERE status='active' ORDER BY updated DESC"):
            if not self._allowed(scope, row):
                continue
            # Reuse native parsing inside this locked retrieval, keeping each reference's digest check.
            content = self._content(row, hot_entries)
            if row['category'] == 'project' and self._filter_history(connection, scope,
                    source_labels(row['path']), _now())['excluded']:
                continue
            records[row["id"]] = {"reference": {"id": row["id"], "revision": row["revision"]},
                                  "content": content, "category": row["category"], "project": row["project"],
                                  "writer": row["writer"], "status": 'historical' if row['source_kind']=='learning' else row["status"],
                                  "source":{'kind':row['source_kind'],'session':row['source_session'],'path':row['path']}}
            corpus.append({"filePath": row["id"], "frontmatter": {"type": ("idea" if "/KNOWLEDGE/Ideas/" in row["path"] else "knowledge") if row["category"] == "project" else "memory",
                                                                 "title": row["project"] or row["category"]},
                           "body": content, "wordCount": max(1, len(content.split())),
                           "noteClass": 'learning' if row['source_kind']=='learning' else "knowledge" if row["category"] == "project" else "memory"})
            declared.append(source_projection(self, row['path'], content))
        if declared:
            checked = self._native('validate_source_batch', contents=declared)['accepted']
            corpus = [item for item, accepted in zip(corpus, checked, strict=True) if accepted is True]
            records = {item['filePath']: records[item['filePath']] for item in corpus}
        return records, corpus

    def relevant_context(self, scope: MemoryScope, query: str, options: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(query, str) or len(query) > 4096 or not isinstance(options, dict):
            raise ValueError("Invalid native memory retrieval request")
        if set(options) - {"topK", "threshold", "excerptChars", "typeFilter"}:
            raise ValueError("Unsupported native memory retrieval options")
        for key, maximum in (("topK", 100), ("excerptChars", 65536)):
            if key in options and (type(options[key]) is not int or not 1 <= options[key] <= maximum):
                raise ValueError("Invalid native retrieval limit")
        if "threshold" in options and (type(options["threshold"]) not in (int, float) or not 0 <= options["threshold"] < float("inf")):
            raise ValueError("Invalid native retrieval threshold")
        if "typeFilter" in options and options["typeFilter"] not in ("memory", "idea", "knowledge", "unknown"):
            raise ValueError("Invalid native retrieval type")
        with self._transaction() as connection:
            _, corpus = self._corpus(connection, scope)
            return self._native("rank", query=query, corpus=corpus, options=options)

    def filter_history(self, scope: MemoryScope, content: str, timestamp: str) -> dict[str, Any]:
        if not isinstance(content, str) or len(content) > 65536 or not isinstance(timestamp, str):
            raise ValueError("Invalid reviewer history input")
        if not CATEGORIES <= set(scope.read) or "*" not in scope.projects:
            return {"content": "", "excluded": True}
        with self._transaction() as connection:
            return self._filter_history(connection,scope,content,timestamp)

    def _filter_history(self, connection: sqlite3.Connection, scope: MemoryScope, content: str, timestamp: str,
                        *, reviewed: bool = False) -> dict[str, Any]:
        retained = connection.execute("""SELECT * FROM records AS retained WHERE status IN ('forgotten','superseded')
                                      AND NOT EXISTS (SELECT 1 FROM records AS current WHERE current.status='active'
                                      AND current.claim_digest=retained.claim_digest AND current.category=retained.category
                                      AND current.project=retained.project)""").fetchall()
        retained = [row for row in retained if self._allowed(scope, row)]
        if not retained:
            return {"content": content, "excluded": False}
        try:
            source_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            if source_time.tzinfo is None:
                raise ValueError("Reviewer sources need an explicit timezone")
            if not reviewed and source_time <= max(datetime.fromisoformat(row["updated"]) for row in retained):
                return {"content": "", "excluded": True}
        except ValueError:
            return {"content": "", "excluded": True}
        words = _claim_words(content)
        hashes_by_length: dict[int, set[str]] = {}
        for row in retained:
            if row["claim_words"] > 0:
                hashes_by_length.setdefault(row["claim_words"], set()).add(row["claim_digest"])
        for length, hashes in hashes_by_length.items():
            for start in range(len(words) - length + 1):
                if _digest(" ".join(words[start:start + length])) in hashes:
                    return {"content": "", "excluded": True}
        return {"content": content, "excluded": False}

    def _target(self, connection: sqlite3.Connection, scope: MemoryScope, reference: dict[str, Any]):
        if not isinstance(reference, dict) or not isinstance(reference.get("id"), str) or type(reference.get("revision")) is not int:
            return None
        row = connection.execute("SELECT * FROM records WHERE id=?", (reference["id"],)).fetchone()
        if row is None or not self._allowed(scope, row, write=True):
            return None
        return row

    def get(self, scope: MemoryScope, reference: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(reference, dict) or not isinstance(reference.get("id"), str) or type(reference.get("revision")) is not int:
            return {"status": "rejected", "reason": "A current memory reference is required"}
        with self._transaction() as connection:
            row = connection.execute("SELECT * FROM records WHERE id=?", (reference["id"],)).fetchone()
            if row is None or not self._allowed(scope, row):
                return {"status": "rejected", "reason": "The memory reference is unavailable or has no read grant"}
            if row["status"] != "active" or row["revision"] != reference["revision"]:
                return {"status": "conflict", "reason": "The referenced revision is no longer current"}
            return {"status": "ok", "reference": reference, "content": self._content(row),
                    "category": row["category"], "project": row["project"], "writer": row["writer"],
                    "source": {"session": row["source_session"], "kind": row["source_kind"]}}

    def correct(self, scope: MemoryScope, reference: dict[str, Any], content: str, request_id: str,
                check_current=None) -> dict[str, Any]:
        def change(connection):
            if check_current is not None:
                check_current(connection)
            row = self._target(connection, scope, reference)
            if row is None:
                return {"status": "rejected", "reason": "The memory reference is unavailable or has no write grant"}
            if row["status"] != "active" or row["revision"] != reference["revision"]:
                return {"status": "conflict", "reason": "The referenced revision is no longer current"}
            if row['category'] in HOT_FILES and row['category'] not in scope.read:
                return {'status': 'rejected', 'reason': 'Hot-memory correction requires read and write grants'}
            if not isinstance(content, str) or not content.strip():
                return {"status": "rejected", "reason": "A replacement fact is required"}
            current = self._hot_snapshot(connection, row['category']) if row['category'] in HOT_FILES else None
            old = self._content(row)
            replacement = content.strip()
            path = self._path(row["path"])
            if row["category"] == "project":
                item = self._archive_item(path, replacement, row["source_session"])
            else:
                if not re.match(r"^(NAME|ROLE|RELATION|PREFERENCE|RULE): ", replacement):
                    replacement = old.split(": ", 1)[0] + ": " + replacement
                item = {"type": "memory", "actor": "principal" if row["category"] == "principal" else "assistant",
                        "content": replacement}
            invalid = self._validate(item, replacement, row["category"])
            if invalid:
                return {"status": "rejected", "reason": invalid}
            if replacement == old:
                return {"status": "unchanged", "reference": reference}
            if self._blocked(connection, replacement):
                return {"status": "rejected", "reason": "This fact needs explicit reactivation after correction or forgetting"}
            existing = self._duplicate(connection, scope, replacement, row["category"], row["project"], row["path"])
            if row["category"] == "project" and not existing:
                # Native path slugs must remain unchanged for section references.
                result = self._archive_write(connection, item, check_current=check_current)
                if not result.get("ok"):
                    return {"status": "rejected", "reason": result.get("message", "Native correction rejected")}
                path = Path(result["path"])
            elif row["category"] != "project":
                entries = current['entries']
                if old not in entries:
                    return {"status": "conflict", "reason": "The native fact changed before correction"}
                updated = [value for value in entries if value != old] if existing else [replacement if value == old else value for value in entries]
                if check_current is not None:
                    check_current(connection)
                result = self._native("set_hot", path=str(path), entries=updated, writer=scope.writer, allowDrastic=True)
                if not result.get("ok"):
                    return {"status": "rejected", "reason": result.get("message", "Native correction rejected")}
            elif check_current is not None:
                check_current(connection)
            new_reference = ({"id": existing["id"], "revision": existing["revision"]} if existing else
                             self._record(connection, scope, path, replacement, row["category"], row["project"],
                                          {"session": row["source_session"], "kind": "correction"}))
            connection.execute("UPDATE records SET status='superseded',revision=revision+1,updated=? WHERE id=?", (_now(), row["id"]))
            return {"status": "committed", "reference": new_reference, "supersedes": reference}
        return self._operation(scope, request_id, {"operation": "correct", "reference": reference, "content": content}, change)

    def forget(self, scope: MemoryScope, reference: dict[str, Any], request_id: str,
               check_current=None) -> dict[str, Any]:
        def remove(connection):
            if check_current is not None:
                check_current(connection)
            row = self._target(connection, scope, reference)
            if row is None:
                return {"status": "rejected", "reason": "The memory reference is unavailable or has no write grant"}
            if row["status"] != "active" or row["revision"] != reference["revision"]:
                return {"status": "conflict", "reason": "The referenced revision is no longer current"}
            if row["category"] != "project":
                if row['category'] not in scope.read:
                    return {'status': 'rejected', 'reason': 'Hot-memory forgetting requires read and write grants'}
                current = self._hot_snapshot(connection, row['category'])
                content = self._content(row)
                path = self._path(row["path"])
                if content not in current.get("entries", []):
                    return {"status": "conflict", "reason": "The native fact changed before forgetting"}
                if check_current is not None:
                    check_current(connection)
                result = self._native("set_hot", path=str(path), entries=[value for value in current["entries"] if value != content],
                                      writer=scope.writer, allowDrastic=True)
                if not result.get("ok"):
                    return {"status": "rejected", "reason": result.get("message", "Native forgetting rejected")}
            elif check_current is not None:
                check_current(connection)
            connection.execute("UPDATE records SET status='forgotten',revision=revision+1,updated=? WHERE id=?", (_now(), row["id"]))
            return {"status": "committed", "reference": {"id": row["id"], "revision": row["revision"] + 1},
                    "retained": ["native history", "audit evidence", "backups", "conversation history", "development logs"]}
        return self._operation(scope, request_id, {"operation": "forget", "reference": reference}, remove)
