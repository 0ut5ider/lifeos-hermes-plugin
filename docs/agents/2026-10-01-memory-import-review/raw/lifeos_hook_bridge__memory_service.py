     1	# ABOUTME: Gives Hermes and authenticated clients the same native memory tool operations.
     2	# ABOUTME: Loads private server-owned identity grants for each request and reports truthful results.
     3	
     4	from __future__ import annotations
     5	
     6	import json
     7	from contextlib import contextmanager
     8	import fcntl
     9	import os
    10	from pathlib import Path
    11	import re
    12	import sqlite3
    13	import subprocess
    14	import stat
    15	from typing import Any
    16	
    17	from .memory_access import HOT_FILES, NativeMemory, MemoryUnavailable
    18	from .memory_policy import CATEGORIES, MemoryPolicy, MemoryScope, SessionContext
    19	from .memory_transaction import publish
    20	
    21	
    22	REFERENCE = {"type": "object", "properties": {"id": {"type": "string"}, "revision": {"type": "integer", "minimum": 1}},
    23	             "required": ["id", "revision"], "additionalProperties": False}
    24	FIELDS = {
    25	    "query": {"type": "string", "minLength": 1, "maxLength": 4096},
    26	    "limit": {"type": "integer", "minimum": 1, "maximum": 100},
    27	    "reference": REFERENCE,
    28	    "decision": {"type":"string", "enum":["accept", "reject", "edit", "applied_elsewhere"]},
    29	    "proposal": {"type":"object", "properties":{
    30	        "type":{"type":"string", "enum":["proposal"]},
    31	        "target_kind":{"type":"string"}, "target_file":{"type":"string"}, "edit":{"type":"string"},
    32	        "confidence":{"type":"number", "minimum":0, "maximum":1}, "rationale":{"type":"string"},
    33	        "source_session":{"type":"string"}, "observed_across_sessions":{"type":"integer", "minimum":1}},
    34	        "required":["type", "target_file", "edit", "confidence", "rationale"], "additionalProperties":False},
    35	    "category": {"type": "string", "enum": sorted(CATEGORIES)},
    36	    "content": {"type": "string", "minLength": 1, "maxLength": 65536},
    37	    "note": {"type":"string", "minLength":1, "maxLength":65536},
    38	    "title": {"type": "string", "maxLength": 1024}, "project": {"type": "string", "maxLength": 256},
    39	    "request_id": {"type": "string", "minLength": 1, "maxLength": 256},
    40	}
    41	TOOLS = {
    42	    "lifeos_memory_propose": ("Submit a native LifeOS change for review. Pending and diverted changes are not applied edits.",
    43	                              ("proposal", "request_id"), ()),
    44	    "lifeos_memory_proposals": ("List permitted pending native LifeOS changes and their references.", (), ()),
    45	    "lifeos_memory_decide_proposal": ("Apply or reject a referenced proposal with a separate approval grant.",
    46	                                     ("reference", "decision", "request_id"), ("content", "note")),
    47	    "lifeos_memory_status": ("Check lasting memory access and availability.", (), ()),
    48	    "lifeos_memory_search": ("Find permitted current LifeOS facts and their references.", ("query",), ("limit",)),
    49	    "lifeos_memory_get": ("Read one current fact by its returned reference.", ("reference",), ()),
    50	    "lifeos_memory_remember": ("Save a fact. Report the returned status; reuse request_id only for an identical retry.",
    51	                               ("category", "content", "title", "project", "request_id"), ()),
    52	    "lifeos_memory_correct": ("Correct a referenced current fact. Superseded facts leave ordinary recall.",
    53	                              ("reference", "content", "request_id"), ()),
    54	    "lifeos_memory_forget": ("Exclude a fact from ordinary recall. Retained history and backups are not erased.",
    55	                             ("reference", "request_id"), ()),
    56	}
    57	
    58	
    59	def tool_schemas() -> list[dict[str, Any]]:
    60	    return [{"name": name, "description": description,
    61	             "parameters": {"type": "object", "properties": {key: FIELDS[key] for key in (*required, *optional)},
    62	                            "required": list(required), "additionalProperties": False}}
    63	            for name, (description, required, optional) in TOOLS.items()]
    64	
    65	
    66	def _validate_arguments(name: str, arguments: Any) -> None:
    67	    if name not in TOOLS or not isinstance(arguments, dict):
    68	        raise ValueError("Unknown memory tool or invalid arguments")
    69	    _, required, optional = TOOLS[name]
    70	    if set(arguments) - set((*required, *optional)) or set(required) - set(arguments):
    71	        raise ValueError("Memory tool arguments contain missing or unrecognized fields")
    72	    for key, value in arguments.items():
    73	        schema = FIELDS[key]
    74	        if schema["type"] == "string":
    75	            if not isinstance(value, str) or not schema.get("minLength", 0) <= len(value) <= schema.get("maxLength", 65536):
    76	                raise ValueError(f"Invalid {key}")
    77	            if "enum" in schema and value not in schema["enum"]:
    78	                raise ValueError(f"Invalid {key}")
    79	        elif schema["type"] == "integer":
    80	            if type(value) is not int or not schema["minimum"] <= value <= schema["maximum"]:
    81	                raise ValueError(f"Invalid {key}")
    82	        elif key == "proposal":
    83	            if (not isinstance(value, dict) or set(value) - set(schema["properties"])
    84	                    or set(schema["required"]) - set(value) or value.get("type") != "proposal"):
    85	                raise ValueError("Invalid native proposal fields")
    86	        elif key == "reference":
    87	            if not isinstance(value, dict) or set(value) != {"id", "revision"} or not isinstance(value["id"], str) or not value["id"]:
    88	                raise ValueError("Invalid memory reference")
    89	            if type(value["revision"]) is not int or value["revision"] < 1:
    90	                raise ValueError("Invalid memory revision")
    91	
    92	
    93	class MemoryConfiguration:
    94	    def __init__(self, path: Path):
    95	        self.path = Path(path)
    96	
    97	    @staticmethod
    98	    def check_owner(configuration: dict[str, Any], account: str | None) -> None:
    99	        # Internal owner helpers have no HTTP account; HTTP callers supply a verified qualified account.
   100	        if account is not None and (not isinstance(account, str)
   101	                or configuration.get('accounts', {}).get(account) != configuration['principal']):
   102	            raise PermissionError('This dashboard account has no installation owner binding')
   103	
   104	    @staticmethod
   105	    def validate(configuration: Any) -> None:
   106	        if not isinstance(configuration, dict) or type(configuration.get("version")) is not int or configuration["version"] != 1:
   107	            raise ValueError("Unsupported memory configuration")
   108	        if not isinstance(configuration.get("root"), str) or not Path(configuration["root"]).is_absolute():
   109	            raise ValueError("Memory needs an absolute installed LifeOS root")
   110	        if type(configuration.get("ownership_enabled", False)) is not bool:
   111	            raise ValueError("Memory ownership must be enabled explicitly")
   112	        if type(configuration.get("sharing_enabled", False)) is not bool:
   113	            raise ValueError("Memory sharing must be enabled explicitly")
   114	        MemoryPolicy(configuration)
   115	        clients = configuration.get("clients", {})
   116	        if not isinstance(clients, dict):
   117	            raise ValueError("Memory clients must have server-owned grants")
   118	        for identifier, grant in clients.items():
   119	            if not isinstance(identifier, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", identifier):
   120	                raise ValueError("Invalid memory client identifier")
   121	            if not isinstance(grant, dict) or type(grant.get("enabled")) is not bool:
   122	                raise ValueError("Invalid memory client grant")
   123	            for key in ("read", "write", "projects"):
   124	                values = grant.get(key, [])
   125	                if not isinstance(values, list) or any(not isinstance(value, str) or not value.strip() for value in values):
   126	                    raise ValueError("Invalid memory client permissions")
   127	            if not set(grant.get("read", [])) <= CATEGORIES or not set(grant.get("write", [])) <= {"project"}:
   128	                raise ValueError("Clients can write project facts; identity changes require native review")
   129	            if (not isinstance(grant.get("proposals", []), list)
   130	                    or any(not isinstance(value, str) or value not in {"create", "review"} for value in grant.get("proposals", []))):
   131	                raise ValueError("External clients cannot approve native proposals")
   132	            if not isinstance(grant.get("model_route", "unknown"), str) or not grant.get("model_route", "unknown"):
   133	                raise ValueError("Invalid declared client model route")
   134	
   135	    def load(self) -> dict[str, Any]:
   136	        if self.path.is_symlink() or not self.path.is_file():
   137	            raise MemoryUnavailable("Memory setup is unavailable")
   138	        info = self.path.stat()
   139	        if info.st_uid != os.getuid() or info.st_mode & 0o077:
   140	            raise MemoryUnavailable("Memory configuration needs private owner permissions")
   141	        configuration = json.loads(self.path.read_text())
   142	        self.validate(configuration)
   143	        return configuration
   144	
   145	    def save(self, configuration: dict[str, Any]) -> None:
   146	        self.validate(configuration)
   147	        with self._lock():
   148	            self._publish(configuration)
   149	
   150	    @contextmanager
   151	    def _lock(self):
   152	        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
   153	        descriptor = os.open(self.path.with_name(self.path.name + '.lock'),
   154	                             os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
   155	        try:
   156	            info = os.fstat(descriptor)
   157	            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
   158	                raise MemoryUnavailable('Memory configuration lock needs private owner permissions')
   159	            fcntl.flock(descriptor, fcntl.LOCK_EX)
   160	            yield
   161	        finally:
   162	            os.close(descriptor)
   163	
   164	    def _publish(self, configuration: dict[str, Any]) -> None:
   165	        if self.path.is_symlink():
   166	            raise MemoryUnavailable('Memory configuration must not be a symlink')
   167	        publish(self.path, (json.dumps(configuration, indent=2) + '\n').encode())
   168	
   169	    def update(self, change) -> dict[str, Any]:
   170	        with self._lock():
   171	            configuration = self.load()
   172	            change(configuration)
   173	            self.validate(configuration)
   174	            self._publish(configuration)
   175	            return configuration
   176	
   177	
   178	class MemoryService:
   179	    def __init__(self, configuration: MemoryConfiguration):
   180	        self.configuration = configuration
   181	
   182	    def scope(self, context: SessionContext) -> MemoryScope:
   183	        return MemoryPolicy(self.configuration.load()).resolve(context)
   184	
   185	    def native(self, context: SessionContext, operation: str, arguments: dict[str, Any]) -> dict[str, Any]:
   186	        try:
   187	            configuration = self.configuration.load()
   188	            scope = MemoryPolicy(configuration).resolve(context)
   189	            memory = NativeMemory(Path(configuration["root"]))
   190	            if operation == "check_sources" and not arguments:
   191	                from .memory_sources import authorize
   192	                return authorize(scope)
   193	            if operation == "check_source" and set(arguments) == {"path"}:
   194	                from .memory_sources import check
   195	                return check(memory,scope,arguments['path'])
   196	            if operation == "filter_source" and set(arguments) == {"content","timestamp"}:
   197	                from .memory_sources import filter_content
   198	                return filter_content(memory,scope,**arguments)
   199	            if operation == "read_source" and set(arguments) == {"path"}:
   200	                from .memory_sources import read
   201	                return read(memory,scope,arguments['path'])
   202	            if operation == "read_diagnostic" and set(arguments) == {"path"}:
   203	                from .memory_diagnostics import read
   204	                return read(memory,scope,arguments['path'])
   205	            if operation == "check_diagnostic" and set(arguments) == {"path"}:
   206	                from .memory_diagnostics import check
   207	                return check(memory,scope,arguments['path'])
   208	            if operation == "check_diagnostic_report" and set(arguments) == {"path"}:
   209	                from .memory_diagnostics import check
   210	                return check(memory,scope,arguments['path'],report=True)
   211	            if operation == "filter_diagnostic" and set(arguments) == {"content", "timestamp"}:
   212	                from .memory_diagnostics import filter_report
   213	                return filter_report(memory,scope,**arguments)
   214	            if operation == "diagnose_hot" and set(arguments) == {"path"}:
   215	                from .memory_diagnostics import diagnose_hot
   216	                return diagnose_hot(memory,scope,arguments['path'])
   217	            if operation == "proposal_list" and set(arguments) == {"path"}:
   218	                from .memory_proposals import QUEUE
   219	                if not isinstance(arguments['path'], str) or Path(arguments['path']).absolute() != memory._path(QUEUE):
   220	                    raise ValueError("Native proposal review needs the installed queue")
   221	                return {"rows":memory.review_proposals(scope, include_resolved=True)}
   222	            if operation == "proposal_decision":
   223	                required = {"reference", "decision", "request_id"}
   224	                if not required <= set(arguments) or set(arguments) - required - {"content", "note", "confidence_threshold"}:
   225	                    raise ValueError("Invalid native proposal decision fields")
   226	                receipt = memory.decide_proposal(scope, **arguments)
   227	                row = memory.proposal_decision_row(scope, receipt['proposal_reference']) if receipt['status'] == 'committed' else None
   228	                return {"ok":receipt['status'] == 'committed', "row":row, "receipt":receipt,
   229	                        "reason":receipt.get('reason', '')}
   230	            if operation == "retrieve" and set(arguments) == {"query", "options"}:
   231	                return memory.relevant_context(scope, **arguments)
   232	            if operation == "filter_history" and set(arguments) == {"content", "timestamp"}:
   233	                return memory.filter_history(scope, **arguments)
   234	            if operation in ("read", "set"):
   235	                if not isinstance(arguments.get("path"), str):
   236	                    raise ValueError("A native hot-memory path is required")
   237	                categories = {str(memory._path(path)): category for category, path in HOT_FILES.items()}
   238	                category = categories.get(str(Path(arguments["path"]).absolute()))
   239	                if category is None:
   240	                    raise ValueError("This is not a supported native hot-memory path")
   241	                if operation == "read" and set(arguments) == {"path"}:
   242	                    return memory.read_hot(scope, category)
   243	                if operation == "set" and set(arguments) == {"path", "entries", "request_id", "observed_revision", "allow_drastic"}:
   244	                    return memory.native_set(scope, category, source_session=context.session_id,
   245	                                             **{key: value for key, value in arguments.items() if key != "path"})
   246	            if operation == "add" and set(arguments) == {"item", "request_id", "project", "observed_revision"}:
   247	                return memory.native_add(scope, **arguments, source_session=context.session_id)
   248	            raise ValueError("Unsupported native memory operation or arguments")
   249	        except (MemoryUnavailable, ValueError, OSError, sqlite3.Error, subprocess.TimeoutExpired) as error:
   250	            return {"ok": False, "code": "EWRITE_FAILED" if operation in ("add", "set") else "EINVAL_PATH", "message": str(error)}
   251	
   252	    @staticmethod
   253	    def client_scope(configuration: dict[str, Any], identifier: str) -> MemoryScope:
   254	        grant = configuration.get("clients", {}).get(identifier)
   255	        if not configuration.get("sharing_enabled", False) or grant is None or not grant["enabled"]:
   256	            raise MemoryUnavailable("This memory connection is disabled or revoked")
   257	        principal = f"client:{identifier}"
   258	        policy = MemoryPolicy({"version": 1, "principal": configuration["principal"],
   259	                               "accounts": {f"mcp:{identifier}": principal},
   260	                               "destinations": {f"mcp:{identifier}": {
   261	                                   "visibility": "private", "participants": [principal],
   262	                                   "read": grant.get("read", ["project"]), "write": grant.get("write", []),
   263	                                   "projects": grant.get("projects", []), "model_routes": [grant.get("model_route", "unknown")],
   264	                                   "proposals": grant.get("proposals", []),
   265	                               }}})
   266	        return policy.resolve(SessionContext("mcp", identifier, identifier, "private", (principal,),
   267	                                             grant.get("model_route", "unknown"), ""))
   268	
   269	    def call_client(self, identifier: str, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
   270	        try:
   271	            configuration = self.configuration.load()
   272	            scope = self.client_scope(configuration, identifier)
   273	        except (MemoryUnavailable, ValueError, OSError) as error:
   274	            return {"status": "rejected", "reason": str(error)}
   275	        return self._call(configuration, scope, name, arguments)
   276	
   277	    def call_context(self, context: SessionContext, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
   278	        try:
   279	            configuration = self.configuration.load()
   280	            scope = MemoryPolicy(configuration).resolve(context)
   281	        except (MemoryUnavailable, ValueError, OSError) as error:
   282	            return {"status": "unavailable", "reason": str(error)}
   283	        return self._call(configuration, scope, name, arguments, source_session=context.session_id)
   284	
   285	    def call(self, scope: MemoryScope, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
   286	        try:
   287	            configuration = self.configuration.load()
   288	        except (MemoryUnavailable, ValueError, OSError) as error:
   289	            return {"status": "unavailable", "reason": str(error)}
   290	        return self._call(configuration, scope, name, arguments)
   291	
   292	    def _call(self, configuration: dict[str, Any], scope: MemoryScope, name: str, arguments: dict[str, Any],
   293	              *, source_session: str = '') -> dict[str, Any]:
   294	        try:
   295	            _validate_arguments(name, arguments)
   296	        except ValueError as error:
   297	            return {"status": "rejected", "reason": str(error)}
   298	        try:
   299	            memory = NativeMemory(Path(configuration["root"]))
   300	            if not scope.read and not scope.write and not scope.proposals:
   301	                return {"status": "rejected", "reason": scope.reason or "This context has no memory grant"}
   302	            if name == "lifeos_memory_propose":
   303	                result = memory.native_add(scope, arguments["proposal"], request_id=arguments["request_id"], project="",
   304	                                           source_session=source_session)
   305	                return result.get("receipt", {"status":"rejected", "reason":result.get("message", "Native proposal failed")})
   306	            if name == "lifeos_memory_proposals":
   307	                return {"status":"ok", "results":memory.review_proposals(scope)}
   308	            if name == "lifeos_memory_decide_proposal":
   309	                return memory.decide_proposal(scope, **arguments)
   310	            if name == "lifeos_memory_search":
   311	                return {"status": "ok", "results": memory.recall(scope, **arguments)}
   312	            if name == "lifeos_memory_get":
   313	                return memory.get(scope, arguments["reference"])
   314	            if name == "lifeos_memory_remember":
   315	                return memory.remember(scope, **arguments, source={'kind': 'explicit', 'session': source_session})
   316	            if name == "lifeos_memory_correct":
   317	                return memory.correct(scope, **arguments)
   318	            if name == "lifeos_memory_forget":
   319	                return memory.forget(scope, **arguments)
   320	            memory._boundary()
   321	            with memory._transaction() as connection:
   322	                connection.execute("SELECT id FROM records LIMIT 1").fetchone()
   323	            memory._native("rank", query="memory health", corpus=[], limit=1)
   324	            return {"status": "ok", "owner": "LifeOS", "read": list(scope.read), "write": list(scope.write),
   325	                    "projects": list(scope.projects), "sharing_enabled": configuration.get("sharing_enabled", False)}
   326	        except (MemoryUnavailable, ValueError, OSError, sqlite3.Error, subprocess.TimeoutExpired) as error:
   327	            return {"status": "unavailable", "reason": str(error)}
