     1	"""Assemble the "learning made visible" graph for desktop.
     2	
     3	Scoped to what a user actually learns over time: non-base, learned/profile
     4	skills (agent-created or used) plus ``MEMORY.md`` / ``USER.md`` chunks as
     5	first-class nodes. Skill links come from declared ``related_skills``;
     6	memory→skill links are derived from lexical overlap.
     7	"""
     8	
     9	from __future__ import annotations
    10	
    11	import hashlib
    12	import json
    13	import re
    14	from collections import Counter
    15	from dataclasses import dataclass, field
    16	from datetime import datetime, timezone
    17	from pathlib import Path
    18	from typing import Any, Optional
    19	
    20	from hermes_constants import get_hermes_home
    21	
    22	_SKIP_PARTS = {".archive", ".hub", ".locks", "node_modules", ".git"}
    23	_USAGE_TS_KEYS = ("last_activity_at", "last_used_at", "last_viewed_at", "last_patched_at", "created_at")
    24	
    25	
    26	@dataclass
    27	class SkillNode:
    28	    name: str
    29	    category: str
    30	    source: str = "profile"
    31	    timestamp: Optional[int] = None
    32	    use_count: int = 0
    33	    state: str = "active"
    34	    created_by: Optional[str] = None
    35	    pinned: bool = False
    36	    related: list[str] = field(default_factory=list)
    37	
    38	
    39	def _fm_field(fm: dict[str, Any], key: str) -> Any:
    40	    """Top-level ``key`` or ``metadata.hermes.<key>``; tolerant of the string-valued
    41	    frontmatter that ``parse_frontmatter``'s malformed-YAML fallback produces."""
    42	    if fm.get(key):
    43	        return fm[key]
    44	    meta = fm.get("metadata")
    45	    hermes = meta.get("hermes") if isinstance(meta, dict) else None
    46	    return hermes.get(key) if isinstance(hermes, dict) else None
    47	
    48	
    49	def _related(fm: dict[str, Any]) -> list[str]:
    50	    raw = _fm_field(fm, "related_skills")
    51	    raw = raw.strip("[]").split(",") if isinstance(raw, str) else raw
    52	    return [str(r).strip() for r in raw if str(r).strip()] if isinstance(raw, list) else []
    53	
    54	
    55	def _load_usage() -> dict[str, dict[str, Any]]:
    56	    try:
    57	        from tools.skill_usage import load_usage
    58	        return load_usage()
    59	    except Exception:
    60	        try:
    61	            return json.loads((get_hermes_home() / "skills" / ".usage.json").read_text(encoding="utf-8-sig"))
    62	        except Exception:
    63	            return {}
    64	
    65	
    66	def _to_int_ts(value: Any) -> Optional[int]:
    67	    """Epoch seconds from a number, numeric string, or ISO timestamp; None otherwise."""
    68	    try:
    69	        if value is None or not (s := str(value).strip()):
    70	            return None
    71	        if isinstance(value, (int, float)):
    72	            return int(value)
    73	        try:
    74	            return int(float(s))
    75	        except ValueError:
    76	            parsed = datetime.fromisoformat(s.replace("Z", "+00:00"))
    77	            return int((parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)).timestamp())
    78	    except Exception:
    79	        return None
    80	
    81	
    82	def build_skill_nodes(skill_roots: list[tuple[str, Path]]) -> dict[str, SkillNode]:
    83	    usage = _load_usage()
    84	    nodes: dict[str, SkillNode] = {}
    85	    for source, root in skill_roots:
    86	        for skill_md in root.rglob("SKILL.md") if root.exists() else ():
    87	            if _SKIP_PARTS.intersection(skill_md.parts):
    88	                continue
    89	            try:
    90	                text = skill_md.read_text(encoding="utf-8-sig")[:4000]
    91	            except OSError:
    92	                continue
    93	            try:
    94	                from agent.skill_utils import parse_frontmatter
    95	                fm = parse_frontmatter(text)[0] or {}
    96	            except Exception:
    97	                fm = {}
    98	            name = str(fm.get("name") or skill_md.parent.name).strip()
    99	            if not name or name in nodes:
   100	                continue
   101	            rec, cat, parts = usage.get(name, {}), _fm_field(fm, "category"), skill_md.parts  # …/skills/<category>/<skill>/SKILL.md
   102	            usage_ts = next((ts for ts in (_to_int_ts(rec.get(k)) for k in _USAGE_TS_KEYS) if ts is not None), None)
   103	            nodes[name] = SkillNode(
   104	                name=name, category=str(cat) if cat else parts[-3] if len(parts) >= 3 else "general", source=source,
   105	                timestamp=usage_ts or _to_int_ts(skill_md.stat().st_mtime),
   106	                use_count=int(rec.get("use_count", 0) or 0), state=str(rec.get("state", "active") or "active"),
   107	                created_by=rec.get("created_by"), pinned=bool(rec.get("pinned", False)), related=_related(fm),
   108	            )
   109	    return nodes
   110	
   111	
   112	def build_edges(nodes: dict[str, SkillNode]) -> list[tuple[str, str]]:
   113	    """Undirected related_skills edges where BOTH endpoints exist (deduped, first-seen order)."""
   114	    return list(dict.fromkeys(
   115	        (min(node.name, target), max(node.name, target)) for node in nodes.values() for target in node.related if target in nodes and target != node.name
   116	    ))
   117	
   118	
   119	def density_stats(nodes: dict[str, SkillNode], edges: list[tuple[str, str]]) -> dict[str, Any]:
   120	    linked, cats, n = {x for edge in edges for x in edge}, Counter(x.category for x in nodes.values()), len(nodes) or 1
   121	    return {
   122	        "nodes": len(nodes), "related_edges": len(edges), "edges_per_node": round(len(edges) / n, 3),
   123	        "linked_nodes": len(linked), "isolated_pct": round(100 * (n - len(linked)) / n, 1), "categories": len(cats),
   124	        "agent_created": sum(1 for x in nodes.values() if x.created_by == "agent"),
   125	        "used": sum(1 for x in nodes.values() if x.use_count > 0),
   126	        "top_categories": sorted(cats.items(), key=lambda kv: -kv[1])[:8],
   127	    }
   128	
   129	
   130	def memory_fingerprint(entry: str) -> str:
   131	    """Short stable digest of a memory entry's TEXT, carried in the node id.
   132	
   133	    A journey card is identified by what it says, not by where it sat: an earlier entry can be
   134	    removed (an agent ``memory_tool`` remove mid-turn, a Journey delete without a refetch)
   135	    between the graph being drawn and the user submitting an edit, and a bare index then names
   136	    somebody else's card (#119668).
   137	    Cards and the mutation path both read entries through ``MemoryStore._read_file``, so the
   138	    same entry digests the same on both sides (a BOM'd file included).
   139	    """
   140	    return hashlib.sha256(entry.strip().encode("utf-8")).hexdigest()[:12]
   141	
   142	
   143	def memory_node_id(card: dict[str, Any], index: int) -> str:
   144	    """``memory:<source>:<index>:<fingerprint>`` — position for the occurrence, text for identity."""
   145	    return f"memory:{card['source']}:{index}:{card['fingerprint']}"
   146	
   147	
   148	def _memory_cards() -> list[dict[str, Any]]:
   149	    """``MEMORY.md`` / ``USER.md`` entries as the memory tool parses them; every
   150	    entry becomes one card (MEMORY.md cards first, then USER.md)."""
   151	    from tools.memory_tool import MemoryStore
   152	
   153	    base = get_hermes_home() / "memories"
   154	    cards: list[dict[str, Any]] = []
   155	    for fname, source in (("MEMORY.md", "memory"), ("USER.md", "profile")):
   156	        path = base / fname
   157	        try:
   158	            file_ts = _to_int_ts(path.stat().st_mtime)
   159	        except OSError:
   160	            continue
   161	        # The store's own parser (utf-8-sig, same delimiter): a hand-rolled split kept a Notepad
   162	        # BOM glued to the first entry, so its fingerprint never matched the store's and the card
   163	        # was "stale" forever.
   164	        for chunk_idx, chunk in enumerate(MemoryStore._read_file(path)):
   165	            first = chunk.splitlines()[0].strip().lstrip("# ").strip()
   166	            cards.append({
   167	                "source": source, "timestamp": file_ts + chunk_idx if file_ts is not None else None,
   168	                "title": (first[:80] + "…") if len(first) > 80 else first, "body": chunk[:1200],
   169	                # Digest the WHOLE chunk, not the truncated ``body`` a long memory renders with.
   170	                "fingerprint": memory_fingerprint(chunk),
   171	            })
   172	    return cards
   173	
   174	
   175	def _tokenize(text: str) -> set[str]:
   176	    return {t for t in re.split(r"[^a-z0-9]+", text.lower()) if len(t) >= 3}
   177	
   178	
   179	def _memory_skill_edges(memory_cards: list[dict[str, Any]], skills: list[SkillNode]) -> list[tuple[str, str]]:
   180	    """Top-4 lexically overlapping skills per memory card (name hit weighs 6)."""
   181	    edges: list[tuple[str, str]] = []
   182	    skill_meta = [(s.name, _tokenize(s.name), s.name.lower()) for s in skills]
   183	    for idx, card in enumerate(memory_cards):
   184	        text = f"{card.get('title', '')}\n{card.get('body', '')}".lower()
   185	        text_tokens = _tokenize(text)
   186	        scored = sorted(
   187	            ((score, name) for name, tokens, name_lower in skill_meta if (score := (6 if name_lower in text else 0) + len(tokens & text_tokens)) > 0),
   188	            key=lambda x: (-x[0], x[1]),
   189	        )
   190	        edges.extend((memory_node_id(card, idx), name) for _, name in scored[:4])
   191	    return edges
   192	
   193	
   194	def _has_learning_signal(node: SkillNode) -> bool:
   195	    """Graph-worthy: agent-created, user-taught (/learn), or actually used.
   196	
   197	    ``created_by="learn"`` is a learning-signal marker only — curator management stays keyed
   198	    strictly on ``"agent"`` (see ``tools.skill_usage._is_curator_managed_record``).
   199	    """
   200	    return node.created_by in {"agent", "learn"} or node.use_count > 0
   201	
   202	
   203	def build_learning_graph() -> dict[str, Any]:
   204	    """Full payload for the desktop learning panel: non-base skills with real
   205	    learning signal (agent-created or used) plus memory chunks as graph nodes."""
   206	    roots = [("base", Path(__file__).resolve().parent.parent / "skills"), ("profile", get_hermes_home() / "skills")]
   207	    learned_skills = {
   208	        name: node for name, node in build_skill_nodes(roots).items()
   209	        if node.source != "base" and _has_learning_signal(node)
   210	    }
   211	    skill_edges, memory_cards = build_edges(learned_skills), _memory_cards()
   212	    memory_edges = _memory_skill_edges(memory_cards, list(learned_skills.values()))
   213	    clusters = Counter(node.category for node in learned_skills.values())
   214	    if memory_cards:
   215	        clusters["memory"] = len(memory_cards)
   216	
   217	    graph_nodes = [
   218	        {
   219	            "id": n.name, "label": n.name, "kind": "skill", "timestamp": n.timestamp, "category": n.category,
   220	            "useCount": n.use_count, "state": n.state, "createdBy": n.created_by, "pinned": n.pinned,
   221	        }
   222	        for n in learned_skills.values()
   223	    ] + [
   224	        {
   225	            "id": memory_node_id(card, i), "label": card["title"], "kind": "memory",
   226	            "memorySource": card["source"], "timestamp": card.get("timestamp"), "category": "memory",
   227	            "useCount": 0, "state": "active", "createdBy": "memory", "pinned": False,
   228	        }
   229	        for i, card in enumerate(memory_cards)
   230	    ]
   231	    return {
   232	        "nodes": graph_nodes,
   233	        "edges": [{"source": a, "target": b} for a, b in skill_edges + memory_edges],
   234	        "clusters": [{"category": c, "count": n} for c, n in sorted(clusters.items(), key=lambda kv: -kv[1])],
   235	        "memory": memory_cards,
   236	        "stats": {
   237	            **density_stats(learned_skills, skill_edges),
   238	            "memory_nodes": len(memory_cards), "memory_skill_edges": len(memory_edges), "learned_skills": len(learned_skills),
   239	        },
   240	    }
