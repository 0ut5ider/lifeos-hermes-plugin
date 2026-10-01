# ABOUTME: Gives Hermes and authenticated clients the same native memory tool operations.
# ABOUTME: Loads private server-owned identity grants for each request and reports truthful results.

from __future__ import annotations

import json
from contextlib import contextmanager
import fcntl
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import stat
from typing import Any

from .memory_access import HOT_FILES, NativeMemory, MemoryUnavailable
from .memory_policy import CATEGORIES, MemoryPolicy, MemoryScope, SessionContext
from .memory_transaction import publish


REFERENCE = {"type": "object", "properties": {"id": {"type": "string"}, "revision": {"type": "integer", "minimum": 1}},
             "required": ["id", "revision"], "additionalProperties": False}
FIELDS = {
    "query": {"type": "string", "minLength": 1, "maxLength": 4096},
    "limit": {"type": "integer", "minimum": 1, "maximum": 100},
    "reference": REFERENCE,
    "decision": {"type":"string", "enum":["accept", "reject", "edit", "applied_elsewhere"]},
    "proposal": {"type":"object", "properties":{
        "type":{"type":"string", "enum":["proposal"]},
        "target_kind":{"type":"string"}, "target_file":{"type":"string"}, "edit":{"type":"string"},
        "confidence":{"type":"number", "minimum":0, "maximum":1}, "rationale":{"type":"string"},
        "source_session":{"type":"string"}, "observed_across_sessions":{"type":"integer", "minimum":1}},
        "required":["type", "target_file", "edit", "confidence", "rationale"], "additionalProperties":False},
    "category": {"type": "string", "enum": sorted(CATEGORIES)},
    "content": {"type": "string", "minLength": 1, "maxLength": 65536},
    "note": {"type":"string", "minLength":1, "maxLength":65536},
    "title": {"type": "string", "maxLength": 1024}, "project": {"type": "string", "maxLength": 256},
    "request_id": {"type": "string", "minLength": 1, "maxLength": 256},
}
TOOLS = {
    "lifeos_memory_propose": ("Submit a native LifeOS change for review. Pending and diverted changes are not applied edits.",
                              ("proposal", "request_id"), ()),
    "lifeos_memory_proposals": ("List permitted pending native LifeOS changes and their references.", (), ()),
    "lifeos_memory_decide_proposal": ("Apply or reject a referenced proposal with a separate approval grant.",
                                     ("reference", "decision", "request_id"), ("content", "note")),
    "lifeos_memory_status": ("Check lasting memory access and availability.", (), ()),
    "lifeos_memory_search": ("Find permitted current LifeOS facts and their references.", ("query",), ("limit",)),
    "lifeos_memory_get": ("Read one current fact by its returned reference.", ("reference",), ()),
    "lifeos_memory_remember": ("Save a fact. Report the returned status; reuse request_id only for an identical retry.",
                               ("category", "content", "title", "project", "request_id"), ()),
    "lifeos_memory_correct": ("Correct a referenced current fact. Superseded facts leave ordinary recall.",
                              ("reference", "content", "request_id"), ()),
    "lifeos_memory_forget": ("Exclude a fact from ordinary recall. Retained history and backups are not erased.",
                             ("reference", "request_id"), ()),
}


def tool_schemas() -> list[dict[str, Any]]:
    return [{"name": name, "description": description,
             "parameters": {"type": "object", "properties": {key: FIELDS[key] for key in (*required, *optional)},
                            "required": list(required), "additionalProperties": False}}
            for name, (description, required, optional) in TOOLS.items()]


def _validate_arguments(name: str, arguments: Any) -> None:
    if name not in TOOLS or not isinstance(arguments, dict):
        raise ValueError("Unknown memory tool or invalid arguments")
    _, required, optional = TOOLS[name]
    if set(arguments) - set((*required, *optional)) or set(required) - set(arguments):
        raise ValueError("Memory tool arguments contain missing or unrecognized fields")
    for key, value in arguments.items():
        schema = FIELDS[key]
        if schema["type"] == "string":
            if not isinstance(value, str) or not schema.get("minLength", 0) <= len(value) <= schema.get("maxLength", 65536):
                raise ValueError(f"Invalid {key}")
            if "enum" in schema and value not in schema["enum"]:
                raise ValueError(f"Invalid {key}")
        elif schema["type"] == "integer":
            if type(value) is not int or not schema["minimum"] <= value <= schema["maximum"]:
                raise ValueError(f"Invalid {key}")
        elif key == "proposal":
            if (not isinstance(value, dict) or set(value) - set(schema["properties"])
                    or set(schema["required"]) - set(value) or value.get("type") != "proposal"):
                raise ValueError("Invalid native proposal fields")
        elif key == "reference":
            if not isinstance(value, dict) or set(value) != {"id", "revision"} or not isinstance(value["id"], str) or not value["id"]:
                raise ValueError("Invalid memory reference")
            if type(value["revision"]) is not int or value["revision"] < 1:
                raise ValueError("Invalid memory revision")


class MemoryConfiguration:
    def __init__(self, path: Path):
        self.path = Path(path)

    @staticmethod
    def check_owner(configuration: dict[str, Any], account: str | None) -> None:
        # Internal owner helpers have no HTTP account; HTTP callers supply a verified qualified account.
        if account is not None and (not isinstance(account, str)
                or configuration.get('accounts', {}).get(account) != configuration['principal']):
            raise PermissionError('This dashboard account has no installation owner binding')

    @staticmethod
    def validate(configuration: Any) -> None:
        if not isinstance(configuration, dict) or type(configuration.get("version")) is not int or configuration["version"] != 1:
            raise ValueError("Unsupported memory configuration")
        if not isinstance(configuration.get("root"), str) or not Path(configuration["root"]).is_absolute():
            raise ValueError("Memory needs an absolute installed LifeOS root")
        if type(configuration.get("ownership_enabled", False)) is not bool:
            raise ValueError("Memory ownership must be enabled explicitly")
        if type(configuration.get("sharing_enabled", False)) is not bool:
            raise ValueError("Memory sharing must be enabled explicitly")
        MemoryPolicy(configuration)
        clients = configuration.get("clients", {})
        if not isinstance(clients, dict):
            raise ValueError("Memory clients must have server-owned grants")
        for identifier, grant in clients.items():
            if not isinstance(identifier, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", identifier):
                raise ValueError("Invalid memory client identifier")
            if not isinstance(grant, dict) or type(grant.get("enabled")) is not bool:
                raise ValueError("Invalid memory client grant")
            for key in ("read", "write", "projects"):
                values = grant.get(key, [])
                if not isinstance(values, list) or any(not isinstance(value, str) or not value.strip() for value in values):
                    raise ValueError("Invalid memory client permissions")
            if not set(grant.get("read", [])) <= CATEGORIES or not set(grant.get("write", [])) <= {"project"}:
                raise ValueError("Clients can write project facts; identity changes require native review")
            if (not isinstance(grant.get("proposals", []), list)
                    or any(not isinstance(value, str) or value not in {"create", "review"} for value in grant.get("proposals", []))):
                raise ValueError("External clients cannot approve native proposals")
            if not isinstance(grant.get("model_route", "unknown"), str) or not grant.get("model_route", "unknown"):
                raise ValueError("Invalid declared client model route")

    def load(self) -> dict[str, Any]:
        if self.path.is_symlink() or not self.path.is_file():
            raise MemoryUnavailable("Memory setup is unavailable")
        info = self.path.stat()
        if info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise MemoryUnavailable("Memory configuration needs private owner permissions")
        configuration = json.loads(self.path.read_text())
        self.validate(configuration)
        return configuration

    def save(self, configuration: dict[str, Any]) -> None:
        self.validate(configuration)
        with self._lock():
            self._publish(configuration)

    @contextmanager
    def _lock(self):
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor = os.open(self.path.with_name(self.path.name + '.lock'),
                             os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            info = os.fstat(descriptor)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise MemoryUnavailable('Memory configuration lock needs private owner permissions')
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        finally:
            os.close(descriptor)

    def _publish(self, configuration: dict[str, Any]) -> None:
        if self.path.is_symlink():
            raise MemoryUnavailable('Memory configuration must not be a symlink')
        publish(self.path, (json.dumps(configuration, indent=2) + '\n').encode())

    def update(self, change) -> dict[str, Any]:
        with self._lock():
            configuration = self.load()
            change(configuration)
            self.validate(configuration)
            self._publish(configuration)
            return configuration


class MemoryService:
    def __init__(self, configuration: MemoryConfiguration):
        self.configuration = configuration

    def scope(self, context: SessionContext) -> MemoryScope:
        return MemoryPolicy(self.configuration.load()).resolve(context)

    def native(self, context: SessionContext, operation: str, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            configuration = self.configuration.load()
            scope = MemoryPolicy(configuration).resolve(context)
            memory = NativeMemory(Path(configuration["root"]))
            if operation == "check_sources" and not arguments:
                from .memory_sources import authorize
                return authorize(scope)
            if operation == "check_source" and set(arguments) == {"path"}:
                from .memory_sources import check
                return check(memory,scope,arguments['path'])
            if operation == "filter_source" and set(arguments) == {"content","timestamp"}:
                from .memory_sources import filter_content
                return filter_content(memory,scope,**arguments)
            if operation == "read_source" and set(arguments) == {"path"}:
                from .memory_sources import read
                return read(memory,scope,arguments['path'])
            if operation == "read_diagnostic" and set(arguments) == {"path"}:
                from .memory_diagnostics import read
                return read(memory,scope,arguments['path'])
            if operation == "check_diagnostic" and set(arguments) == {"path"}:
                from .memory_diagnostics import check
                return check(memory,scope,arguments['path'])
            if operation == "check_diagnostic_report" and set(arguments) == {"path"}:
                from .memory_diagnostics import check
                return check(memory,scope,arguments['path'],report=True)
            if operation == "filter_diagnostic" and set(arguments) == {"content", "timestamp"}:
                from .memory_diagnostics import filter_report
                return filter_report(memory,scope,**arguments)
            if operation == "diagnose_hot" and set(arguments) == {"path"}:
                from .memory_diagnostics import diagnose_hot
                return diagnose_hot(memory,scope,arguments['path'])
            if operation == "proposal_list" and set(arguments) == {"path"}:
                from .memory_proposals import QUEUE
                if not isinstance(arguments['path'], str) or Path(arguments['path']).absolute() != memory._path(QUEUE):
                    raise ValueError("Native proposal review needs the installed queue")
                return {"rows":memory.review_proposals(scope, include_resolved=True)}
            if operation == "proposal_decision":
                required = {"reference", "decision", "request_id"}
                if not required <= set(arguments) or set(arguments) - required - {"content", "note", "confidence_threshold"}:
                    raise ValueError("Invalid native proposal decision fields")
                receipt = memory.decide_proposal(scope, **arguments)
                row = memory.proposal_decision_row(scope, receipt['proposal_reference']) if receipt['status'] == 'committed' else None
                return {"ok":receipt['status'] == 'committed', "row":row, "receipt":receipt,
                        "reason":receipt.get('reason', '')}
            if operation == "retrieve" and set(arguments) == {"query", "options"}:
                return memory.relevant_context(scope, **arguments)
            if operation == "filter_history" and set(arguments) == {"content", "timestamp"}:
                return memory.filter_history(scope, **arguments)
            if operation in ("read", "set"):
                if not isinstance(arguments.get("path"), str):
                    raise ValueError("A native hot-memory path is required")
                categories = {str(memory._path(path)): category for category, path in HOT_FILES.items()}
                category = categories.get(str(Path(arguments["path"]).absolute()))
                if category is None:
                    raise ValueError("This is not a supported native hot-memory path")
                if operation == "read" and set(arguments) == {"path"}:
                    return memory.read_hot(scope, category)
                if operation == "set" and set(arguments) == {"path", "entries", "request_id", "observed_revision", "allow_drastic"}:
                    return memory.native_set(scope, category, source_session=context.session_id,
                                             **{key: value for key, value in arguments.items() if key != "path"})
            if operation == "add" and set(arguments) == {"item", "request_id", "project", "observed_revision"}:
                return memory.native_add(scope, **arguments, source_session=context.session_id)
            raise ValueError("Unsupported native memory operation or arguments")
        except (MemoryUnavailable, ValueError, OSError, sqlite3.Error, subprocess.TimeoutExpired) as error:
            return {"ok": False, "code": "EWRITE_FAILED" if operation in ("add", "set") else "EINVAL_PATH", "message": str(error)}

    @staticmethod
    def client_scope(configuration: dict[str, Any], identifier: str) -> MemoryScope:
        grant = configuration.get("clients", {}).get(identifier)
        if not configuration.get("sharing_enabled", False) or grant is None or not grant["enabled"]:
            raise MemoryUnavailable("This memory connection is disabled or revoked")
        principal = f"client:{identifier}"
        policy = MemoryPolicy({"version": 1, "principal": configuration["principal"],
                               "accounts": {f"mcp:{identifier}": principal},
                               "destinations": {f"mcp:{identifier}": {
                                   "visibility": "private", "participants": [principal],
                                   "read": grant.get("read", ["project"]), "write": grant.get("write", []),
                                   "projects": grant.get("projects", []), "model_routes": [grant.get("model_route", "unknown")],
                                   "proposals": grant.get("proposals", []),
                               }}})
        return policy.resolve(SessionContext("mcp", identifier, identifier, "private", (principal,),
                                             grant.get("model_route", "unknown"), ""))

    def call_client(self, identifier: str, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            configuration = self.configuration.load()
            scope = self.client_scope(configuration, identifier)
        except (MemoryUnavailable, ValueError, OSError) as error:
            return {"status": "rejected", "reason": str(error)}
        return self._call(configuration, scope, name, arguments)

    def call_context(self, context: SessionContext, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            configuration = self.configuration.load()
            scope = MemoryPolicy(configuration).resolve(context)
        except (MemoryUnavailable, ValueError, OSError) as error:
            return {"status": "unavailable", "reason": str(error)}
        return self._call(configuration, scope, name, arguments, source_session=context.session_id)

    def call(self, scope: MemoryScope, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            configuration = self.configuration.load()
        except (MemoryUnavailable, ValueError, OSError) as error:
            return {"status": "unavailable", "reason": str(error)}
        return self._call(configuration, scope, name, arguments)

    def _call(self, configuration: dict[str, Any], scope: MemoryScope, name: str, arguments: dict[str, Any],
              *, source_session: str = '') -> dict[str, Any]:
        try:
            _validate_arguments(name, arguments)
        except ValueError as error:
            return {"status": "rejected", "reason": str(error)}
        try:
            memory = NativeMemory(Path(configuration["root"]))
            if not scope.read and not scope.write and not scope.proposals:
                return {"status": "rejected", "reason": scope.reason or "This context has no memory grant"}
            if name == "lifeos_memory_propose":
                result = memory.native_add(scope, arguments["proposal"], request_id=arguments["request_id"], project="",
                                           source_session=source_session)
                return result.get("receipt", {"status":"rejected", "reason":result.get("message", "Native proposal failed")})
            if name == "lifeos_memory_proposals":
                return {"status":"ok", "results":memory.review_proposals(scope)}
            if name == "lifeos_memory_decide_proposal":
                return memory.decide_proposal(scope, **arguments)
            if name == "lifeos_memory_search":
                return {"status": "ok", "results": memory.recall(scope, **arguments)}
            if name == "lifeos_memory_get":
                return memory.get(scope, arguments["reference"])
            if name == "lifeos_memory_remember":
                return memory.remember(scope, **arguments, source={'kind': 'explicit', 'session': source_session})
            if name == "lifeos_memory_correct":
                return memory.correct(scope, **arguments)
            if name == "lifeos_memory_forget":
                return memory.forget(scope, **arguments)
            memory._boundary()
            with memory._transaction() as connection:
                connection.execute("SELECT id FROM records LIMIT 1").fetchone()
            memory._native("rank", query="memory health", corpus=[], limit=1)
            return {"status": "ok", "owner": "LifeOS", "read": list(scope.read), "write": list(scope.write),
                    "projects": list(scope.projects), "sharing_enabled": configuration.get("sharing_enabled", False)}
        except (MemoryUnavailable, ValueError, OSError, sqlite3.Error, subprocess.TimeoutExpired) as error:
            return {"status": "unavailable", "reason": str(error)}
