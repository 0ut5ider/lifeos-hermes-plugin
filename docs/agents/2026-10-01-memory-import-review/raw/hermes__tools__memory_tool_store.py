     1	"""MemoryStore — bounded, file-backed curated memory (MEMORY.md / USER.md).
     2	Entries are joined by ``ENTRY_DELIMITER``; budgets are in chars (model-independent).
     3	Module state that tests monkeypatch (``get_memory_dir``, ``fcntl``/``msvcrt``) stays
     4	in ``tools.memory_tool`` and is read lazily."""
     5	
     6	import logging
     7	import os
     8	import time
     9	from contextlib import contextmanager, suppress
    10	from pathlib import Path
    11	from typing import Any, Dict, List, Optional, Tuple
    12	
    13	from utils import atomic_write_text
    14	from tools.threat_patterns import first_threat_message as _first_threat_message
    15	
    16	logger = logging.getLogger("tools.memory_tool")
    17	
    18	# Block header prefixes rendered by _render_block; agent/conversation_compression.py
    19	# matches them to detect a leftover block for an emptied target — keep in lockstep.
    20	MEMORY_BLOCK_HEADERS = {
    21	    "memory": "MEMORY (your personal notes)", "user": "USER PROFILE (who the user is)"}
    22	
    23	ENTRY_DELIMITER = "\n§\n"
    24	
    25	
    26	def _scan_memory_content(content: str) -> Optional[str]:
    27	    """Error string if *content* matches injection/exfil patterns. Strict scope:
    28	    memory enters the system prompt, so a poisoned entry persists across sessions."""
    29	    return _first_threat_message(content, scope="strict")
    30	
    31	
    32	def _error(message: str, **extra) -> Dict[str, Any]:
    33	    return {"success": False, "error": message, **extra}
    34	
    35	
    36	def _drift_error(path: Path, bak_path: str) -> Dict[str, Any]:
    37	    """External drift: the file wouldn't round-trip, so flushing would discard content."""
    38	    return _error((
    39	        f"Refusing to write {path.name}: file on disk has content that wouldn't round-trip "
    40	        f"through the memory tool (likely added by the patch tool, a shell append, a manual edit, "
    41	        f"or a concurrent session). A snapshot was saved to {bak_path}. Resolve the drift first — "
    42	        f"either rewrite the file as a clean §-delimited list of entries, or move the extra "
    43	        f"content out — then retry. This guard exists to prevent silent data loss (issue #26045)."
    44	    ), drift_backup=bak_path, remediation=(
    45	        "Open the .bak file, integrate the missing entries into the memory tool one at a time via "
    46	        "memory(action=add, content=...), then remove or rewrite the original file to a clean state."))
    47	
    48	
    49	def _read_failed_error(path: Path) -> Dict[str, Any]:
    50	    """Existing-but-unreadable file: saving from an assumed-empty view would wipe it."""
    51	    return _error(
    52	        f"Refusing to write {path.name}: the file exists on disk but could not be read right now "
    53	        f"(temporarily locked by another program, a permission change, invalid/corrupt text encoding, "
    54	        f"or a filesystem error). Treating an unreadable file as empty and saving would wipe existing "
    55	        f"memory, so the write is refused. Nothing was changed — retry in a moment.")
    56	
    57	
    58	def _find_unique_match(entries: List[str], old_text: str) -> Tuple[Optional[int], bool]:
    59	    """``(index, ambiguous)`` for entries matching *old_text*. A whole-entry
    60	    EXACT match (``old_text == entry``) takes absolute priority — substring
    61	    matches are only considered when no entry equals *old_text*, so a short
    62	    entry stays addressable even when its full text is contained inside a
    63	    longer sibling entry (remove('test') vs '...tests pass...'). Exact-duplicate
    64	    matches are safe (first wins); distinct matches → ``(None, True)``."""
    65	    exact = [i for i, e in enumerate(entries) if e == old_text]
    66	    matches = exact if exact else [i for i, e in enumerate(entries) if old_text in e]
    67	    if len({entries[i] for i in matches}) > 1:
    68	        return None, True
    69	    return (matches[0] if matches else None), False
    70	
    71	
    72	def _pinned_index(entries: List[str], matched_entry: str) -> Optional[int]:
    73	    """Index of the exact entry a staged write was reviewed against; None once it is gone (stale)."""
    74	    return entries.index(matched_entry) if matched_entry in entries else None
    75	
    76	
    77	def _stale_entry_message(entry: str) -> str:
    78	    return (f"Entry changed since it was staged, so this write was not applied: '{entry}' is no longer "
    79	            f"in memory as reviewed. Recreate the change against the current entry or reject it; the "
    80	            f"pending record has been preserved.")
    81	
    82	
    83	# Optional third value of an _apply closure: a dict merged into the success payload —
    84	# e.g. the full text an entry-level replace overwrote, so a whole-entry write is never
    85	# silent about the loss (#117952). Same convention as _error(**extra).
    86	
    87	
    88	class MemoryStore:
    89	    """Bounded curated memory with file persistence; one instance per AIAgent.
    90	    ``_system_prompt_snapshot`` is frozen at load time (prefix-cache stable);
    91	    ``memory_entries`` / ``user_entries`` are live state persisted to disk."""
    92	
    93	    # Failed consolidation attempts (overflow / zero-match) allowed per turn before
    94	    # a TERMINAL "save skipped" result, so a fragile replace/add can't loop the turn
    95	    # to budget exhaustion and suppress the user's reply.
    96	    # See #42405.
    97	    _MAX_CONSOLIDATION_FAILURES_PER_TURN = 3
    98	
    99	    def __init__(self, memory_char_limit: int = 2200, user_char_limit: int = 1375, *,
   100	                 memory_enabled: bool = True, user_profile_enabled: bool = True):
   101	        self.memory_entries: List[str] = []
   102	        self.user_entries: List[str] = []
   103	        self.memory_char_limit, self.user_char_limit = memory_char_limit, user_char_limit
   104	        self.memory_enabled, self.user_profile_enabled = memory_enabled, user_profile_enabled
   105	        self._system_prompt_snapshot: Dict[str, str] = {"memory": "", "user": ""}
   106	        self._consolidation_failures = 0  # per turn; reset by reset_consolidation_failures()
   107	
   108	    # Per-turn counter of failed at-capacity consolidation attempts; reset at each turn boundary by
   109	    # reset_consolidation_failures() (#42405).
   110	    def target_enabled(self, target: str) -> bool:
   111	        return self.user_profile_enabled if target == "user" else self.memory_enabled
   112	
   113	    def reset_consolidation_failures(self) -> None:
   114	        """Call at turn start."""
   115	        self._consolidation_failures = 0
   116	
   117	    def _consolidation_failure(self, response: Dict[str, Any]) -> Dict[str, Any]:
   118	        """Count a consolidation failure: under the per-turn cap return ``response``
   119	        (it says how to retry); past it a TERMINAL result so the model stops looping.
   120	
   121	        Once the cap is exceeded, drop the retry instruction and return a TERMINAL result so the model stops
   122	        looping memory calls and proceeds to answer the user — a failed memory side effect must never block
   123	        the turn's reply (#42405).
   124	        """
   125	        self._consolidation_failures += 1
   126	        if self._consolidation_failures <= self._MAX_CONSOLIDATION_FAILURES_PER_TURN:
   127	            return response
   128	        return {"success": False, "done": True, "error": (
   129	            f"Memory consolidation failed {self._consolidation_failures} times this turn. Stop retrying "
   130	            "memory calls — leave memory unchanged for now and continue with your reply to the user. "
   131	            "The fact can be saved in a later turn.")}
   132	
   133	    def load_from_disk(self):
   134	        """Load MEMORY.md / USER.md and capture the frozen system-prompt snapshot.
   135	        Threat hits are replaced by a ``[BLOCKED: …]`` placeholder in the SNAPSHOT only;
   136	        live lists keep the raw text so the user can see and remove poisoned entries
   137	        (dropping them silently would hide the attack)."""
   138	        from tools.threat_patterns import scan_for_threats
   139	
   140	        def _sanitize(entry, filename):
   141	            # Strict scope, same as writes; empty / already-blocked entries pass through.
   142	            findings = scan_for_threats(entry, scope="strict") if entry and not entry.startswith("[BLOCKED:") else None
   143	            if not findings:
   144	                return entry
   145	            logger.warning("Memory entry from %s blocked at load time: %s", filename, ", ".join(findings))
   146	            return (f"[BLOCKED: {filename} entry contained threat pattern(s): {', '.join(findings)}. "
   147	                    f"Removed from system prompt; use memory(action=remove) to delete the original.]")
   148	
   149	        for target in ("memory", "user"):
   150	            path = self._path_for(target)
   151	            from hermes_constants import mkdir_under_hermes_home
   152	
   153	            mkdir_under_hermes_home(path.parent)
   154	            # Deduplicate (order-preserving, first occurrence wins).
   155	            entries = list(dict.fromkeys(self._read_file(path)))
   156	            self._set_entries(target, entries)
   157	            # External writers (MCP bridges, hand edits) can exceed the cap; the limit only fires on
   158	            # add/replace, so the oversized block would silently ride in the prompt while every later
   159	            # add is refused with no visible cause (#10877). Warn; never truncate a user's memories.
   160	            if (count := self._char_count(target)) > (limit := self._char_limit(target)):
   161	                logger.warning("%s exceeds its char limit on load: %d/%d chars. Entries stay loaded; "
   162	                               "further additions are blocked until it is back under the limit.",
   163	                               path.name, count, limit)
   164	            self._system_prompt_snapshot[target] = self._render_block(target, [_sanitize(e, path.name) for e in entries])
   165	
   166	    @staticmethod
   167	    @contextmanager
   168	    def _file_lock(path: Path):
   169	        """Exclusive lock on a separate .lock file so the memory file itself can
   170	        still be atomically replaced."""
   171	        from tools import memory_tool as _mt  # fcntl/msvcrt live (and are patched) there
   172	        fcntl, msvcrt = _mt.fcntl, _mt.msvcrt
   173	        lock_path = path.with_suffix(path.suffix + ".lock")
   174	        from hermes_constants import mkdir_under_hermes_home
   175	
   176	        mkdir_under_hermes_home(lock_path.parent)
   177	        if fcntl is None and msvcrt is None:
   178	            yield
   179	            return
   180	        flags = os.O_RDWR | os.O_CREAT
   181	        if hasattr(os, "O_NOFOLLOW"):
   182	            flags |= os.O_NOFOLLOW
   183	        raw_fd = os.open(lock_path, flags, 0o600)
   184	        try:
   185	            # The creation mode is filtered through the process umask and does
   186	            # not repair a lock left loose by an older Hermes process. Tighten
   187	            # the opened inode before acquiring the lock so both cases are
   188	            # owner-only. Operating on the fd avoids a path-swap window.
   189	            if hasattr(os, "fchmod"):
   190	                os.fchmod(raw_fd, 0o600)
   191	            fd = os.fdopen(raw_fd, "r+", encoding="utf-8")
   192	        except Exception:
   193	            os.close(raw_fd)
   194	            raise
   195	        with fd:
   196	            def _flock(unlock: bool):
   197	                if fcntl:
   198	                    fcntl.flock(fd, fcntl.LOCK_UN if unlock else fcntl.LOCK_EX)
   199	                else:
   200	                    fd.seek(0)
   201	                    msvcrt.locking(fd.fileno(), msvcrt.LK_UNLCK if unlock else msvcrt.LK_LOCK, 1)
   202	            _flock(False)
   203	            try:
   204	                yield
   205	            finally:
   206	                with suppress(OSError):
   207	                    _flock(True)
   208	
   209	    @staticmethod
   210	    def _path_for(target: str) -> Path:
   211	        from tools import memory_tool  # get_memory_dir is monkeypatched there
   212	        return memory_tool.get_memory_dir() / ("USER.md" if target == "user" else "MEMORY.md")
   213	
   214	    def _entries_for(self, target: str) -> List[str]:
   215	        return self.user_entries if target == "user" else self.memory_entries
   216	
   217	    def _set_entries(self, target: str, entries: List[str]):
   218	        setattr(self, "user_entries" if target == "user" else "memory_entries", entries)
   219	
   220	    def _char_count(self, target: str) -> int:
   221	        return len(ENTRY_DELIMITER.join(self._entries_for(target)))
   222	
   223	    def _char_limit(self, target: str) -> int:
   224	        return self.user_char_limit if target == "user" else self.memory_char_limit
   225	
   226	    def _usage(self, target: str) -> str:
   227	        return f"{self._char_count(target):,}/{self._char_limit(target):,}"
   228	
   229	    def _usage_pct(self, target: str, current: int) -> str:
   230	        limit = self._char_limit(target)
   231	        return f"{min(100, int((current / limit) * 100)) if limit > 0 else 0}% — {current:,}/{limit:,} chars"
   232	
   233	    def _failure_with_entries(self, target: str, message: str) -> Dict[str, Any]:
   234	        """Consolidation failure carrying the live entries so the model can consolidate."""
   235	        return self._consolidation_failure(
   236	            _error(message, current_entries=self._entries_for(target), usage=self._usage(target)))
   237	
   238	    def _batch_failure(self, target: str, message: str) -> Dict[str, Any]:
   239	        """Batch-abort failure WITHOUT ``current_entries``: the store did not change and the
   240	        caller already holds the inventory, so echoing it made each consolidation retry
   241	        grow the context it was invoked to shrink (#97316)."""
   242	        return self._consolidation_failure(
   243	            _error(message + " No operations were applied (batch is all-or-nothing).", usage=self._usage(target)))
   244	
   245	    def _mutate(self, target: str, mutate, *, skip_drift: bool = False) -> Dict[str, Any]:
   246	        """Lock, re-read from disk, run ``mutate(entries, limit)`` -> ``(new_entries, message)``
   247	        or an error dict, then persist and return the success response. The reload aborts
   248	        on an existing-but-unreadable file (even append-only ``add`` rewrites the whole
   249	        file) and, unless *skip_drift*, on external drift (flushing would discard
   250	        un-roundtrippable content). Drift check and parse use the SAME raw snapshot —
   251	        a failed second read used to count as "no drift". The closure may return a
   252	        third value, a dict merged into the success payload (``_error``'s ``**extra``
   253	        convention) — e.g. the full text a replace overwrote (#117952). ANY dict the closure
   254	        returns is passed through verbatim and nothing is persisted: error dicts, or the
   255	        success payload of a read-only closure (``resolve_entry``, ``resolve_batch_entries``)."""
   256	        path = self._path_for(target)
   257	        with self._file_lock(path):
   258	            raw, read_ok = self._read_raw_checked(path)
   259	            if not read_ok:
   260	                return _read_failed_error(path)
   261	            bak = None if skip_drift else self._detect_external_drift(target, raw)
   262	            self._set_entries(target, list(dict.fromkeys(self._parse_entries(raw))))
   263	            if bak:
   264	                return _drift_error(path, bak)
   265	            result = mutate(self._entries_for(target), self._char_limit(target))
   266	            if isinstance(result, dict):
   267	                return result
   268	            self._set_entries(target, result[0])
   269	            from hermes_constants import mkdir_under_hermes_home
   270	
   271	            mkdir_under_hermes_home(path.parent)
   272	            self._write_file(path, result[0])
   273	            extra_fields = result[2] if len(result) > 2 else {}
   274	            return self._success_response(target, result[1], **extra_fields)
   275	
   276	    def add(self, target: str, content: str) -> Dict[str, Any]:
   277	        """Append a new entry. Returns error if it would exceed the char limit."""
   278	        content = content.strip()
   279	        if not content:
   280	            return _error("Content cannot be empty.")
   281	        if scan_error := _scan_memory_content(content):
   282	            return _error(scan_error)
   283	
   284	        def _add(entries, limit):
   285	            if content in entries:
   286	                return self._success_response(target, "Entry already exists (no duplicate added).")
   287	            if len(ENTRY_DELIMITER.join(entries + [content])) > limit:
   288	                return self._failure_with_entries(target, (
   289	                    f"Memory at {self._char_count(target):,}/{limit:,} chars. Adding this entry "
   290	                    f"({len(content)} chars) would exceed the limit. Consolidate now: use 'replace' to merge "
   291	                    f"overlapping entries into shorter ones or 'remove' stale or less important entries (see "
   292	                    f"current_entries below), then retry this add — all in this turn."))
   293	            return entries + [content], "Entry added."
   294	        # Append-only: skip the drift guard (appending never clobbers foreign
   295	        # content) but still refuse a failed read — add rewrites the WHOLE file.
   296	        return self._mutate(target, _add, skip_drift=True)
   297	
   298	    def replace(self, target: str, old_text: str, new_content: str,
   299	                matched_entry: Optional[str] = None) -> Dict[str, Any]:
   300	        """Find the entry containing old_text (whole-entry exact match first) and
   301	        replace the WHOLE entry with new_content — old_text only locates the entry;
   302	        the matched span is not spliced into it."""
   303	        new_content = new_content.strip()
   304	        if not old_text.strip():
   305	            return _error("old_text cannot be empty.")
   306	        if not new_content:
   307	            return _error("new_content cannot be empty. Use 'remove' to delete entries.")
   308	        if scan_error := _scan_memory_content(new_content):
   309	            return _error(scan_error)
   310	        return self._edit(target, old_text.strip(), new_content, matched_entry)
   311	
   312	    def remove(self, target: str, old_text: str, matched_entry: Optional[str] = None) -> Dict[str, Any]:
   313	        """Remove the entry containing old_text substring."""
   314	        if not old_text.strip():
   315	            return _error("old_text cannot be empty.")
   316	        return self._edit(target, old_text.strip(), None, matched_entry)
   317	
   318	    def _locate(self, entries: List[str], old_text: str, verb: str, matched_entry: Optional[str] = None):
   319	        """Index of the entry *old_text* selects, or the error dict the edit returns. A write
   320	        staged for approval carries the FULL entry it was reviewed against (*matched_entry*):
   321	        only that exact entry qualifies, so replay never hits a newer entry that still
   322	        contains old_text."""
   323	        if matched_entry is not None:
   324	            idx = _pinned_index(entries, matched_entry)
   325	            return idx if idx is not None else _error(_stale_entry_message(matched_entry))
   326	        idx, ambiguous = _find_unique_match(entries, old_text)
   327	        if ambiguous:
   328	            return _error(f"Multiple entries matched '{old_text}'. Be more specific.",
   329	                          matches=[e[:80] + ("..." if len(e) > 80 else "") for e in entries if old_text in e])
   330	        if idx is None:
   331	            return self._consolidation_failure(_error(
   332	                f"No entry matched '{old_text}'. Check current_entries below and retry with the exact text "
   333	                f"of the entry you want to {verb}.", current_entries=entries))
   334	        return idx
   335	
   336	    def resolve_entry(self, target: str, old_text: str, verb: str) -> Dict[str, Any]:
   337	        """``{"success": True, "matched_entry": <full entry>}`` for the entry *old_text* selects
   338	        now, read under the lock, or the error the direct edit would return."""
   339	        def _resolve(entries, limit):
   340	            idx = self._locate(entries, old_text.strip(), verb)
   341	            return idx if isinstance(idx, dict) else {"success": True, "matched_entry": entries[idx]}
   342	        return self._mutate(target, _resolve, skip_drift=True)
   343	
   344	    def _edit(self, target: str, old_text: str, new_content: Optional[str],
   345	              matched_entry: Optional[str] = None) -> Dict[str, Any]:
   346	        """Locked replace (``new_content`` set) or remove (None) of the entry matching *old_text*."""
   347	        def _apply(entries, limit):
   348	            idx = self._locate(entries, old_text, "replace" if new_content else "remove", matched_entry)
   349	            if isinstance(idx, dict):
   350	                return idx
   351	            replaced = entries[:idx] + ([] if new_content is None else [new_content]) + entries[idx + 1:]
   352	            if new_content is None:
   353	                return replaced, "Entry removed.", {"removed_entry": entries[idx]}
   354	            new_total = len(ENTRY_DELIMITER.join(replaced))
   355	            if new_total > limit:
   356	                return self._failure_with_entries(target, (
   357	                    f"Replacement would put memory at {new_total:,}/{limit:,} chars. Shorten the new content, "
   358	                    f"or 'remove' other stale or less important entries to make room (see current_entries "
   359	                    f"below), then retry — all in this turn."))
   360	            return replaced, "Entry replaced.", {"replaced_entry": entries[idx]}
   361	        return self._mutate(target, _apply)
   362	
   363	    @staticmethod
   364	    def _apply_batch_op(working: List[str], act: str, content: str, old_text: str,
   365	                        pos: str, matched_entry: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
   366	        """Apply one batch op to *working*; return ``(error message, previous content)``.
   367	        Previous content is captured before each replace/remove, under the store lock.
   368	        It is published only after the entire batch has been validated and persisted.
   369	        A staged op's *matched_entry* selects exactly that entry, as in ``_locate``.
   370	        """
   371	        if act == "add":
   372	            if not content:
   373	                return f"{pos}: content is required.", None
   374	            if content not in working:  # idempotent -- skip duplicate, don't fail the batch
   375	                working.append(content)
   376	            return None, None
   377	        if act not in ("replace", "remove"):
   378	            return f"{pos}: unknown action. Use add, replace, or remove.", None
   379	        if not old_text:
   380	            return f"{pos}: old_text is required.", None
   381	        if act == "replace" and not content:
   382	            return f"{pos}: content is required (use action='remove' to delete).", None
   383	        if matched_entry is not None:
   384	            idx = _pinned_index(working, matched_entry)
   385	            if idx is None:
   386	                return f"{pos}: {_stale_entry_message(matched_entry)}", None
   387	        else:
   388	            idx, ambiguous = _find_unique_match(working, old_text)
   389	            if ambiguous:
   390	                return f"{pos}: '{old_text}' matched multiple distinct entries -- be more specific.", None
   391	            if idx is None:
   392	                return f"{pos}: no entry matched '{old_text}'.", None
   393	        previous_content = working[idx]
   394	        working[idx:idx + 1] = [content] if act == "replace" else []
   395	        return None, previous_content
   396	
   397	    def apply_batch(self, target: str, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
   398	        """Apply add/replace/remove ops atomically against the FINAL budget, so one call
   399	        can free space and add entries. All-or-nothing: any malformed / unmatched op or
   400	        an over-limit result writes NOTHING and returns the first failure. Aborts do not
   401	        echo ``current_entries`` — the store is unchanged and the model already has it."""
   402	        return self._batch(target, operations, commit=True)
   403	
   404	    def resolve_batch_entries(self, target: str, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
   405	        """Dry-run ``apply_batch`` under the lock without persisting: the same content scan,
   406	        op walk, empty-store and budget checks, so it fails exactly where the direct batch
   407	        would; on success ``{"success": True, "matched_entries": [...]}`` — per op, the FULL
   408	        entry its replace/remove selects now (None for add), in batch order."""
   409	        return self._batch(target, operations, commit=False)
   410	
   411	    def _batch(self, target: str, operations: List[Dict[str, Any]], *, commit: bool) -> Dict[str, Any]:
   412	        if not operations:
   413	            return _error("operations list is empty.")
   414	        ops = [op or {} for op in operations]
   415	        # Scan every add/replace content BEFORE touching disk -- one poisoned op rejects the batch.
   416	        for i, op in enumerate(ops):
   417	            scan_error = op.get("action") in {"add", "replace"} and op.get("content") and _scan_memory_content(op["content"])
   418	            if scan_error:
   419	                return _error(f"Operation {i + 1}: {scan_error}")
   420	
   421	        def _apply(entries, limit):
   422	            working = list(entries)  # only committed if the whole batch validates
   423	            matched = []  # per op, the entry a replace/remove selected (None for add)
   424	            for i, op in enumerate(ops):
   425	                act = op.get("action")
   426	                msg, previous_content = self._apply_batch_op(
   427	                    working, act, (op.get("content") or op.get("new_text") or "").strip(),
   428	                    (op.get("old_text") or "").strip(), f"Operation {i + 1} ({act or 'unknown'})",
   429	                    op.get("matched_entry"))
   430	                if msg:
   431	                    return self._batch_failure(target, msg)
   432	                matched.append(previous_content)
   433	            if entries and not working:
   434	                # #103419: a consolidation batch that removes the last entry would
   435	                # commit an empty file as a normal successful write. Refuse; single
   436	                # remove() is the deliberate-wipe path.
   437	                label = self._path_for(target).name
   438	                return self._batch_failure(target, (
   439	                    f"Refusing to empty {label}: this batch would remove every entry from a "
   440	                    f"previously non-empty store. Keep at least one entry — merge overlapping "
   441	                    f"entries into a shorter one instead of removing the last one. To delete the "
   442	                    f"final entry deliberately, use single remove() calls."))
   443	            new_total = len(ENTRY_DELIMITER.join(working))  # budget check against the FINAL state only
   444	            if new_total > limit:
   445	                return self._batch_failure(target, (
   446	                    f"After applying all {len(operations)} operations, memory would be at "
   447	                    f"{new_total:,}/{limit:,} chars -- over the limit. Remove or shorten more "
   448	                    f"entries in the same batch, then retry."))
   449	            if not commit:
   450	                return {"success": True, "matched_entries": matched}
   451	            # op index -> full entry text its replace/remove selected (#117952), 1-based to
   452	            # match the "Operation N" error numbering the model sees for failed ops.
   453	            replaced, removed = {}, {}
   454	            for i, (op, previous_content) in enumerate(zip(ops, matched), 1):
   455	                if previous_content is not None:
   456	                    (replaced if op.get("action") == "replace" else removed)[i] = previous_content
   457	            replaced_fields = {"replaced_entries": replaced} if replaced else {}
   458	            if removed:
   459	                replaced_fields["removed_entries"] = removed
   460	            return working, f"Applied {len(operations)} operation(s).", replaced_fields
   461	        return self._mutate(target, _apply, skip_drift=not commit)
   462	
   463	    def format_for_system_prompt(self, target: str) -> Optional[str]:
   464	        """Frozen load-time snapshot (NOT live state — mid-session writes don't touch
   465	        it, preserving the prefix cache); None if empty."""
   466	        return self._system_prompt_snapshot.get(target, "") or None
   467	
   468	    def _success_response(self, target: str, message: str = None, **extra) -> Dict[str, Any]:
   469	        """TERMINAL and WITHOUT the entries list: echoing entries invites the model to
   470	        "find more to fix" and re-issue the same ops. A successful write resets the
   471	        per-turn failure budget. ``**extra`` mirrors ``_error``'s convention — e.g. the
   472	        full text a replace overwrote (#117952), deliberately visible despite the
   473	        no-entries rule: silent data loss is the failure this field exists to prevent."""
   474	        # A successful write means the consolidation loop made progress, so the per-turn failure budget
   475	        # resets (the cap counts consecutive failures, not lifetime ones within a turn) (#42405).
   476	        self._consolidation_failures = 0
   477	        return {"success": True, "done": True, "target": target,
   478	                "usage": self._usage_pct(target, self._char_count(target)),
   479	                "entry_count": len(self._entries_for(target)), **({"message": message} if message else {}),
   480	                **extra,
   481	                "note": "Write saved. This update is complete — do not repeat it."}
   482	
   483	    def _render_block(self, target: str, entries: List[str]) -> str:
   484	        """System prompt block: header + usage indicator + entries ("" when empty)."""
   485	        if not entries:
   486	            return ""
   487	        content, sep = ENTRY_DELIMITER.join(entries), "═" * 46
   488	        title = MEMORY_BLOCK_HEADERS["user" if target == "user" else "memory"]
   489	        return f"{sep}\n{title} [{self._usage_pct(target, len(content))}]\n{sep}\n{content}"
   490	
   491	    @staticmethod
   492	    def _read_raw_checked(path: Path) -> Tuple[str, bool]:
   493	        """``(raw, read_ok)``; ``read_ok`` is False ONLY when the file EXISTS but can't be
   494	        read. Decoding stays STRICT (``errors="replace"`` would hand callers a lossy view
   495	        a save then persists); ``utf-8-sig`` strips a Notepad BOM off the first entry."""
   496	        if not path.exists():
   497	            return "", True
   498	        try:
   499	            # utf-8-sig strips a leading UTF-8 BOM (Notepad-edited memory files on Windows) and is
   500	            # byte-identical to utf-8 otherwise. Plain utf-8 kept U+FEFF glued to the first entry,
   501	            # corrupting matching/dedup for that entry forever (#10878 / PR #10888). Decode errors stay
   502	            # STRICT on purpose: errors="replace" would hand read-modify-write callers a lossy view that a
   503	            # subsequent save persists over the real bytes — the wipe class documented above. Undecodable
   504	            # bytes must surface as read_ok=False.
   505	            return path.read_text(encoding="utf-8-sig"), True
   506	        except (OSError, UnicodeDecodeError):
   507	            return "", False
   508	
   509	    @staticmethod
   510	    def _parse_entries(raw: str) -> List[str]:
   511	        """Stripped, non-empty entries; splits on the FULL delimiter so a bare "§" survives."""
   512	        return [e for e in (x.strip() for x in raw.split(ENTRY_DELIMITER)) if e]
   513	
   514	    @staticmethod
   515	    def _read_file(path: Path) -> List[str]:
   516	        """Entries of a memory file ([] on any error). Read-only callers only; mutation
   517	        paths use ``_read_raw_checked`` so they can refuse to overwrite an unreadable file."""
   518	        return MemoryStore._parse_entries(MemoryStore._read_raw_checked(path)[0])
   519	
   520	    @staticmethod
   521	    def _write_file(path: Path, entries: List[str]):
   522	        """Atomic temp-file + rename: readers never see a truncated file. Callers
   523	        hold ``_file_lock`` (via ``_mutate``): a bare write from an earlier snapshot
   524	        drops concurrent entries (#119668)."""
   525	        try:
   526	            atomic_write_text(path, ENTRY_DELIMITER.join(entries), tmp_prefix=".mem_")
   527	        except OSError as e:
   528	            raise RuntimeError(f"Failed to write memory file {path}: {e}")
   529	
   530	    def _detect_external_drift(self, target: str, raw: str) -> Optional[str]:
   531	        """``.bak.<ts>`` snapshot path if *raw* shows external drift, else None. Signals:
   532	        round-trip mismatch, or one entry over the whole-file limit (no tool-written
   533	        entry can be — an external writer appended free-form text)."""
   534	        parsed = self._parse_entries(raw)
   535	        if not raw.strip() or (raw.strip() == ENTRY_DELIMITER.join(parsed)
   536	                               and max(map(len, parsed), default=0) <= self._char_limit(target)):
   537	            return None
   538	        path = self._path_for(target)
   539	        bak_path = path.with_suffix(path.suffix + f".bak.{int(time.time())}")
   540	        try:
   541	            bak_path.write_text(raw, encoding="utf-8")
   542	        except OSError:
   543	            return str(bak_path) + " (BACKUP FAILED — file unchanged on disk)"
   544	        return str(bak_path)
