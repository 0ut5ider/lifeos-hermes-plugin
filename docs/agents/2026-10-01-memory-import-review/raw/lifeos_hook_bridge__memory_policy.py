     1	# ABOUTME: Resolves memory permissions from host-approved identities and conversation metadata.
     2	# ABOUTME: Uses the same access rules for every messaging app and restricts unknown contexts.
     3	
     4	from __future__ import annotations
     5	
     6	from dataclasses import asdict, dataclass
     7	import hashlib
     8	import json
     9	from typing import Any
    10	
    11	
    12	CATEGORIES = frozenset({"project", "principal", "assistant"})
    13	PROPOSAL_PERMISSIONS = frozenset({"create", "review", "approve", "auto_apply"})
    14	
    15	
    16	@dataclass(frozen=True)
    17	class SessionContext:
    18	    transport: str
    19	    author: str
    20	    destination: str
    21	    visibility: str
    22	    participants: tuple[str, ...]
    23	    model_route: str
    24	    session_id: str
    25	
    26	
    27	@dataclass(frozen=True)
    28	class MemoryScope:
    29	    principal: str
    30	    writer: str
    31	    read: tuple[str, ...]
    32	    write: tuple[str, ...]
    33	    projects: tuple[str, ...]
    34	    signature: str
    35	    reason: str = ""
    36	    proposals: tuple[str, ...] = ()
    37	
    38	    def as_dict(self) -> dict[str, Any]:
    39	        return asdict(self)
    40	
    41	
    42	def _strings(value: Any, label: str) -> tuple[str, ...]:
    43	    if not isinstance(value, list) or any(not isinstance(v, str) or not v.strip() for v in value):
    44	        raise ValueError(f"{label} must contain nonempty strings")
    45	    return tuple(sorted(set(value)))
    46	
    47	
    48	class MemoryPolicy:
    49	    def __init__(self, configuration: dict[str, Any]):
    50	        if configuration.get("version") != 1 or not isinstance(configuration.get("principal"), str):
    51	            raise ValueError("Unsupported memory policy or missing principal")
    52	        self.principal = configuration["principal"]
    53	        self.accounts = configuration.get("accounts", {})
    54	        destinations = configuration.get("destinations", {})
    55	        if not self.principal or not isinstance(self.accounts, dict) or not isinstance(destinations, dict):
    56	            raise ValueError("Invalid memory identity or destination policy")
    57	        if any(not isinstance(k, str) or ":" not in k or not isinstance(v, str) or not v
    58	               for k, v in self.accounts.items()):
    59	            raise ValueError("Account bindings must map qualified account IDs to principals")
    60	        self.destinations = {}
    61	        for identifier, grant in destinations.items():
    62	            if not isinstance(identifier, str) or ":" not in identifier or not isinstance(grant, dict):
    63	                raise ValueError("Invalid destination grant")
    64	            if grant.get("visibility") not in {"private", "shared"}:
    65	                raise ValueError("Destination visibility must be private or shared")
    66	            clean = dict(grant)
    67	            for kind in ("read", "write"):
    68	                clean[kind] = _strings(grant.get(kind, []), kind)
    69	                if not set(clean[kind]) <= CATEGORIES:
    70	                    raise ValueError(f"Unknown memory category in {kind}")
    71	            clean["proposals"] = _strings(grant.get("proposals", []), "proposals")
    72	            if not set(clean["proposals"]) <= PROPOSAL_PERMISSIONS:
    73	                raise ValueError("Unknown proposal permission")
    74	            clean["participants"] = _strings(grant.get("participants", []), "participants")
    75	            clean["projects"] = _strings(grant.get("projects", ["*"]), "projects")
    76	            clean["model_routes"] = _strings(grant.get("model_routes", ["local"]), "model_routes")
    77	            self.destinations[identifier] = clean
    78	        self.revision = hashlib.sha256(json.dumps(configuration, sort_keys=True).encode()).hexdigest()
    79	
    80	    def resolve(self, context: SessionContext) -> MemoryScope:
    81	        writer = f"{context.transport}:{context.author}"
    82	        principal = self.accounts.get(writer, "")
    83	        destination = self.destinations.get(f"{context.transport}:{context.destination}")
    84	        reason = ""
    85	        if not principal:
    86	            reason = "The current account has no approved identity binding"
    87	        elif destination is None:
    88	            reason = "The destination has no approved memory grant"
    89	        elif context.visibility != destination["visibility"]:
    90	            reason = "Conversation visibility is unknown or differs from its approved grant"
    91	        elif tuple(sorted(set(context.participants))) != destination["participants"]:
    92	            reason = "Conversation participants differ from the approved audience"
    93	        elif principal not in context.participants:
    94	            reason = "The authenticated author is outside the approved audience"
    95	        elif context.model_route not in destination["model_routes"]:
    96	            reason = "The model route has no approved memory grant"
    97	        read = destination["read"] if not reason else ()
    98	        write = destination["write"] if not reason else ()
    99	        projects = destination["projects"] if not reason else ()
   100	        proposals = destination["proposals"] if not reason else ()
   101	        signature = hashlib.sha256(json.dumps({
   102	            "context": asdict(context), "policy": self.revision, "principal": principal,
   103	            "read": read, "write": write, "projects": projects, "proposals": proposals,
   104	        }, sort_keys=True).encode()).hexdigest()
   105	        return MemoryScope(principal, writer, read, write, projects, signature, reason, proposals)
