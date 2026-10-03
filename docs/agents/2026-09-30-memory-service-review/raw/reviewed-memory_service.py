# ABOUTME: Gives Hermes and authenticated clients the same native memory tool operations.
# ABOUTME: Loads private server-owned identity grants for each request and reports truthful results.

from __future__ import annotations

import json
import os
from pathlib import Path
import re
from typing import Any

from .memory_access import NativeMemory, MemoryUnavailable
from .memory_policy import CATEGORIES, MemoryPolicy, MemoryScope, SessionContext
from .memory_transaction import publish


REFERENCE = {"type": "object", "properties": {"id": {"type": "string"}, "revision": {"type": "integer", "minimum": 1}},
             "required": ["id", "revision"], "additionalProperties": False}
FIELDS = {
    "query": {"type": "string", "minLength": 1, "maxLength": 4096},
    "limit": {"type": "integer", "minimum": 1, "maximum": 100},
    "reference": REFERENCE,
    "category": {"type": "string", "enum": sorted(CATEGORIES)},
    "content": {"type": "string", "minLength": 1, "maxLength": 65536},
    "title": {"type": "string", "maxLength": 1024}, "project": {"type": "string", "maxLength": 256},
    "request_id": {"type": "string", "minLength": 1, "maxLength": 256},
}
TOOLS = {
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
        elif key == "reference":
            if not isinstance(value, dict) or set(value) != {"id", "revision"} or not isinstance(value["id"], str) or not value["id"]:
                raise ValueError("Invalid memory reference")
            if type(value["revision"]) is not int or value["revision"] < 1:
                raise ValueError("Invalid memory revision")


class MemoryConfiguration:
    def __init__(self, path: Path):
        self.path = Path(path)

    @staticmethod
    def validate(configuration: Any) -> None:
        if not isinstance(configuration, dict) or type(configuration.get("version")) is not int or configuration["version"] != 1:
            raise ValueError("Unsupported memory configuration")
        if not isinstance(configuration.get("root"), str) or not Path(configuration["root"]).is_absolute():
            raise ValueError("Memory needs an absolute installed LifeOS root")
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
        publish(self.path, (json.dumps(configuration, indent=2) + "\n").encode())


class MemoryService:
    def __init__(self, configuration: MemoryConfiguration):
        self.configuration = configuration

    def scope(self, context: SessionContext) -> MemoryScope:
        return MemoryPolicy(self.configuration.load()).resolve(context)

    def client_scope(self, identifier: str) -> MemoryScope:
        configuration = self.configuration.load()
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
                               }}})
        return policy.resolve(SessionContext("mcp", identifier, identifier, "private", (principal,),
                                             grant.get("model_route", "unknown"), ""))

    def call_client(self, identifier: str, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            scope = self.client_scope(identifier)
        except (MemoryUnavailable, ValueError, OSError) as error:
            return {"status": "rejected", "reason": str(error)}
        return self.call(scope, name, arguments)

    def call(self, scope: MemoryScope, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            _validate_arguments(name, arguments)
        except ValueError as error:
            return {"status": "rejected", "reason": str(error)}
        try:
            configuration = self.configuration.load()
            memory = NativeMemory(Path(configuration["root"]))
            if not scope.read and not scope.write:
                return {"status": "rejected", "reason": scope.reason or "This context has no memory grant"}
            if name == "lifeos_memory_search":
                return {"status": "ok", "results": memory.recall(scope, **arguments)}
            if name == "lifeos_memory_get":
                return memory.get(scope, arguments["reference"])
            if name == "lifeos_memory_remember":
                return memory.remember(scope, **arguments)
            if name == "lifeos_memory_correct":
                return memory.correct(scope, **arguments)
            if name == "lifeos_memory_forget":
                return memory.forget(scope, **arguments)
            memory._boundary()
            return {"status": "ok", "owner": "LifeOS", "read": list(scope.read), "write": list(scope.write),
                    "projects": list(scope.projects), "sharing_enabled": configuration.get("sharing_enabled", False)}
        except (MemoryUnavailable, ValueError, OSError) as error:
            return {"status": "unavailable", "reason": str(error)}
