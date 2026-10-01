     1	# ABOUTME: Governs native LifeOS memory writes and reads with stable references and permissions.
     2	# ABOUTME: Keeps operation metadata separate from authoritative native fact contents.
     3	
     4	from __future__ import annotations
     5	
     6	from contextlib import contextmanager
     7	from datetime import datetime, timezone
     8	import hashlib
     9	import json
    10	import os
    11	from pathlib import Path
    12	import re
    13	import shutil
    14	import sqlite3
    15	import subprocess
    16	from typing import Any, Callable
    17	from uuid import uuid4
    18	
    19	from .memory_policy import CATEGORIES, MemoryScope
    20	from .memory_transaction import MemoryTransaction
    21	
    22	
    23	SCHEMA_VERSION = 3
    24	HOT_FILES = {
    25	    "principal": "LIFEOS/USER/PRINCIPAL/PRINCIPAL_MEMORY.md",
    26	    "assistant": "LIFEOS/USER/DIGITAL_ASSISTANT/DA_MEMORY.md",
    27	}
    28	HOT_WRITE_LOG = 'LIFEOS/MEMORY/OBSERVABILITY/memory-writes.jsonl'
    29	
    30	
    31	def _digest(text: str) -> str:
    32	    return hashlib.sha256(text.encode()).hexdigest()
    33	
    34	
    35	def _claim_words(text: str) -> list[str]:
    36	    body = re.sub(r"^(NAME|ROLE|RELATION|PREFERENCE|RULE):\s*", "", text)
    37	    body = re.sub(r"\s+~(?:explicit|deduced|inferred)\s*$", "", body)
    38	    return re.findall(r"\w+", body.casefold())
    39	
    40	
    41	def _claim_digest(text: str) -> str:
    42	    return _digest(" ".join(_claim_words(text)))
    43	
    44	
    45	def _now() -> str:
    46	    return datetime.now(timezone.utc).isoformat()
    47	
    48	
    49	class MemoryUnavailable(RuntimeError):
    50	    pass
    51	
    52	
    53	class MemoryConflict(MemoryUnavailable):
    54	    pass
    55	
    56	
    57	class NativeMemory:
    58	    def __init__(self, installed_root: Path, *, bun: str | None = None):
    59	        self.root = Path(installed_root).absolute()
    60	        self.bun = bun or shutil.which("bun") or "bun"
    61	        self.database = self.root / "LIFEOS/MEMORY/STATE/memory-access.sqlite"
    62	        self.worker = Path(__file__).with_name("memory_native.ts")
    63	        self.transaction = MemoryTransaction(self.database.parent, self._path)
    64	
    65	    def _boundary(self) -> None:
    66	        user = self.root.parent / ".config/LIFEOS/USER"
    67	        if not user.is_dir():
    68	            raise MemoryUnavailable("The native USER_DATA boundary is missing")
    69	        for name in ("USER", "MEMORY"):
    70	            path = self.root / "LIFEOS" / name
    71	            if not path.is_symlink() or not path.is_dir() or not path.resolve().is_relative_to(user.resolve()):
    72	                raise MemoryUnavailable(f"LifeOS {name} is outside the physical USER_DATA boundary")
    73	        if not (self.root / "LIFEOS/TOOLS/MemorySystem.ts").is_file():
    74	            raise MemoryUnavailable("The native LifeOS memory tools are unavailable")
    75	
    76	    def _connect(self) -> sqlite3.Connection:
    77	        self._boundary()
    78	        self.database.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    79	        connection = sqlite3.connect(self.database, timeout=30, isolation_level=None)
    80	        connection.row_factory = sqlite3.Row
    81	        try:
    82	            connection.execute("PRAGMA busy_timeout=30000")
    83	            connection.execute("BEGIN IMMEDIATE")
    84	            version = connection.execute("PRAGMA user_version").fetchone()[0]
    85	            if version not in (0, SCHEMA_VERSION):
    86	                raise MemoryUnavailable("The memory metadata schema is unsupported")
    87	            connection.executescript("""
    88	                CREATE TABLE IF NOT EXISTS records (
    89	                    id TEXT PRIMARY KEY, path TEXT NOT NULL, category TEXT NOT NULL, project TEXT NOT NULL,
    90	                    digest TEXT NOT NULL, chars INTEGER NOT NULL, position INTEGER NOT NULL,
    91	                    revision INTEGER NOT NULL, status TEXT NOT NULL, writer TEXT NOT NULL,
    92	                    source_session TEXT NOT NULL, source_kind TEXT NOT NULL, updated TEXT NOT NULL,
    93	                    claim_digest TEXT NOT NULL, claim_words INTEGER NOT NULL
    94	                );
    95	                CREATE TABLE IF NOT EXISTS proposals (
    96	                    id TEXT PRIMARY KEY, path TEXT NOT NULL, target TEXT NOT NULL, target_digest TEXT NOT NULL, digest TEXT NOT NULL,
    97	                    revision INTEGER NOT NULL, status TEXT NOT NULL, writer TEXT NOT NULL,
    98	                    source_session TEXT NOT NULL, updated TEXT NOT NULL
    99	                );
   100	                CREATE TABLE IF NOT EXISTS operations (
   101	                    writer TEXT NOT NULL, request_id TEXT NOT NULL, payload_digest TEXT NOT NULL,
   102	                    receipt TEXT NOT NULL, PRIMARY KEY(writer, request_id)
   103	                );
   104	            """)
   105	            connection.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
   106	            connection.commit()
   107	            os.chmod(self.database, 0o600)
   108	            return connection
   109	        except BaseException:
   110	            connection.close()
   111	            raise
   112	
   113	    @contextmanager
   114	    def _transaction(self):
   115	        self._boundary()
   116	        with self.transaction.lock():
   117	            connection = self._connect()
   118	            try:
   119	                self.transaction.recover(connection)
   120	                connection.execute("BEGIN IMMEDIATE")
   121	                yield connection
   122	                connection.commit()
   123	                self.transaction.finish()
   124	            except BaseException:
   125	                connection.rollback()
   126	                raise
   127	            finally:
   128	                connection.close()
   129	
   130	    def _native(self, action: str, **values: Any) -> dict[str, Any]:
   131	        environment = dict(os.environ)
   132	        environment["HOME"] = str(self.root.parent)
   133	        environment["LIFEOS_DIR"] = str(self.root / "LIFEOS")
   134	        environment["LIFEOS_CONFIG_DIR"] = str(self.root / "LIFEOS/USER/CONFIG")
   135	        environment.pop("LIFEOS_MEMORY_PUBLICATION_JOURNAL", None)
   136	        if self.transaction.inherited_descriptors():
   137	            environment["LIFEOS_MEMORY_PUBLICATION_JOURNAL"] = str(self.transaction.journal)
   138	        environment["LIFEOS_MEMORY_INTERNAL"] = "1"
   139	        environment["BUN_CONFIG_NO_AUTO_INSTALL"] = "1"
   140	        result = subprocess.run([self.bun, "--no-install", str(self.worker), str(self.root)],
   141	                                input=json.dumps({"action": action, **values}), text=True,
   142	                                capture_output=True, timeout=30, env=environment, cwd=self.root,
   143	                                pass_fds=self.transaction.inherited_descriptors())
   144	        if result.returncode:
   145	            raise MemoryUnavailable("Native memory operation failed: " + result.stderr.strip()[:500])
   146	        try:
   147	            response = json.loads(result.stdout)
   148	        except ValueError as error:
   149	            raise MemoryUnavailable("Native memory returned an invalid response") from error
   150	        if not isinstance(response, dict):
   151	            raise MemoryUnavailable("Native memory returned an invalid result")
   152	        return response
   153	
   154	    def _path(self, name: str) -> Path:
   155	        relative = Path(name)
   156	        if relative.is_absolute() or ".." in relative.parts or not name.startswith(("LIFEOS/USER/", "LIFEOS/MEMORY/")):
   157	            raise MemoryUnavailable("Invalid native memory reference")
   158	        path = self.root / relative
   159	        user = (self.root.parent / ".config/LIFEOS/USER").resolve()
   160	        if not path.resolve().is_relative_to(user):
   161	            raise MemoryUnavailable("Native memory reference leaves the user boundary")
   162	        return path
   163	
   164	    @staticmethod
   165	    def _allowed(scope: MemoryScope, record: sqlite3.Row, *, write: bool = False) -> bool:
   166	        permissions = scope.write if write else scope.read
   167	        if record["category"] not in permissions:
   168	            return False
   169	        if record["path"].startswith(("LIFEOS/MEMORY/KNOWLEDGE/People/", "LIFEOS/MEMORY/KNOWLEDGE/Companies/")) and "principal" not in permissions:
   170	            return False
   171	        if record['category'] == 'project' and not record['project'] and not CATEGORIES <= set(permissions):
   172	            return False
   173	        return record["category"] != "project" or "*" in scope.projects or record["project"] in scope.projects
   174	
   175	    def _content(self, record: sqlite3.Row, hot_entries: dict[Path, list[str]] | None = None) -> str:
   176	        path = self._path(record["path"])
   177	        if not path.is_file():
   178	            raise MemoryUnavailable("The referenced native memory file is missing")
   179	        text = path.read_text(encoding="utf-8")
   180	        length = record["chars"]
   181	        position = record["position"]
   182	        candidate = text[position:position + length]
   183	        if record["category"] == "project":
   184	            boundary = re.search(r"\n## Appended \d{4}-\d{2}-\d{2}T[^\n]+Z\n<!-- source_session: [^\n]* -->\n", text[position:])
   185	            end = position + boundary.start() if boundary else len(text)
   186	            section = text[position:end].rstrip("\r\n")
   187	            if section == candidate and _digest(candidate) == record["digest"]:
   188	                return candidate
   189	        if record["category"] != "project":
   190	            if hot_entries is None:
   191	                entries = self._native("read_hot", path=str(path)).get("entries", [])
   192	            else:
   193	                if path not in hot_entries:
   194	                    hot_entries[path] = self._native("read_hot", path=str(path)).get("entries", [])
   195	                entries = hot_entries[path]
   196	            matches = [entry for entry in entries if _digest(entry) == record["digest"]]
   197	            if len(matches) == 1:
   198	                return matches[0]
   199	        raise MemoryConflict("The referenced fact changed outside its recorded revision")
   200	
   201	    def _validate(self, item: dict[str, Any], content: str, category: str) -> str | None:
   202	        checked = self._native("validate", item=item)
   203	        if not checked.get("ok"):
   204	            return checked.get("message", "Native validation rejected the fact")
   205	        if checked["item"] != item:
   206	            return "Native validation changed the requested fact or metadata"
   207	        if category != "project" and (len(content.split(": ", 1)[-1].encode("utf-16-le")) // 2 > 256 or "\n" in content or "\r" in content):
   208	            return "A native hot-memory entry requires one line of at most 256 characters"
   209	        return None
   210	
   211	    @staticmethod
   212	    def _blocked(connection: sqlite3.Connection, content: str) -> bool:
   213	        return connection.execute("""SELECT id FROM records AS retained WHERE claim_digest=? AND status IN ('forgotten','superseded')
   214	                                  AND NOT EXISTS (SELECT 1 FROM records AS current WHERE current.status='active'
   215	                                  AND current.claim_digest=retained.claim_digest AND current.category=retained.category
   216	                                  AND current.project=retained.project)""",
   217	                                  (_claim_digest(content),)).fetchone() is not None
   218	
   219	    def _archive_write(self, connection: sqlite3.Connection, item: dict[str, Any]) -> dict[str, Any]:
   220	        path = Path(self._native("route", item=item)["path"])
   221	        relative = path.relative_to(self.root).as_posix()
   222	        path = self._path(relative)
   223	        rows = connection.execute("SELECT * FROM records WHERE path=? AND status='active'", (relative,)).fetchall()
   224	        old_text = path.read_text(encoding="utf-8") if path.exists() else ""
   225	        for row in rows:
   226	            self._content(row)
   227	        result = self._native("add", item=item)
   228	        if not result.get("ok"):
   229	            return result
   230	        if Path(result["path"]) != path:
   231	            raise MemoryUnavailable("Native publication changed its declared archive destination")
   232	        if rows:
   233	            text = path.read_text(encoding="utf-8")
   234	            old_frontmatter = re.match(r"^---\n.*?\n---\n", old_text, re.DOTALL)
   235	            frontmatter = re.match(r"^---\n.*?\n---\n", text, re.DOTALL)
   236	            if old_frontmatter is None or frontmatter is None or not text[frontmatter.end():].startswith(old_text[old_frontmatter.end():].rstrip("\r\n")):
   237	                raise MemoryUnavailable("Native archive publication changed an earlier section; recovery is required")
   238	            delta = frontmatter.end() - old_frontmatter.end()
   239	            for row in rows:
   240	                connection.execute("UPDATE records SET position=position+? WHERE id=?", (delta, row["id"]))
   241	                updated = connection.execute("SELECT * FROM records WHERE id=?", (row["id"],)).fetchone()
   242	                self._content(updated)
   243	        return result
   244	
   245	    @staticmethod
   246	    def _archive_item(path: Path, content: str, source_session: str) -> dict[str, Any]:
   247	        common = {"content": content, "source_session": source_session or "none"}
   248	        if 'LEARNING' in path.parts:
   249	            return {**common, 'type':'knowledge', 'entity_type':'research', 'name':path.stem}
   250	        if path.parent.name == "Ideas":
   251	            return {**common, "type": "idea", "title": path.stem}
   252	        entity = {"People": "person", "Companies": "company", "Research": "research"}.get(path.parent.name)
   253	        if entity is None:
   254	            raise MemoryUnavailable("The archive reference has no supported native routing type")
   255	        return {**common, "type": "knowledge", "entity_type": entity, "name": path.stem}
   256	
   257	    @staticmethod
   258	    def _private_entity(path: str) -> bool:
   259	        return path.startswith(("LIFEOS/MEMORY/KNOWLEDGE/People/", "LIFEOS/MEMORY/KNOWLEDGE/Companies/"))
   260	
   261	    def _duplicate(self, connection: sqlite3.Connection, scope: MemoryScope, content: str,
   262	                   category: str, project: str, destination: str) -> sqlite3.Row | None:
   263	        candidates = connection.execute("SELECT * FROM records WHERE digest=? AND category=? AND project=? AND status='active'",
   264	                                        (_digest(content), category, project)).fetchall()
   265	        for candidate in candidates:
   266	            if self._allowed(scope, candidate, write=True) and self._private_entity(candidate["path"]) == self._private_entity(destination):
   267	                self._content(candidate)
   268	                return candidate
   269	        return None
   270	
   271	    def _record(self, connection: sqlite3.Connection, scope: MemoryScope, path: Path,
   272	                content: str, category: str, project: str, source: dict[str, str]) -> dict[str, Any]:
   273	        relative = path.relative_to(self.root).as_posix()
   274	        text = self._path(relative).read_text(encoding="utf-8")
   275	        if category == "project":
   276	            position = len(text.rstrip("\r\n")) - len(content)
   277	        else:
   278	            start = text.index("<!-- BEGIN ENTRIES -->") + len("<!-- BEGIN ENTRIES -->")
   279	            position = text.find(content, start, text.index("<!-- END ENTRIES -->"))
   280	        if position < 0 or text[position:position + len(content)] != content:
   281	            raise MemoryUnavailable("The native writer did not save the requested fact")
   282	        identifier = uuid4().hex
   283	        connection.execute("INSERT INTO records VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
   284	            identifier, relative, category, project, _digest(content), len(content), position,
   285	            1, "active", scope.writer, source.get("session", ""), source.get("kind", "explicit"), _now(), _claim_digest(content), len(_claim_words(content)),
   286	        ))
   287	        return {"id": identifier, "revision": 1}
   288	
   289	    def _operation(self, scope: MemoryScope, request_id: str, payload: dict[str, Any],
   290	                   callback: Callable[[sqlite3.Connection], dict[str, Any]]) -> dict[str, Any]:
   291	        if not isinstance(request_id, str) or not request_id or len(request_id) > 256:
   292	            return {"status": "rejected", "reason": "A bounded request identifier is required"}
   293	        payload_digest = _digest(json.dumps(payload, sort_keys=True))
   294	        reserved = False
   295	        try:
   296	            with self._transaction() as connection:
   297	                prior = connection.execute("SELECT * FROM operations WHERE writer=? AND request_id=?",
   298	                                           (scope.writer, request_id)).fetchone()
   299	                if prior is not None:
   300	                    if prior["payload_digest"] != payload_digest:
   301	                        return {"status": "conflict", "reason": "This request identifier names another operation"}
   302	                    return json.loads(prior["receipt"])
   303	                unknown = {"status": "unknown", "reason": "The operation outcome needs recovery before retry",
   304	                           "writer": scope.writer, "request_id": request_id}
   305	                paths = self._publication_paths(connection, scope, payload)
   306	                self.transaction.prepare(scope.writer, request_id, paths)
   307	                connection.execute("INSERT INTO operations VALUES (?,?,?,?)",
   308	                                   (scope.writer, request_id, payload_digest, json.dumps(unknown)))
   309	                connection.commit()
   310	                reserved = True
   311	                connection.execute("BEGIN IMMEDIATE")
   312	                try:
   313	                    receipt = callback(connection)
   314	                except MemoryConflict as error:
   315	                    receipt = {"status": "conflict", "reason": str(error)}
   316	                receipt.setdefault("writer", scope.writer)
   317	                receipt.setdefault("request_id", request_id)
   318	                connection.execute("UPDATE operations SET receipt=? WHERE writer=? AND request_id=?",
   319	                                   (json.dumps(receipt), scope.writer, request_id))
   320	                self.transaction.flush_publication()
   321	                return receipt
   322	        except MemoryConflict as error:
   323	            return {"status": "conflict", "reason": str(error), "writer": scope.writer, "request_id": request_id}
   324	        except (MemoryUnavailable, OSError, sqlite3.Error, subprocess.TimeoutExpired) as error:
   325	            return {"status": "unknown" if reserved else "rejected",
   326	                    "reason": str(error), "writer": scope.writer, "request_id": request_id}
   327	
   328	    def _publication_paths(self, connection: sqlite3.Connection, scope: MemoryScope,
   329	                           payload: dict[str, Any]) -> list[str]:
   330	        if payload["operation"] == "proposal_decision":
   331	            from .memory_proposals import _permitted
   332	            permission = 'auto_apply' if payload['decision'] == 'auto_apply' else 'approve'
   333	            if not _permitted(scope, permission):
   334	                return []
   335	            row = connection.execute("SELECT * FROM proposals WHERE id=?", (payload['reference']['id'],)).fetchone()
   336	            if row is None or row['status'] != 'pending' or row['revision'] != payload['reference']['revision']:
   337	                return []
   338	            return [row['path'], row['target'], "LIFEOS/MEMORY/OBSERVABILITY/identity-proposals.jsonl"]
   339	        if payload["operation"] == "native_proposal":
   340	            return ["LIFEOS/MEMORY/OBSERVABILITY/pending-proposals.jsonl"]
   341	        if payload["operation"] == "native_set":
   342	            return self._hot_publication_paths(payload['category'])
   343	        if payload["operation"] in ("remember", "native_add"):
   344	            checked = self._native("validate", item=payload["item"])
   345	            if not checked.get("ok") or checked["item"] != payload["item"]:
   346	                return []
   347	            result = self._native("route", item=checked["item"])
   348	            relative = Path(result["path"]).relative_to(self.root).as_posix()
   349	            category = next((category for category, path in HOT_FILES.items() if path == relative), None)
   350	            return self._hot_publication_paths(category) if category else [relative]
   351	        reference = payload.get("reference")
   352	        if not isinstance(reference, dict) or not isinstance(reference.get("id"), str):
   353	            return []
   354	        row = self._target(connection, scope, reference)
   355	        if row is None or row['status'] != 'active' or row['revision'] != reference['revision']:
   356	            return []
   357	        if row['category'] in HOT_FILES:
   358	            if row['category'] not in scope.read:
   359	                return []
   360	            # Refuse drift before the recovery journal copies the whole source file.
   361	            self._hot_snapshot(connection, row['category'])
   362	        paths = self._hot_publication_paths(row['category']) if row['category'] in HOT_FILES else [row['path']]
   363	        if payload['operation'] == 'correct' and row['category'] == 'project' and isinstance(payload['content'],str):
   364	            item = self._archive_item(self._path(row['path']),payload['content'],row['source_session'])
   365	            checked = self._native('validate',item=item)
   366	            if checked.get('ok') and checked.get('item') == item:
   367	                target = Path(self._native('route',item=item)['path']).relative_to(self.root).as_posix()
   368	                self._path(target)
   369	                paths.append(target)
   370	        return paths
   371	
   372	    def _hot_publication_paths(self, category: str) -> list[str]:
   373	        log = self._path(HOT_WRITE_LOG)
   374	        expected = self.root.parent / '.config/LIFEOS/USER/MEMORY/OBSERVABILITY/memory-writes.jsonl'
   375	        if log.resolve() != expected.absolute() or (log.exists() and not log.is_file()):
   376	            raise MemoryUnavailable('The native hot-write log changes its permitted physical path')
   377	        # Native append evidence must recover with the fact publication it describes.
   378	        return [HOT_FILES[category], HOT_WRITE_LOG]
   379	
   380	    @staticmethod
   381	    def _native_receipt(receipt: dict[str, Any], *, category: str, path: Path) -> dict[str, Any]:
   382	        if receipt["status"] not in ("committed", "unchanged"):
   383	            return {"ok": False, "code": "EINVAL_ITEM", "message": receipt.get("reason", "Memory operation did not commit"),
   384	                    "receipt": receipt}
   385	        return {"ok": True, "type": "memory" if category != "project" else "knowledge", "path": str(path),
   386	                "detail": receipt.get("detail", {}), "receipt": receipt}
   387	
   388	    def _hot_snapshot(self, connection: sqlite3.Connection, category: str) -> dict[str, Any]:
   389	        path = self._path(HOT_FILES[category])
   390	        snapshot = self._native("read_hot", path=str(path))
   391	        if "entries" not in snapshot or snapshot.get("dropped_invalid"):
   392	            raise MemoryUnavailable("Native hot memory needs repair before governed curation")
   393	        indexed = connection.execute("SELECT * FROM records WHERE category=? AND status='active'", (category,)).fetchall()
   394	        entries = snapshot["entries"]
   395	        if sorted(_digest(entry) for entry in entries) != sorted(row["digest"] for row in indexed):
   396	            raise MemoryConflict("Native hot memory changed outside governed publication; review it before adoption")
   397	        return {**snapshot, "revision": _digest(path.read_text(encoding="utf-8"))}
   398	
   399	    def read_hot(self, scope: MemoryScope, category: str) -> dict[str, Any]:
   400	        if category not in HOT_FILES or category not in scope.read:
   401	            return {"ok": False, "code": "EINVAL_PATH", "message": "This hot-memory file has no read grant"}
   402	        with self._transaction() as connection:
   403	            return self._hot_snapshot(connection, category)
   404	
   405	    def _curate_hot(self, connection: sqlite3.Connection, scope: MemoryScope, category: str,
   406	                    entries: list[str], observed_revision: str, *, allow_drastic: bool = False,
   407	                    source: dict[str, str] | None = None, native_writer: str | None = None) -> dict[str, Any]:
   408	        current = self._hot_snapshot(connection, category)
   409	        if not observed_revision or observed_revision != current["revision"]:
   410	            return {"status": "conflict", "reason": "The native memory revision changed after the reviewer read it"}
   411	        desired = list(dict.fromkeys(entries))
   412	        prior = connection.execute("SELECT * FROM records WHERE category=? AND status='active'", (category,)).fetchall()
   413	        by_digest = {row["digest"]: row for row in prior}
   414	        by_claim: dict[str, list[sqlite3.Row]] = {}
   415	        for row in prior:
   416	            by_claim.setdefault(row["claim_digest"], []).append(row)
   417	        assignments = []
   418	        preserved = set()
   419	        desired_digests = {_digest(entry) for entry in desired}
   420	        for entry in desired:
   421	            item = {"type": "memory", "actor": category, "content": entry}
   422	            if not re.match(r"^(NAME|ROLE|RELATION|PREFERENCE|RULE): ", entry):
   423	                return {"status": "rejected", "reason": "Every native hot entry requires a recognized prefix"}
   424	            invalid = self._validate(item, entry, category)
   425	            if invalid:
   426	                return {"status": "rejected", "reason": invalid}
   427	            if entry not in current["entries"] and self._blocked(connection, entry):
   428	                return {"status": "rejected", "reason": "This fact needs explicit reactivation after correction or forgetting"}
   429	            row = by_digest.get(_digest(entry))
   430	            equivalent = by_claim.get(_claim_digest(entry), [])
   431	            if row is None and len(equivalent) == 1 and equivalent[0]["digest"] not in desired_digests:
   432	                row = equivalent[0]
   433	            if row is not None:
   434	                if row["id"] in preserved:
   435	                    return {"status": "conflict", "reason": "Curation maps several replacements to one native fact"}
   436	                preserved.add(row["id"])
   437	            assignments.append(row)
   438	        path = self._path(HOT_FILES[category])
   439	        # Native summaries recognize the addition label; registry authorship stays in scope.writer.
   440	        result = self._native("set_hot", path=str(path), entries=desired,
   441	                              writer=native_writer or scope.writer, allowDrastic=allow_drastic)
   442	        if not result.get("ok"):
   443	            return {"status": "rejected", "reason": result.get("message", "Native curation rejected the update")}
   444	        if result.get("dropped_malformed") or result.get("dropped_overlength"):
   445	            raise MemoryUnavailable("Native curation dropped submitted facts; publication requires recovery")
   446	        actual = self._native("read_hot", path=str(path)).get("entries")
   447	        if actual != desired:
   448	            raise MemoryUnavailable("Native curation did not publish the complete requested snapshot")
   449	        references = []
   450	        for row in prior:
   451	            if row["id"] not in preserved:
   452	                connection.execute("UPDATE records SET status='superseded',revision=revision+1,updated=? WHERE id=?", (_now(), row["id"]))
   453	        for entry, row in zip(desired, assignments):
   454	            if row is None:
   455	                references.append(self._record(connection, scope, path, entry, category, "",
   456	                                               source if source is not None else {"kind": "native-curation"}))
   457	            elif row["digest"] == _digest(entry):
   458	                references.append({"id": row["id"], "revision": row["revision"]})
   459	            else:
   460	                text = path.read_text(encoding="utf-8")
   461	                start = text.index("<!-- BEGIN ENTRIES -->") + len("<!-- BEGIN ENTRIES -->")
   462	                position = text.find(entry, start, text.index("<!-- END ENTRIES -->"))
   463	                if position < 0:
   464	                    raise MemoryUnavailable("Native curation did not save the replacement fact")
   465	                connection.execute("UPDATE records SET digest=?,chars=?,position=?,revision=revision+1,updated=? WHERE id=?",
   466	                                   (_digest(entry), len(entry), position, _now(), row["id"]))
   467	                references.append({"id": row["id"], "revision": row["revision"] + 1})
   468	        return {"status": "committed", "references": references, "detail": result}
   469	
   470	    def native_set(self, scope: MemoryScope, category: str, entries: list[str], request_id: str,
   471	                   observed_revision: str, *, allow_drastic: bool = False, source_session: str = '') -> dict[str, Any]:
   472	        if category not in HOT_FILES or category not in scope.read or category not in scope.write:
   473	            return {"ok": False, "code": "EINVAL_PATH", "message": "Native curation needs read and write grants for the whole file"}
   474	        if not isinstance(entries, list) or any(not isinstance(entry, str) for entry in entries) or type(allow_drastic) is not bool:
   475	            return {"ok": False, "code": "EINVAL_ITEM", "message": "Native curation requires a validated entry list"}
   476	        payload = {"operation": "native_set", "category": category, "entries": entries,
   477	                   "observed_revision": observed_revision, "allow_drastic": allow_drastic, 'source_session': source_session}
   478	        receipt = self._operation(scope, request_id, payload, lambda connection:
   479	                                  self._curate_hot(connection, scope, category, entries, observed_revision, allow_drastic=allow_drastic,
   480	                                                   source={'kind': 'native-curation', 'session': source_session}))
   481	        result = self._native_receipt(receipt, category=category, path=self._path(HOT_FILES[category]))
   482	        return {**receipt["detail"], "receipt": receipt} if result["ok"] else {**result, "code": "EWRITE_FAILED"}
   483	
   484	    def review_proposals(self, scope: MemoryScope, *, include_resolved: bool = False) -> list[dict[str, Any]]:
   485	        from .memory_proposals import review
   486	        return review(self, scope, include_resolved=include_resolved)
   487	
   488	    def decide_proposal(self, scope: MemoryScope, reference: dict[str, Any], decision: str,
   489	                        request_id: str, *, content: str = "", note: str = "",
   490	                        confidence_threshold: float | None = None) -> dict[str, Any]:
   491	        from .memory_proposals import decide
   492	        return decide(self, scope, reference, decision, request_id, content=content, note=note,
   493	                      confidence_threshold=confidence_threshold)
   494	
   495	    def proposal_decision_row(self, scope: MemoryScope, reference: dict[str, Any]) -> dict[str, Any]:
   496	        from .memory_proposals import decision_row
   497	        return decision_row(self, scope, reference)
   498	
   499	    def preview_adoption(self, scope: MemoryScope) -> dict[str, Any]:
   500	        from .memory_adoption import preview
   501	        return preview(self, scope)
   502	
   503	    def adopt(self, scope: MemoryScope, signature: str, projects: dict[str, str], request_id: str) -> dict[str, Any]:
   504	        from .memory_adoption import adopt
   505	        return adopt(self, scope, signature, projects, request_id)
   506	
   507	    def native_add(self, scope: MemoryScope, item: dict[str, Any], *, request_id: str, project: str,
   508	                   observed_revision: str = "", source_session: str = "") -> dict[str, Any]:
   509	        if not isinstance(item, dict):
   510	            return {"ok": False, "code": "EINVAL_ITEM", "message": "A native memory item is required"}
   511	        if item.get("type") == "proposal":
   512	            from .memory_proposals import enqueue
   513	            return enqueue(self, scope, item, request_id, source_session)
   514	        category = item.get("actor") if item.get("type") == "memory" else "project"
   515	        if not isinstance(category, str) or item.get("type") not in ("memory", "knowledge", "idea") or category not in CATEGORIES:
   516	            return {"ok": False, "code": "EINVAL_ITEM", "message": "This native memory item needs a supported governed operation"}
   517	        if category not in scope.write or (category == "project" and (not project or ("*" not in scope.projects and project not in scope.projects))):
   518	            return {"ok": False, "code": "EINVAL_ITEM", "message": "This native memory item has no write grant"}
   519	        if category != "project" and category not in scope.read:
   520	            return {"ok": False, "code": "EINVAL_ITEM", "message": "Native curation requires a read grant for the current hot file"}
   521	        if item.get("type") == "knowledge" and item.get("entity_type") in ("person", "company") and "principal" not in scope.write:
   522	            return {"ok": False, "code": "EINVAL_ITEM", "message": "Native private entity notes need principal write permission"}
   523	        checked = self._native("validate", item=item)
   524	        if not checked.get("ok") or checked["item"] != item:
   525	            return {"ok": False, "code": "EINVAL_ITEM", "message": checked.get("message", "Native validation changed the requested item")}
   526	        if category != "project" and item.get("op") == "set":
   527	            result = self.native_set(scope, category, item.get("entries"), request_id, observed_revision,
   528	                                     source_session=source_session)
   529	            if not result.get("ok"):
   530	                return result
   531	            return {"ok": True, "type": "memory", "path": str(self._path(HOT_FILES[category])), "detail": result, "receipt": result["receipt"]}
   532	        project = project if category == "project" else ""
   533	        content = item.get("content")
   534	        if not isinstance(content, str) or not content.strip():
   535	            return {"ok": False, "code": "EINVAL_ITEM", "message": "A native fact requires content"}
   536	        def save(connection):
   537	            invalid = self._validate(item, content, category)
   538	            if invalid:
   539	                return {"status": "rejected", "reason": invalid}
   540	            if category != "project":
   541	                snapshot = self._hot_snapshot(connection, category)
   542	                return self._curate_hot(connection, scope, category, [*snapshot["entries"], content], snapshot["revision"],
   543	                                        native_writer='MemorySystem.add', source={'kind': 'native', 'session': source_session})
   544	            if self._blocked(connection, content):
   545	                return {"status": "rejected", "reason": "This fact needs explicit reactivation after correction or forgetting"}
   546	            result = self._archive_write(connection, item)
   547	            if not result.get("ok"):
   548	                return {"status": "rejected", "reason": result.get("message", "Native memory rejected the fact")}
   549	            reference = self._record(connection, scope, Path(result["path"]), content, category, project,
   550	                                     {"kind": "native", "session": source_session})
   551	            return {"status": "committed", "reference": reference, "detail": result["detail"]}
   552	        receipt = self._operation(scope, request_id, {"operation": "native_add", "item": item, "project": project,
   553	                                                    "source_session": source_session}, save)
   554	        path = self._path(HOT_FILES[category]) if category in HOT_FILES else self.root / "LIFEOS/MEMORY"
   555	        result = self._native_receipt(receipt, category=category, path=path)
   556	        if result["ok"] and category == "project":
   557	            result["type"] = item["type"]
   558	            with self._transaction() as connection:
   559	                row = connection.execute("SELECT path FROM records WHERE id=?", (receipt["reference"]["id"],)).fetchone()
   560	                result["path"] = str(self._path(row["path"]))
   561	        return result
   562	
   563	    def remember(self, scope: MemoryScope, *, category: str, content: str, title: str, project: str,
   564	                 request_id: str, source: dict[str, str] | None = None) -> dict[str, Any]:
   565	        source = source or {"kind": "explicit", "session": ""}
   566	        if category not in CATEGORIES or category not in scope.write or not isinstance(content, str) or not content.strip():
   567	            return {"status": "rejected", "reason": "The fact or write permission is invalid"}
   568	        if category == "project" and (not project or ("*" not in scope.projects and project not in scope.projects)):
   569	            return {"status": "rejected", "reason": "The project has no write grant"}
   570	        if category in HOT_FILES and category not in scope.read:
   571	            return {"status": "rejected", "reason": "Hot-memory publication requires a read grant for the current file"}
   572	        if category != "project":
   573	            project = ""
   574	        content = content.strip()
   575	        if category != "project" and not re.match(r"^(NAME|ROLE|RELATION|PREFERENCE|RULE): ", content):
   576	            content = ("PREFERENCE: " if category == "principal" else "RULE: ") + content
   577	        item = ({"type": "knowledge", "entity_type": "research", "name": title, "content": content,
   578	                 "source_session": source.get("session", "") or "none"} if category == "project" else
   579	                {"type": "memory", "actor": "principal" if category == "principal" else "assistant", "content": content})
   580	
   581	        def save(connection):
   582	            invalid = self._validate(item, content, category)
   583	            if invalid:
   584	                return {"status": "rejected", "reason": invalid}
   585	            snapshot = self._hot_snapshot(connection, category) if category in HOT_FILES else None
   586	            if self._blocked(connection, content):
   587	                return {"status": "rejected", "reason": "This fact needs explicit reactivation after correction or forgetting"}
   588	            destination = Path(self._native("route", item=item)["path"]).relative_to(self.root).as_posix()
   589	            existing = self._duplicate(connection, scope, content, category, project, destination)
   590	            if existing:
   591	                return {"status": "unchanged", "reference": {"id": existing["id"], "revision": existing["revision"]}, "source": source}
   592	            if snapshot is not None:
   593	                result = self._curate_hot(connection, scope, category, [*snapshot['entries'], content],
   594	                                          snapshot['revision'], source=source, native_writer='MemorySystem.add')
   595	                if result['status'] != 'committed':
   596	                    return result
   597	                return {'status': 'committed', 'reference': result['references'][-1], 'source': source}
   598	            result = self._archive_write(connection, item)
   599	            if not result.get("ok"):
   600	                return {"status": "rejected", "reason": result.get("message", "Native memory rejected the fact")}
   601	            reference = self._record(connection, scope, Path(result["path"]), content, category, project, source)
   602	            return {"status": "committed", "reference": reference, "source": source}
   603	
   604	        return self._operation(scope, request_id, {"operation": "remember", "item": item, "project": project, "source": source}, save)
   605	
   606	    def recall(self, scope: MemoryScope, query: str, *, limit: int = 20) -> list[dict[str, Any]]:
   607	        if not isinstance(query, str) or not query.strip():
   608	            raise ValueError("A memory query is required")
   609	        if type(limit) is not int:
   610	            raise ValueError("The memory result limit must be an integer")
   611	        with self._transaction() as connection:
   612	            records, corpus = self._corpus(connection, scope)
   613	            if not corpus:
   614	                return []
   615	            ranked = self._native("rank", query=query, corpus=corpus, limit=max(1, min(limit, 100)))
   616	            return [{**records[item["path"]], "score": item["score"]} for item in ranked["results"]]
   617	
   618	    def _corpus(self, connection: sqlite3.Connection, scope: MemoryScope) -> tuple[dict[str, Any], list[dict[str, Any]]]:
   619	        records = {}
   620	        corpus = []
   621	        hot_entries = {}
   622	        for row in connection.execute("SELECT * FROM records WHERE status='active' ORDER BY updated DESC"):
   623	            if not self._allowed(scope, row):
   624	                continue
   625	            # Reuse native parsing inside this locked retrieval, keeping each reference's digest check.
   626	            content = self._content(row, hot_entries)
   627	            records[row["id"]] = {"reference": {"id": row["id"], "revision": row["revision"]},
   628	                                  "content": content, "category": row["category"], "project": row["project"],
   629	                                  "writer": row["writer"], "status": 'historical' if row['source_kind']=='learning' else row["status"],
   630	                                  "source":{'kind':row['source_kind'],'session':row['source_session'],'path':row['path']}}
   631	            corpus.append({"filePath": row["id"], "frontmatter": {"type": ("idea" if "/KNOWLEDGE/Ideas/" in row["path"] else "knowledge") if row["category"] == "project" else "memory",
   632	                                                                 "title": row["project"] or row["category"]},
   633	                           "body": content, "wordCount": max(1, len(content.split())),
   634	                           "noteClass": 'learning' if row['source_kind']=='learning' else "knowledge" if row["category"] == "project" else "memory"})
   635	        return records, corpus
   636	
   637	    def relevant_context(self, scope: MemoryScope, query: str, options: dict[str, Any]) -> dict[str, Any]:
   638	        if not isinstance(query, str) or len(query) > 4096 or not isinstance(options, dict):
   639	            raise ValueError("Invalid native memory retrieval request")
   640	        if set(options) - {"topK", "threshold", "excerptChars", "typeFilter"}:
   641	            raise ValueError("Unsupported native memory retrieval options")
   642	        for key, maximum in (("topK", 100), ("excerptChars", 65536)):
   643	            if key in options and (type(options[key]) is not int or not 1 <= options[key] <= maximum):
   644	                raise ValueError("Invalid native retrieval limit")
   645	        if "threshold" in options and (type(options["threshold"]) not in (int, float) or not 0 <= options["threshold"] < float("inf")):
   646	            raise ValueError("Invalid native retrieval threshold")
   647	        if "typeFilter" in options and options["typeFilter"] not in ("memory", "idea", "knowledge", "unknown"):
   648	            raise ValueError("Invalid native retrieval type")
   649	        with self._transaction() as connection:
   650	            _, corpus = self._corpus(connection, scope)
   651	            return self._native("rank", query=query, corpus=corpus, options=options)
   652	
   653	    def filter_history(self, scope: MemoryScope, content: str, timestamp: str) -> dict[str, Any]:
   654	        if not isinstance(content, str) or len(content) > 65536 or not isinstance(timestamp, str):
   655	            raise ValueError("Invalid reviewer history input")
   656	        if not CATEGORIES <= set(scope.read) or "*" not in scope.projects:
   657	            return {"content": "", "excluded": True}
   658	        with self._transaction() as connection:
   659	            return self._filter_history(connection,scope,content,timestamp)
   660	
   661	    def _filter_history(self, connection: sqlite3.Connection, scope: MemoryScope, content: str, timestamp: str) -> dict[str, Any]:
   662	        retained = connection.execute("""SELECT * FROM records AS retained WHERE status IN ('forgotten','superseded')
   663	                                      AND NOT EXISTS (SELECT 1 FROM records AS current WHERE current.status='active'
   664	                                      AND current.claim_digest=retained.claim_digest AND current.category=retained.category
   665	                                      AND current.project=retained.project)""").fetchall()
   666	        retained = [row for row in retained if self._allowed(scope, row)]
   667	        if not retained:
   668	            return {"content": content, "excluded": False}
   669	        try:
   670	            source_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
   671	            if source_time.tzinfo is None:
   672	                raise ValueError("Reviewer sources need an explicit timezone")
   673	            if source_time <= max(datetime.fromisoformat(row["updated"]) for row in retained):
   674	                return {"content": "", "excluded": True}
   675	        except ValueError:
   676	            return {"content": "", "excluded": True}
   677	        words = _claim_words(content)
   678	        hashes_by_length: dict[int, set[str]] = {}
   679	        for row in retained:
   680	            if row["claim_words"] > 0:
   681	                hashes_by_length.setdefault(row["claim_words"], set()).add(row["claim_digest"])
   682	        for length, hashes in hashes_by_length.items():
   683	            for start in range(len(words) - length + 1):
   684	                if _digest(" ".join(words[start:start + length])) in hashes:
   685	                    return {"content": "", "excluded": True}
   686	        return {"content": content, "excluded": False}
   687	
   688	    def _target(self, connection: sqlite3.Connection, scope: MemoryScope, reference: dict[str, Any]):
   689	        if not isinstance(reference, dict) or not isinstance(reference.get("id"), str) or type(reference.get("revision")) is not int:
   690	            return None
   691	        row = connection.execute("SELECT * FROM records WHERE id=?", (reference["id"],)).fetchone()
   692	        if row is None or not self._allowed(scope, row, write=True):
   693	            return None
   694	        return row
   695	
   696	    def get(self, scope: MemoryScope, reference: dict[str, Any]) -> dict[str, Any]:
   697	        if not isinstance(reference, dict) or not isinstance(reference.get("id"), str) or type(reference.get("revision")) is not int:
   698	            return {"status": "rejected", "reason": "A current memory reference is required"}
   699	        with self._transaction() as connection:
   700	            row = connection.execute("SELECT * FROM records WHERE id=?", (reference["id"],)).fetchone()
   701	            if row is None or not self._allowed(scope, row):
   702	                return {"status": "rejected", "reason": "The memory reference is unavailable or has no read grant"}
   703	            if row["status"] != "active" or row["revision"] != reference["revision"]:
   704	                return {"status": "conflict", "reason": "The referenced revision is no longer current"}
   705	            return {"status": "ok", "reference": reference, "content": self._content(row),
   706	                    "category": row["category"], "project": row["project"], "writer": row["writer"],
   707	                    "source": {"session": row["source_session"], "kind": row["source_kind"]}}
   708	
   709	    def correct(self, scope: MemoryScope, reference: dict[str, Any], content: str, request_id: str) -> dict[str, Any]:
   710	        def change(connection):
   711	            row = self._target(connection, scope, reference)
   712	            if row is None:
   713	                return {"status": "rejected", "reason": "The memory reference is unavailable or has no write grant"}
   714	            if row["status"] != "active" or row["revision"] != reference["revision"]:
   715	                return {"status": "conflict", "reason": "The referenced revision is no longer current"}
   716	            if row['category'] in HOT_FILES and row['category'] not in scope.read:
   717	                return {'status': 'rejected', 'reason': 'Hot-memory correction requires read and write grants'}
   718	            if not isinstance(content, str) or not content.strip():
   719	                return {"status": "rejected", "reason": "A replacement fact is required"}
   720	            current = self._hot_snapshot(connection, row['category']) if row['category'] in HOT_FILES else None
   721	            old = self._content(row)
   722	            replacement = content.strip()
   723	            path = self._path(row["path"])
   724	            if row["category"] == "project":
   725	                item = self._archive_item(path, replacement, row["source_session"])
   726	            else:
   727	                if not re.match(r"^(NAME|ROLE|RELATION|PREFERENCE|RULE): ", replacement):
   728	                    replacement = old.split(": ", 1)[0] + ": " + replacement
   729	                item = {"type": "memory", "actor": "principal" if row["category"] == "principal" else "assistant",
   730	                        "content": replacement}
   731	            invalid = self._validate(item, replacement, row["category"])
   732	            if invalid:
   733	                return {"status": "rejected", "reason": invalid}
   734	            if replacement == old:
   735	                return {"status": "unchanged", "reference": reference}
   736	            if self._blocked(connection, replacement):
   737	                return {"status": "rejected", "reason": "This fact needs explicit reactivation after correction or forgetting"}
   738	            existing = self._duplicate(connection, scope, replacement, row["category"], row["project"], row["path"])
   739	            if row["category"] == "project" and not existing:
   740	                # Native path slugs must remain unchanged for section references.
   741	                result = self._archive_write(connection, item)
   742	                if not result.get("ok"):
   743	                    return {"status": "rejected", "reason": result.get("message", "Native correction rejected")}
   744	                path = Path(result["path"])
   745	            elif row["category"] != "project":
   746	                entries = current['entries']
   747	                if old not in entries:
   748	                    return {"status": "conflict", "reason": "The native fact changed before correction"}
   749	                updated = [value for value in entries if value != old] if existing else [replacement if value == old else value for value in entries]
   750	                result = self._native("set_hot", path=str(path), entries=updated, writer=scope.writer, allowDrastic=True)
   751	                if not result.get("ok"):
   752	                    return {"status": "rejected", "reason": result.get("message", "Native correction rejected")}
   753	            new_reference = ({"id": existing["id"], "revision": existing["revision"]} if existing else
   754	                             self._record(connection, scope, path, replacement, row["category"], row["project"],
   755	                                          {"session": row["source_session"], "kind": "correction"}))
   756	            connection.execute("UPDATE records SET status='superseded',revision=revision+1,updated=? WHERE id=?", (_now(), row["id"]))
   757	            return {"status": "committed", "reference": new_reference, "supersedes": reference}
   758	        return self._operation(scope, request_id, {"operation": "correct", "reference": reference, "content": content}, change)
   759	
   760	    def forget(self, scope: MemoryScope, reference: dict[str, Any], request_id: str) -> dict[str, Any]:
   761	        def remove(connection):
   762	            row = self._target(connection, scope, reference)
   763	            if row is None:
   764	                return {"status": "rejected", "reason": "The memory reference is unavailable or has no write grant"}
   765	            if row["status"] != "active" or row["revision"] != reference["revision"]:
   766	                return {"status": "conflict", "reason": "The referenced revision is no longer current"}
   767	            if row["category"] != "project":
   768	                if row['category'] not in scope.read:
   769	                    return {'status': 'rejected', 'reason': 'Hot-memory forgetting requires read and write grants'}
   770	                current = self._hot_snapshot(connection, row['category'])
   771	                content = self._content(row)
   772	                path = self._path(row["path"])
   773	                if content not in current.get("entries", []):
   774	                    return {"status": "conflict", "reason": "The native fact changed before forgetting"}
   775	                result = self._native("set_hot", path=str(path), entries=[value for value in current["entries"] if value != content],
   776	                                      writer=scope.writer, allowDrastic=True)
   777	                if not result.get("ok"):
   778	                    return {"status": "rejected", "reason": result.get("message", "Native forgetting rejected")}
   779	            connection.execute("UPDATE records SET status='forgotten',revision=revision+1,updated=? WHERE id=?", (_now(), row["id"]))
   780	            return {"status": "committed", "reference": {"id": row["id"], "revision": row["revision"] + 1},
   781	                    "retained": ["native history", "audit evidence", "backups", "conversation history", "development logs"]}
   782	        return self._operation(scope, request_id, {"operation": "forget", "reference": reference}, remove)
