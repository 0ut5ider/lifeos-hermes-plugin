# ABOUTME: Resolves memory permissions from host-approved identities and conversation metadata.
# ABOUTME: Uses the same access rules for every messaging app and restricts unknown contexts.

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any


CATEGORIES = frozenset({"project", "principal", "assistant"})
PROPOSAL_PERMISSIONS = frozenset({"create", "review", "approve", "auto_apply"})


@dataclass(frozen=True)
class SessionContext:
    transport: str
    author: str
    destination: str
    visibility: str
    participants: tuple[str, ...]
    model_route: str
    session_id: str


@dataclass(frozen=True)
class MemoryScope:
    principal: str
    writer: str
    read: tuple[str, ...]
    write: tuple[str, ...]
    projects: tuple[str, ...]
    signature: str
    reason: str = ""
    proposals: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _strings(value: Any, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(v, str) or not v.strip() for v in value):
        raise ValueError(f"{label} must contain nonempty strings")
    return tuple(sorted(set(value)))


class MemoryPolicy:
    def __init__(self, configuration: dict[str, Any]):
        if configuration.get("version") != 1 or not isinstance(configuration.get("principal"), str):
            raise ValueError("Unsupported memory policy or missing principal")
        self.principal = configuration["principal"]
        self.accounts = configuration.get("accounts", {})
        destinations = configuration.get("destinations", {})
        if not self.principal or not isinstance(self.accounts, dict) or not isinstance(destinations, dict):
            raise ValueError("Invalid memory identity or destination policy")
        if any(not isinstance(k, str) or ":" not in k or not isinstance(v, str) or not v
               for k, v in self.accounts.items()):
            raise ValueError("Account bindings must map qualified account IDs to principals")
        self.destinations = {}
        for identifier, grant in destinations.items():
            if not isinstance(identifier, str) or ":" not in identifier or not isinstance(grant, dict):
                raise ValueError("Invalid destination grant")
            if grant.get("visibility") not in {"private", "shared"}:
                raise ValueError("Destination visibility must be private or shared")
            clean = dict(grant)
            for kind in ("read", "write"):
                clean[kind] = _strings(grant.get(kind, []), kind)
                if not set(clean[kind]) <= CATEGORIES:
                    raise ValueError(f"Unknown memory category in {kind}")
            clean["proposals"] = _strings(grant.get("proposals", []), "proposals")
            if not set(clean["proposals"]) <= PROPOSAL_PERMISSIONS:
                raise ValueError("Unknown proposal permission")
            clean["participants"] = _strings(grant.get("participants", []), "participants")
            clean["projects"] = _strings(grant.get("projects", ["*"]), "projects")
            clean["model_routes"] = _strings(grant.get("model_routes", ["local"]), "model_routes")
            self.destinations[identifier] = clean
        self.revision = hashlib.sha256(json.dumps(configuration, sort_keys=True).encode()).hexdigest()

    def resolve(self, context: SessionContext) -> MemoryScope:
        writer = f"{context.transport}:{context.author}"
        principal = self.accounts.get(writer, "")
        destination = self.destinations.get(f"{context.transport}:{context.destination}")
        reason = ""
        if not principal:
            reason = "The current account has no approved identity binding"
        elif destination is None:
            reason = "The destination has no approved memory grant"
        elif context.visibility != destination["visibility"]:
            reason = "Conversation visibility is unknown or differs from its approved grant"
        elif tuple(sorted(set(context.participants))) != destination["participants"]:
            reason = "Conversation participants differ from the approved audience"
        elif principal not in context.participants:
            reason = "The authenticated author is outside the approved audience"
        elif context.model_route not in destination["model_routes"]:
            reason = "The model route has no approved memory grant"
        read = destination["read"] if not reason else ()
        write = destination["write"] if not reason else ()
        projects = destination["projects"] if not reason else ()
        proposals = destination["proposals"] if not reason else ()
        signature = hashlib.sha256(json.dumps({
            "context": asdict(context), "policy": self.revision, "principal": principal,
            "read": read, "write": write, "projects": projects, "proposals": proposals,
        }, sort_keys=True).encode()).hexdigest()
        return MemoryScope(principal, writer, read, write, projects, signature, reason, proposals)
