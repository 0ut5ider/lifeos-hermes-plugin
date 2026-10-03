     1	"""User-initiated edit/delete for journey nodes (learned skills + memories).
     2	
     3	Node ids (from ``agent.learning_graph``): skills → the skill name; memories →
     4	``memory:<source>:<index>:<fingerprint>`` (``source`` = ``memory`` for MEMORY.md /
     5	``profile`` for USER.md; ``index`` = position in the combined card list, MEMORY.md
     6	first; ``fingerprint`` = digest of the card's text, so the entry the user clicked is
     7	still nameable once the list has shifted). Ids from an older graph carry no
     8	fingerprint and resolve by position alone.
     9	Shared by CLI ``hermes journey``, the TUI ``/journey`` overlay and the desktop.
    10	Deleting a skill *archives* it (``hermes curator restore`` recovers it);
    11	deleting a memory rewrites its file under the memory tool's lock.
    12	"""
    13	
    14	from __future__ import annotations
    15	
    16	from pathlib import Path
    17	from typing import Any, Callable
    18	
    19	_MEMORY_FILES = {"memory": "MEMORY.md", "profile": "USER.md"}
    20	_STORE_TARGETS = {"memory": "memory", "profile": "user"}  # journey source -> MemoryStore target
    21	
    22	
    23	def parse_node_kind(node_id: str) -> str:
    24	    return "memory" if node_id.startswith("memory:") else "skill"
    25	
    26	
    27	def _parse_memory_id(node_id: str) -> tuple[str, int, str]:
    28	    """``memory:<source>:<index>[:<fingerprint>]`` → (source, global_index, fingerprint).
    29	
    30	    The fingerprint is empty for an id minted before the graph carried one."""
    31	    parts = node_id.split(":")
    32	    try:
    33	        if len(parts) not in (3, 4) or parts[0] != "memory" or parts[1] not in _MEMORY_FILES:
    34	            raise ValueError
    35	        return parts[1], int(parts[2]), parts[3] if len(parts) == 4 else ""
    36	    except ValueError as exc:
    37	        raise ValueError(f"bad memory node id: {node_id!r}") from exc
    38	
    39	
    40	def _resolve_fingerprint(chunks: list[str], fingerprint: str) -> int | None:
    41	    """Index of the first entry in *chunks* whose text carries *fingerprint*, or None when gone.
    42	
    43	    The text names the entry, so a list that shifted under the user (an earlier entry removed
    44	    between the graph being drawn and the edit being submitted) still resolves to the card they
    45	    clicked. Identical entries are one entry to the memory store (it collapses byte-identical
    46	    copies on every mutation), so the first match is the entry.
    47	    """
    48	    from agent.learning_graph import memory_fingerprint
    49	
    50	    return next((i for i, chunk in enumerate(chunks) if memory_fingerprint(chunk) == fingerprint), None)
    51	
    52	
    53	def _locate_memory(node_id: str) -> tuple[Path, list[str], int]:
    54	    """Resolve a memory node id to (file, all §-delimited entries, local index).
    55	    Entries come from ``MemoryStore._read_file`` — the memory tool's own parser. A
    56	    fingerprinted id resolves by the entry's text; a legacy id by position (a profile
    57	    card's local index is its global index minus the MEMORY.md card count). Read-only
    58	    view: mutations resolve the id again INSIDE ``_mutate_memory``'s lock."""
    59	    from hermes_constants import get_hermes_home
    60	    from tools.memory_tool import MemoryStore
    61	
    62	    source, gidx, fingerprint = _parse_memory_id(node_id)
    63	    path = get_hermes_home() / "memories" / _MEMORY_FILES[source]
    64	    if not path.exists():
    65	        raise ValueError(f"{path.name} not found")
    66	    chunks = MemoryStore._read_file(path)
    67	    if fingerprint:
    68	        local = _resolve_fingerprint(chunks, fingerprint)
    69	        if local is None:
    70	            raise ValueError("memory node id is stale — refresh the graph")
    71	        return path, chunks, local
    72	    from agent.learning_graph import _memory_cards
    73	
    74	    cards = _memory_cards()
    75	    if not 0 <= gidx < len(cards):
    76	        raise IndexError(f"memory index {gidx} out of range")
    77	    if cards[gidx].get("source") != source:
    78	        raise ValueError("memory node id is stale — refresh the graph")
    79	    local = gidx if source == "memory" else gidx - sum(1 for c in cards if c.get("source") == "memory")
    80	    if not 0 <= local < len(chunks):
    81	        raise ValueError("memory node id is stale — refresh the graph")
    82	    return path, chunks, local
    83	
    84	
    85	def _mutate_memory(node_id: str, replacement: str | None) -> dict[str, Any]:
    86	    """Replace (or, with ``replacement=None``, remove) the entry *node_id* names, through
    87	    ``MemoryStore._mutate`` — the memory tool's cross-process lock, re-read under lock and
    88	    drift guard (``.bak`` snapshot + refusal when the file wouldn't round-trip). The file is
    89	    shared with the live agent, so a read-modify-write from an unlocked snapshot silently
    90	    dropped whatever the agent stored in between and reformatted hand-edited files
    91	    (#119668). The id is resolved to its entry text INSIDE the lock and matched by exact
    92	    text against the store's re-read entries; a target gone under the lock is refused."""
    93	    from tools.memory_tool import load_on_disk_store
    94	
    95	    source, _, _ = _parse_memory_id(node_id)
    96	    name = _MEMORY_FILES[source]
    97	    message = f"deleted memory from {name}" if replacement is None else f"updated memory in {name}"
    98	
    99	    def _apply(entries, limit):
   100	        from tools.memory_tool import ENTRY_DELIMITER
   101	
   102	        _, chunks, local = _locate_memory(node_id)
   103	        text = chunks[local].strip()
   104	        if text not in entries:
   105	            return {"success": False, "error": "memory node id is stale — refresh the graph"}
   106	        idx = entries.index(text)
   107	        new_entries = entries[:idx] + ([] if replacement is None else [replacement]) + entries[idx + 1:]
   108	        # Same cap the memory tool enforces on replace (never on remove: deleting is how a file
   109	        # already over its total gets back under it). An over-limit entry reads as external drift
   110	        # to every later mutation, so the tool's own remove/replace refuse until hand-fixed.
   111	        if replacement is not None and (total := len(ENTRY_DELIMITER.join(new_entries))) > limit:
   112	            return {"success": False,
   113	                    "error": f"Replacement would put memory at {total:,}/{limit:,} chars. Shorten the new content."}
   114	        return new_entries, message
   115	
   116	    result = load_on_disk_store()._mutate(_STORE_TARGETS[source], _apply)
   117	    if not result.get("success"):
   118	        return {"ok": False, "message": result.get("error", f"{name} write failed")}
   119	    return {"ok": True, "message": message}
   120	
   121	
   122	def _clear_skill_cache() -> None:
   123	    try:
   124	        from agent.prompt_builder import clear_skills_system_prompt_cache
   125	        clear_skills_system_prompt_cache(clear_snapshot=True)
   126	    except Exception:
   127	        pass
   128	
   129	
   130	def _dispatch(node_id: str, memory_fn: Callable, skill_fn: Callable, *args) -> dict[str, Any]:
   131	    try:
   132	        return (memory_fn if parse_node_kind(node_id) == "memory" else skill_fn)(node_id, *args)
   133	    except (ValueError, IndexError) as exc:
   134	        return {"ok": False, "message": str(exc)}
   135	
   136	
   137	# ── Inspect (edit prefill) ──────────────────────────────────────────────────
   138	
   139	def node_detail(node_id: str) -> dict[str, Any]:
   140	    """Current content for an edit prefill. ``content`` is the full SKILL.md
   141	    (skills) or the raw memory chunk (memories)."""
   142	    return _dispatch(node_id, _memory_detail, _skill_detail)
   143	
   144	
   145	def _memory_detail(node_id: str) -> dict[str, Any]:
   146	    _, chunks, local = _locate_memory(node_id)
   147	    body = chunks[local].strip()
   148	    return {"ok": True, "kind": "memory", "id": node_id, "label": body.splitlines()[0][:80], "content": body}
   149	
   150	
   151	def _skill_detail(node_id: str) -> dict[str, Any]:
   152	    from tools.skill_manager_tool import _find_skill
   153	    found = _find_skill(node_id)
   154	    if not found:
   155	        return {"ok": False, "message": f"skill '{node_id}' not found"}
   156	    skill_md = Path(found["path"]) / "SKILL.md"
   157	    if not skill_md.exists():
   158	        return {"ok": False, "message": f"SKILL.md missing for '{node_id}'"}
   159	    return {"ok": True, "kind": "skill", "id": node_id, "label": node_id, "content": skill_md.read_text(encoding="utf-8-sig")}
   160	
   161	
   162	# ── Delete ──────────────────────────────────────────────────────────────────
   163	
   164	def delete_node(node_id: str) -> dict[str, Any]:
   165	    return _dispatch(node_id, _delete_memory, _delete_skill)
   166	
   167	
   168	def _delete_skill(name: str) -> dict[str, Any]:
   169	    from tools import skill_usage
   170	    # Pin must be respected by autonomous maintenance. The curator already skips pinned skills from every
   171	    # auto-transition; the background review fork is the same kind of autonomous, no-user-present actor, so
   172	    # it must not write to a pinned skill either (issue #25839). This is stricter than the foreground
   173	    # ``_pinned_guard`` (which only blocks deletion) precisely because there is no user in the loop to
   174	    # consent to an edit here.
   175	    if skill_usage.get_record(name).get("pinned"):
   176	        return {"ok": False, "message": f"'{name}' is pinned — unpin it first (hermes curator unpin {name})"}
   177	    ok, message = skill_usage.archive_skill(name)
   178	    if ok:
   179	        _clear_skill_cache()
   180	    return {"ok": ok, "message": f"archived '{name}' — restore with: hermes curator restore {name}" if ok else message}
   181	
   182	
   183	def _delete_memory(node_id: str) -> dict[str, Any]:
   184	    return _mutate_memory(node_id, None)
   185	
   186	
   187	# ── Edit ────────────────────────────────────────────────────────────────────
   188	
   189	def edit_node(node_id: str, content: str) -> dict[str, Any]:
   190	    return _dispatch(node_id, _edit_memory, _edit_skill, content)
   191	
   192	
   193	def _edit_skill(name: str, content: str) -> dict[str, Any]:
   194	    from tools.skill_manager_tool import _edit_skill as _do_edit
   195	    result = _do_edit(name, content)
   196	    if result.get("success"):
   197	        _clear_skill_cache()
   198	        return {"ok": True, "message": f"updated '{name}'"}
   199	    return {"ok": False, "message": result.get("error", "edit failed")}
   200	
   201	
   202	def _edit_memory(node_id: str, content: str) -> dict[str, Any]:
   203	    _parse_memory_id(node_id)  # id errors win over the empty-body message
   204	    body = content.strip()
   205	    if not body:
   206	        return {"ok": False, "message": "empty memory — use delete to remove it"}
   207	    return _mutate_memory(node_id, body)
