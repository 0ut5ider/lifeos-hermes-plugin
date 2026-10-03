     1	#!/usr/bin/env python3
     2	"""Memory Tool - persistent curated memory (MEMORY.md = agent notes, USER.md = user
     3	profile). Both enter the system prompt as a FROZEN snapshot at session start;
     4	mid-session writes hit disk but never change the prompt (prefix cache intact).
     5	Single `memory` tool: add/replace/remove or a batch `operations` list."""
     6	
     7	import copy
     8	import json
     9	import logging
    10	from contextvars import ContextVar
    11	from pathlib import Path
    12	from hermes_constants import get_hermes_home
    13	from typing import Dict, Any, List, Optional, Tuple
    14	
    15	from utils import is_truthy_value
    16	from tools.registry import no_cache_check_fn
    17	
    18	# fcntl is Unix-only; Windows uses msvcrt. MemoryStore reads both lazily from
    19	# this module (tests patch ``memory_tool.fcntl``).
    20	msvcrt = None
    21	try:
    22	    import fcntl
    23	except ImportError:
    24	    fcntl = None
    25	    try:
    26	        import msvcrt  # noqa: F401
    27	    except ImportError:
    28	        pass
    29	
    30	logger = logging.getLogger(__name__)
    31	
    32	# One tool-definition pass must use ONE config decision for availability and the
    33	# dynamic target schema: the check_fn result flows to the immediately following
    34	# dynamic_schema_overrides call; ContextVar isolates concurrent profile builds.
    35	_memory_surface_flags: ContextVar[Optional[Tuple[bool, bool]]] = ContextVar("memory_surface_flags", default=None)
    36	
    37	
    38	def get_memory_dir() -> Path:
    39	    """Profile-scoped memories dir, resolved per call (HERMES_HOME may switch after import)."""
    40	    return get_hermes_home() / "memories"
    41	
    42	
    43	from tools.memory_tool_store import (  # noqa: E402,F401  (re-exports)
    44	    ENTRY_DELIMITER, MEMORY_BLOCK_HEADERS, MemoryStore, _scan_memory_content)
    45	
    46	
    47	def load_on_disk_store() -> "MemoryStore":
    48	    """Fresh on-disk MemoryStore with configured limits/flags for contexts with no live
    49	    agent (gateway, Desktop, ``/memory``) so approvals enforce the SAME caps as
    50	    ``agent_init``. Falls back to defaults if config can't load; never raises."""
    51	    try:
    52	        from hermes_cli.config import load_config
    53	        config = load_config() or {}
    54	        mem_cfg = get_builtin_memory_config(config)
    55	        memory_enabled, user_profile_enabled = get_builtin_memory_store_flags(config)
    56	        store = MemoryStore(int(mem_cfg.get("memory_char_limit", 2200)), int(mem_cfg.get("user_char_limit", 1375)),
    57	                            memory_enabled=memory_enabled, user_profile_enabled=user_profile_enabled)
    58	    except Exception:
    59	        store = MemoryStore()  # config optional — fall back to defaults rather than break /memory
    60	    store.load_from_disk()
    61	    return store
    62	
    63	
    64	def _pin_matched_entries(store: "MemoryStore", payload: Dict[str, Any]) -> Optional[str]:
    65	    """Record on each staged replace/remove the FULL entry its old_text selects now. Approval
    66	    then applies to exactly the entry the approver reviewed and refuses if it changed:
    67	    re-running the old_text search at approve time could hit a newer entry that still
    68	    contains it. Returns the JSON error when the search fails now, as the direct write would."""
    69	    target = payload.get("target", "memory")
    70	    if payload.get("action") == "batch":
    71	        result = store.resolve_batch_entries(target, payload["operations"])
    72	        if result.get("success"):
    73	            payload["operations"] = [op if entry is None else {**op, "matched_entry": entry}
    74	                                     for op, entry in zip(payload["operations"], result["matched_entries"])]
    75	    elif payload.get("action") in _BG_DELETE_ACTIONS:
    76	        result = store.resolve_entry(target, payload.get("old_text") or "", payload["action"])
    77	        if result.get("success"):
    78	            payload["matched_entry"] = result["matched_entry"]
    79	    else:
    80	        return None
    81	    return None if result.get("success") else json.dumps(result, ensure_ascii=False)
    82	
    83	
    84	def _gate_or_stage(store: "MemoryStore", summary: str, detail: str, payload: Dict[str, Any]) -> Optional[str]:
    85	    """JSON tool-result string when the write must NOT proceed (blocked or staged
    86	    for approval), None to proceed. Fails open if the gate module can't load."""
    87	    try:
    88	        from tools import write_approval as wa
    89	    except Exception:
    90	        return None
    91	    decision = wa.evaluate_gate(wa.MEMORY, inline_summary=summary, inline_detail=detail)
    92	    if decision.allow:
    93	        return None
    94	    if decision.blocked:
    95	        return tool_error(decision.message, success=False)
    96	    if (unmatched := _pin_matched_entries(store, payload)) is not None:
    97	        return unmatched
    98	    record = wa.stage_write(wa.MEMORY, payload, summary=f"{summary}: {detail[:120]}", origin=wa.current_origin())
    99	    return json.dumps({"success": True, "staged": True, "pending_id": record["id"], "message": decision.message},
   100	                      ensure_ascii=False)
   101	
   102	
   103	# action -> (store call, gate (summary, detail) text) for the live tool path and staged replay.
   104	_STORE_ACTIONS = {
   105	    "add": (lambda store, target, content, old_text, entry=None: store.add(target, content),
   106	            lambda label, content, old_text: (f"add to {label}", content or "")),
   107	    "replace": (lambda store, target, content, old_text, entry=None: store.replace(target, old_text, content, entry),
   108	                lambda label, content, old_text: (f"replace in {label}",
   109	                                                  f"entry matching: {old_text}\nwhole entry becomes: {content}")),
   110	    "remove": (lambda store, target, content, old_text, entry=None: store.remove(target, old_text, entry),
   111	               lambda label, content, old_text: (f"remove from {label}", old_text or ""))}
   112	
   113	
   114	def _batch_op_line(op: Dict[str, Any]) -> str:
   115	    op = op or {}
   116	    act, content, old = op.get("action", "?"), op.get("content") or op.get("new_text") or "", op.get("old_text", "")
   117	    if act == "remove":
   118	        return f"- remove: {old}"
   119	    # Whole-entry contract (#117952): the approver must not read this as a span patch.
   120	    return (f"- replace entry matching '{old}' -> whole entry becomes: {content}" if act == "replace"
   121	            else f"- {act}: {content}")
   122	
   123	
   124	def _apply_write_gate(store: "MemoryStore", action: str, target: str, content: Optional[str],
   125	                      old_text: Optional[str], operations: Optional[List[Dict[str, Any]]] = None) -> Optional[str]:
   126	    """Gate one mutating op, or (``operations`` set) a whole batch as a single unit."""
   127	    label = "user profile" if target == "user" else "memory"
   128	    if operations is not None:
   129	        return _gate_or_stage(store, f"apply {len(operations)} op(s) to {label}",
   130	                              "\n".join(_batch_op_line(op) for op in operations),
   131	                              {"action": "batch", "target": target, "operations": operations})
   132	    return _gate_or_stage(store, *_STORE_ACTIONS[action][1](label, content, old_text),
   133	                          {"action": action, "target": target, "content": content, "old_text": old_text})
   134	
   135	
   136	def _validate_single_op(store, action, target, content, old_text) -> Optional[str]:
   137	    """Validate BEFORE the gate so an invalid write is rejected now, not at approve time.
   138	    Missing ``old_text`` is recoverable (it can't be schema-required — needs a combinator
   139	    the Codex backend rejects): return the inventory plus a retry instruction."""
   140	    if action == "add" and not content:
   141	        return tool_error("Content is required for 'add' action.", success=False)
   142	    if action in ("replace", "remove") and not old_text:
   143	        replace_hint = (" For 'replace', content is the COMPLETE new entry -- the whole "
   144	                        "matched entry is overwritten, not just the old_text span."
   145	                        if action == "replace" else "")
   146	        return json.dumps({
   147	            "success": False,
   148	            "error": (f"'{action}' needs old_text -- a short unique substring of the entry "
   149	                      f"to {action}. None was provided. Reissue the {action} with old_text "
   150	                      f"set to part of one of the current_entries below.{replace_hint}"),
   151	            "current_entries": store._entries_for(target), "usage": store._usage(target)}, ensure_ascii=False)
   152	    if action == "replace" and not content:
   153	        return tool_error("content is required for 'replace' action.", success=False)
   154	    return None
   155	
   156	
   157	_BG_DELETE_ACTIONS = ("replace", "remove")
   158	
   159	
   160	def destructive_ops(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
   161	    """The replace/remove ops of a staged memory payload, single-op or batch shape."""
   162	    ops = (payload.get("operations") or []) if payload.get("action") == "batch" else [payload]
   163	    return [op for op in ops if (op or {}).get("action") in _BG_DELETE_ACTIONS]
   164	
   165	
   166	def _background_delete_gate(store, action, operations, target="memory", content=None,
   167	                            old_text=None) -> Optional[str]:
   168	    """Fail-closed operation gate for unattended background-review forks (#105921): ``add``
   169	    stays available (it is all any review prompt asks for), while ``replace``/``remove`` —
   170	    single or inside a batch — are never applied unattended. The op is staged in the pending
   171	    store instead of merely denied: the fork's own review summary is never published back, so
   172	    a plain denial would drop the consolidation request with no surfacing path at all. A
   173	    staging failure fails closed to a plain denial."""
   174	    from tools.skill_provenance import is_unattended_review
   175	
   176	    if not is_unattended_review():
   177	        return None
   178	    payload = ({"action": "batch", "target": target, "operations": operations}
   179	               if operations is not None else
   180	               {"action": action, "target": target, "content": content, "old_text": old_text})
   181	    if not destructive_ops(payload):
   182	        return None
   183	    detail = ("; ".join(_batch_op_line(op) for op in operations) if operations is not None
   184	              else _batch_op_line({"action": action, "content": content, "old_text": old_text}))
   185	    try:
   186	        if (unmatched := _pin_matched_entries(store, payload)) is not None:
   187	            return unmatched
   188	        from tools import write_approval as wa
   189	        record = wa.stage_write(
   190	            wa.MEMORY, payload,
   191	            summary=(f"background review consolidation ({'batch' if operations is not None else action} "
   192	                     f"on {target}): {detail}")[:200],
   193	            origin=wa.current_origin())
   194	        return json.dumps({
   195	            "success": True, "staged": True, "proposal_staged": True, "pending_id": record["id"],
   196	            "message": ("Background review may not delete memory entries unattended. The proposed "
   197	                        f"{'batch' if operations is not None else action} was staged for your approval — "
   198	                        "review it with /memory pending (approve to apply, discard to drop)."),
   199	        }, ensure_ascii=False)
   200	    except Exception:
   201	        logger.warning("Failed to stage background-review consolidation; denying", exc_info=True)
   202	        return tool_error(
   203	            "Background review may not delete memory entries ('replace'/'remove', including in a "
   204	            "batch); 'add' is still available.", success=False)
   205	
   206	
   207	def memory_tool(action: str = None, target: str = "memory", content: str = None, old_text: str = None,
   208	                new_text: str = None, operations: Optional[List[Dict[str, Any]]] = None,
   209	                store: Optional[MemoryStore] = None) -> str:
   210	    """Tool entry point; returns a JSON string. Single op (action + content/old_text)
   211	    or batch (``operations``, atomic against the final budget). ``new_text``
   212	    aliases ``content`` -- for 'replace' both mean the COMPLETE new entry (the
   213	    whole matched entry is overwritten; old_text only locates it)."""
   214	    if store is None:
   215	        return tool_error("Memory is not available. It may be disabled in config or this environment.", success=False)
   216	    if content is None and new_text is not None:
   217	        content = new_text
   218	    # Strict providers send JSON null for optional fields; treat as omitted.
   219	    target = "memory" if target is None else target
   220	    target_error = _memory_target_error(store, target)
   221	    if target_error is not None:
   222	        return json.dumps(target_error)
   223	    if operations:
   224	        if not isinstance(operations, list):
   225	            return tool_error("operations must be a list of {action, content?, old_text?} objects.", success=False)
   226	        denied = _background_delete_gate(store, action, operations, target)
   227	        if denied is not None:
   228	            return denied
   229	        # Approval gate: stages (background/gateway) or prompts inline (CLI); off by default.
   230	        gate_result = _apply_write_gate(store, "batch", target, None, None, operations)
   231	        if gate_result is not None:
   232	            return gate_result
   233	        return json.dumps(store.apply_batch(target, operations), ensure_ascii=False)
   234	    if action not in _STORE_ACTIONS:
   235	        return tool_error(f"Unknown action '{action}'. Use: add, replace, remove", success=False)
   236	    invalid = (_validate_single_op(store, action, target, content, old_text)
   237	               or _background_delete_gate(store, action, None, target, content, old_text)
   238	               or _apply_write_gate(store, action, target, content, old_text))
   239	    if invalid is not None:
   240	        return invalid
   241	    return json.dumps(_STORE_ACTIONS[action][0](store, target, content, old_text), ensure_ascii=False)
   242	
   243	
   244	def get_builtin_memory_config(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
   245	    """Normalized ``memory`` config section ({} when missing/malformed → flags default to
   246	    enabled). ``agent_init`` reads the same section so availability and store cannot diverge."""
   247	    if config is None:
   248	        try:
   249	            from hermes_cli.config import load_config_readonly
   250	            config = load_config_readonly()
   251	        except Exception:
   252	            logger.debug("Could not read memory config for availability", exc_info=True)
   253	            return {}
   254	    section = config.get("memory") if isinstance(config, dict) else None
   255	    return section if isinstance(section, dict) else {}
   256	
   257	
   258	def get_builtin_memory_store_flags(config: Optional[Dict[str, Any]] = None) -> Tuple[bool, bool]:
   259	    """Return ``(memory_enabled, user_profile_enabled)`` from resolved config."""
   260	    section = get_builtin_memory_config(config)
   261	    return tuple(is_truthy_value(section.get(k), default=True) for k in ("memory_enabled", "user_profile_enabled"))
   262	
   263	
   264	@no_cache_check_fn
   265	def check_memory_requirements() -> bool:
   266	    """Snapshot store flags and report whether the built-in tool is available."""
   267	    _memory_surface_flags.set(None)
   268	    flags = get_builtin_memory_store_flags()
   269	    _memory_surface_flags.set(flags)
   270	    return flags[0] or flags[1]
   271	
   272	
   273	def _memory_target_error(store: "MemoryStore", target: str) -> Optional[Dict[str, Any]]:
   274	    """Return a shared validation error for an invalid or disabled target."""
   275	    if target not in {"memory", "user"}:
   276	        from tools.registry import _bound_error_text
   277	        return {"success": False,
   278	                "error": _bound_error_text(f"Invalid memory target '{target}'. Use 'memory' or 'user'.")}
   279	    if store.target_enabled(target):
   280	        return None
   281	    label = "USER.md" if target == "user" else "MEMORY.md"
   282	    return {"success": False, "error": f"Built-in {label} writes are disabled in memory config.", "target": target}
   283	
   284	
   285	def apply_memory_pending(payload: Dict[str, Any], store: "MemoryStore") -> Dict[str, Any]:
   286	    """Replay a staged write against the store, bypassing the gate (/memory approve). A
   287	    replace/remove applies to exactly its pinned ``matched_entry`` or is refused; a record
   288	    staged before pinning has no verifiable target, so it is refused rather than replayed by
   289	    old_text (which could hit a newer entry the approver never saw)."""
   290	    action, target = payload.get("action"), payload.get("target", "memory")
   291	    target_error = _memory_target_error(store, target)
   292	    if target_error is not None:
   293	        return target_error
   294	    if any(not op.get("matched_entry") for op in destructive_ops(payload)):
   295	        return {"success": False, "error": "This destructive pending write predates entry pinning and cannot be "
   296	                                           "verified; nothing was applied. Reject it and recreate the change."}
   297	    if action == "batch":
   298	        return store.apply_batch(target, payload.get("operations") or [])
   299	    if action not in _STORE_ACTIONS:
   300	        return {"success": False, "error": f"Unknown staged action '{action}'."}
   301	    return _STORE_ACTIONS[action][0](store, target, payload.get("content") or "", payload.get("old_text") or "",
   302	                                     payload.get("matched_entry"))
   303	
   304	
   305	MEMORY_SCHEMA = {
   306	    "name": "memory",
   307	    "description": (
   308	        "Save durable facts to persistent memory that survive across sessions. Memory is "
   309	        "injected into every future turn, so keep entries compact and high-signal.\n\n"
   310	        "HOW: make ALL your changes in ONE call via an 'operations' array (each item: "
   311	        "{action, content?, old_text?}). The batch applies atomically and the char limit is "
   312	        "checked only on the FINAL result — so a single call can remove/replace stale entries "
   313	        "to free room AND add new ones, even when an add alone would overflow. The response "
   314	        "reports current/limit chars and confirms completion; one batch call finishes the "
   315	        "update, so don't repeat it. Use the bare action/content/old_text fields only for a "
   316	        "single lone change.\n\n"
   317	        "WHEN: only for facts that apply to EVERY session regardless of task: who the user "
   318	        "is, stable environment facts, standing conventions with no task home. Anything "
   319	        "learned while doing a task (procedures, pitfalls, and the user's preferences and "
   320	        "corrections for that kind of work) belongs in the task's skill via skill_manage, "
   321	        "where it loads only when relevant; memory is injected into every turn and must "
   322	        "stay small.\n\n"
   323	        "IF FULL: an add is rejected with the current entries shown. Reissue as ONE batch that "
   324	        "removes or shortens enough stale entries and adds the new one together.\n\n"
   325	        "TARGETS: 'user' = who the user is (name, role, preferences, style). 'memory' = your "
   326	        "notes (environment, conventions, tool quirks, lessons).\n\n"
   327	        "SKIP: trivial/obvious info, easily re-discovered facts, raw data dumps, task progress, "
   328	        "completed-work logs, temporary TODO state (use session_search for those). Reusable "
   329	        "procedures belong in a skill, not memory."
   330	    ),
   331	    "parameters": {
   332	        "type": "object",
   333	        "properties": {
   334	            "action": {
   335	                "type": "string",
   336	                "enum": ["add", "replace", "remove"],
   337	                "description": "The action to perform (single-op shape). Omit when using 'operations'."
   338	            },
   339	            "target": {
   340	                "type": "string",
   341	                "enum": ["memory", "user"],
   342	                "description": "Which memory store: 'memory' for personal notes, 'user' for user profile."
   343	            },
   344	            "content": {
   345	                "type": "string",
   346	                "description": "The entry content. Required for 'add' and 'replace'. For 'replace' it is the COMPLETE new entry text: the whole matched entry is overwritten, so include everything you want to keep. Alias: 'new_text' is also accepted (same full-entry meaning)."
   347	            },
   348	            "old_text": {
   349	                "type": "string",
   350	                "description": "REQUIRED for 'replace' and 'remove' (single-op shape): a short unique substring IDENTIFYING the existing entry to modify -- it locates the entry, it is not spliced out. Omit only for 'add'."
   351	            },
   352	            "new_text": {
   353	                "type": "string",
   354	                "description": "Alias for 'content' (single-op shape): the COMPLETE new entry for 'replace', not a patch of old_text. If both are set, 'content' wins."
   355	            },
   356	            "operations": {
   357	                "type": "array",
   358	                "description": (
   359	                    "Batch shape: a list of operations applied atomically in one call "
   360	                    "against the final char budget. Preferred when making multiple changes "
   361	                    "or consolidating to make room. Each item is {action, content?, old_text?}."
   362	                ),
   363	                "items": {
   364	                    "type": "object",
   365	                    "properties": {
   366	                        "action": {"type": "string", "enum": ["add", "replace", "remove"]},
   367	                        "content": {"type": "string", "description": "Entry content for add/replace. For replace, the COMPLETE new entry (whole entry is overwritten). Alias: 'new_text'."},
   368	                        "new_text": {"type": "string", "description": "Alias for 'content' in a batch op."},
   369	                        "old_text": {"type": "string", "description": "Substring identifying the entry for replace/remove."},
   370	                    },
   371	                    "required": ["action"],
   372	                },
   373	            },
   374	        },
   375	        "required": ["target"],
   376	    },
   377	}
   378	
   379	
   380	# Schema text when only one built-in store is enabled: (target description, TARGETS replacement).
   381	_SINGLE_TARGET_TEXT = {
   382	    ("memory",): ("The enabled built-in store: 'memory' for personal notes.",
   383	                  "TARGET: only 'memory' is enabled for personal notes (environment, conventions, "
   384	                  "tool quirks, lessons)."),
   385	    ("user",): ("The enabled built-in store: 'user' for user profile.",
   386	                "TARGET: only 'user' is enabled for user profile facts (name, role, preferences, style).")}
   387	
   388	
   389	def _build_memory_schema_overrides() -> Dict[str, Any]:
   390	    """Narrow the advertised target surface using the availability snapshot."""
   391	    flags = _memory_surface_flags.get() or get_builtin_memory_store_flags()
   392	    _memory_surface_flags.set(None)
   393	    targets = [t for t, on in zip(("memory", "user"), flags) if on]
   394	    parameters = copy.deepcopy(MEMORY_SCHEMA["parameters"])
   395	    target_schema, description = parameters["properties"]["target"], MEMORY_SCHEMA["description"]
   396	    target_schema["enum"] = targets
   397	    if narrowed := _SINGLE_TARGET_TEXT.get(tuple(targets)):
   398	        target_schema["description"], replacement = narrowed
   399	        description = description.replace(
   400	            "TARGETS: 'user' = who the user is (name, role, preferences, style). 'memory' = your "
   401	            "notes (environment, conventions, tool quirks, lessons).", replacement)
   402	    return {"description": description, "parameters": parameters}
   403	
   404	
   405	from tools.registry import registry, tool_error  # noqa: E402  (registration at import time)
   406	
   407	registry.register(
   408	    name="memory",
   409	    toolset="memory",
   410	    schema=MEMORY_SCHEMA,
   411	    handler=lambda args, **kw: memory_tool(
   412	        action=args.get("action", ""), target=args.get("target", "memory"), store=kw.get("store"),
   413	        **{k: args.get(k) for k in ("content", "old_text", "new_text", "operations")}),
   414	    check_fn=check_memory_requirements,
   415	    emoji="🧠",
   416	    dynamic_schema_overrides=_build_memory_schema_overrides)
   417	
   418	
   419	# ---- BEGIN PLUGIN-COMPAT (revert-scheduled; see COMPAT_MANIFEST.md) ----
   420	# Names external plugins imported from this module before the Sep 2026 decomposition.
   421	# Internal code MUST NOT use these (scripts/check_compat_pointers.py fails CI if it does).
   422	# The whole block is removed by reverting the commit that added it.
   423	from contextlib import contextmanager  # noqa: F401,E402
   424	import time  # noqa: F401,E402
   425	
   426	
   427	_PLUGIN_COMPAT_LAZY = {
   428	    'atomic_write_text': ('utils', 'atomic_write_text'),
   429	}
   430	
   431	
   432	def __getattr__(name):  # PEP 562 — lazy so no import cycles
   433	    target = _PLUGIN_COMPAT_LAZY.get(name)
   434	    if target is None:
   435	        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
   436	    import importlib
   437	    from hermes_cli.plugin_compat import warn_once
   438	    warn_once(__name__, name, *target)
   439	    return getattr(importlib.import_module(target[0]), target[1])
   440	# ---- END PLUGIN-COMPAT ----
