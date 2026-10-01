     1	"""MemoryManager — fans the agent's memory hooks out to registered providers.
     2	
     3	The builtin provider is always allowed; only ONE external plugin provider may be
     4	registered at a time (tool-schema bloat, conflicting backends).
     5	"""
     6	
     7	from __future__ import annotations
     8	
     9	import contextvars
    10	import inspect
    11	import json
    12	import logging
    13	import re
    14	import threading
    15	from concurrent.futures import Future, ThreadPoolExecutor, wait
    16	from functools import partial
    17	from typing import Any, Callable, Dict, List, Optional
    18	
    19	from agent.memory_provider import MemoryProvider, PRE_COMPRESS_CHECKPOINT_API_VERSION, ctx_bound, spawn_context_thread
    20	from agent.skill_commands import extract_user_instruction_from_skill_message
    21	from tools.hook_output_spill import get_spill_config, spill_if_oversized
    22	from tools.registry import tool_error
    23	
    24	logger = logging.getLogger(__name__)
    25	
    26	# Providers that predate the checkpoint-API attribute are on the best-effort v1 contract.
    27	_LEGACY_PRE_COMPRESS_API_VERSION = 1
    28	
    29	# shutdown_all() drain bound; workers are daemon threads so a wedged provider never
    30	# blocks interpreter exit.
    31	_SYNC_DRAIN_TIMEOUT_S = 5.0
    32	_EXTERNAL_PREFETCH_TIMEOUT_S = 8.0
    33	
    34	
    35	# -- Signature introspection (providers are duck-typed; call shapes vary) -----
    36	
    37	def _signature_params(fn: Callable[..., Any]):
    38	    """``fn``'s parameter mapping, or None when uninspectable (C callables, exotic proxies)."""
    39	    try:
    40	        return inspect.signature(fn).parameters
    41	    except (TypeError, ValueError):
    42	        return None
    43	
    44	
    45	def _has_var_kwargs(params) -> bool:
    46	    return any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values())
    47	
    48	
    49	def _accepts_require_checkpoint(fn: Callable[..., Any]) -> bool:
    50	    """True if ``fn`` can receive the ``require_checkpoint`` keyword (unreadable signatures -> False).
    51	
    52	    Bare-shape v2 providers (``on_pre_compress(self, messages)``) would raise TypeError on the
    53	    keyword, which the host would re-raise as a checkpoint failure despite a successful write.
    54	    """
    55	    params = _signature_params(fn)
    56	    if params is None:
    57	        return False
    58	    kind = getattr(params.get("require_checkpoint"), "kind", None)
    59	    return _has_var_kwargs(params) or kind in (inspect.Parameter.KEYWORD_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    60	
    61	
    62	# -- Tool-schema plumbing -----------------------------------------------------
    63	
    64	def normalize_tool_schema(schema: Any) -> Optional[Dict[str, Any]]:
    65	    """Return a bare function-tool dict with a resolvable top-level ``name``, else None.
    66	
    67	    Providers should return ``{"name", "description", "parameters"}`` but some return the
    68	    wrapped OpenAI form; wrapping that twice yields a nameless ``function`` and strict
    69	    providers (DeepSeek) reject the ENTIRE request, so both shapes are normalized here.
    70	    """
    71	    if not isinstance(schema, dict):
    72	        return None
    73	    if schema.get("type") == "function" and isinstance(schema.get("function"), dict):
    74	        schema = schema["function"]
    75	    name = schema.get("name", "")
    76	    return schema if name and isinstance(name, str) else None
    77	
    78	
    79	def memory_provider_tools_enabled(enabled_toolsets: Optional[List[str]], disabled_toolsets: Optional[List[str]] = None,
    80	                                  *, memory_tool_present: bool = False) -> bool:
    81	    """Return whether external memory-provider tools should be exposed."""
    82	    if disabled_toolsets and "memory" in disabled_toolsets:
    83	        return False
    84	    if memory_tool_present or enabled_toolsets is None:
    85	        return True
    86	    if not enabled_toolsets:
    87	        return False
    88	    if "memory" in enabled_toolsets:
    89	        return True
    90	    try:
    91	        from toolsets import resolve_toolset
    92	
    93	        return any("memory" in resolve_toolset(name) for name in enabled_toolsets)
    94	    except Exception:
    95	        logger.debug("Failed to resolve enabled toolsets for memory-provider tools", exc_info=True)
    96	        return False
    97	
    98	
    99	def _tool_name(tool: Any) -> Any:
   100	    return tool.get("function", {}).get("name") if isinstance(tool, dict) else None
   101	
   102	
   103	def memory_provider_tools_exposed(agent: Any) -> bool:
   104	    """Whether external memory-provider tools are exposed on ``agent``.
   105	
   106	    Same gate as ``inject_memory_provider_tools`` so a provider's ``system_prompt_block()``
   107	    never advertises tools absent from the tool surface.
   108	    """
   109	    tools = getattr(agent, "tools", None)
   110	    present = isinstance(tools, (list, tuple)) and any(_tool_name(t) == "memory" for t in tools)
   111	    enabled, disabled = getattr(agent, "enabled_toolsets", None), getattr(agent, "disabled_toolsets", None)
   112	    return memory_provider_tools_enabled(enabled, disabled, memory_tool_present=present)
   113	
   114	
   115	def inject_memory_provider_tools(agent: Any) -> int:
   116	    """Append external memory-provider tool schemas to an agent tool surface; return count added."""
   117	    memory_manager = getattr(agent, "_memory_manager", None)
   118	    tools = getattr(agent, "tools", None)
   119	    if not memory_manager or tools is None:
   120	        return 0
   121	
   122	    if not memory_provider_tools_exposed(agent):
   123	        # Say so once: a silent 0 leaves the provider looking "half on" with no clue which
   124	        # config key (platform_toolsets / disabled_toolsets) gated it.
   125	        # See #81014.
   126	        _providers = [p for p in getattr(memory_manager, "providers", None) or []
   127	                      if getattr(p, "name", "") != "builtin"]
   128	        if _providers:
   129	            logger.info(
   130	                "Memory provider(s) %s configured but the 'memory' toolset is "
   131	                "gated off for this session (platform_toolsets / "
   132	                "agent.disabled_toolsets) — provider tools and system-prompt "
   133	                "block are both withheld.",
   134	                [getattr(p, "name", type(p).__name__) for p in _providers],
   135	            )
   136	        return 0
   137	
   138	    get_schemas = getattr(memory_manager, "get_all_tool_schemas", None)
   139	    if not callable(get_schemas):
   140	        return 0
   141	
   142	    if getattr(agent, "valid_tool_names", None) is None:
   143	        agent.valid_tool_names = set()
   144	    existing_tool_names = {_tool_name(tool) for tool in tools if isinstance(tool, dict)}
   145	    added = 0
   146	    for raw_schema in get_schemas():
   147	        schema = normalize_tool_schema(raw_schema)
   148	        if schema is None:
   149	            logger.warning(
   150	                "Memory provider returned a tool schema with no resolvable "
   151	                "name; skipping to avoid poisoning the request (%r)", raw_schema,
   152	            )
   153	        elif schema["name"] not in existing_tool_names:
   154	            tools.append({"type": "function", "function": schema})
   155	            agent.valid_tool_names.add(schema["name"])
   156	            existing_tool_names.add(schema["name"])
   157	            added += 1
   158	    return added
   159	
   160	
   161	# -- Context fencing helpers --------------------------------------------------
   162	
   163	_FENCE_TAG_RE = re.compile(r'</?\s*memory-context\s*>', re.IGNORECASE)
   164	_INTERNAL_CONTEXT_RE = re.compile(r'<\s*memory-context\s*>[\s\S]*?</\s*memory-context\s*>', re.IGNORECASE)
   165	_INTERNAL_NOTE_RE = re.compile(
   166	    r'\[System note:\s*The following is recalled memory context,\s*NOT new user input\.\s*Treat as (?:informational background data|authoritative reference data[^\]]*)\.\]\s*',
   167	    re.IGNORECASE,
   168	)
   169	
   170	
   171	def sanitize_context(text: str) -> str:
   172	    """Strip fence tags, injected context blocks, and system notes from provider output."""
   173	    for pattern in (_INTERNAL_CONTEXT_RE, _INTERNAL_NOTE_RE, _FENCE_TAG_RE):
   174	        text = pattern.sub('', text)
   175	    return text
   176	
   177	
   178	class StreamingContextScrubber:
   179	    """Stateful scrubber for streaming text whose memory-context spans may straddle deltas.
   180	
   181	    ``sanitize_context`` needs both tags in one string, so a split span would leak to the UI;
   182	    this holds back partial-tag tails between ``feed()`` calls and drops span interiors.
   183	    One scrubber (or ``reset()``) per top-level response; call ``flush()`` at end of stream.
   184	    """
   185	
   186	    _OPEN_TAG = "<memory-context>"
   187	    _CLOSE_TAG = "</memory-context>"
   188	
   189	    def __init__(self) -> None:
   190	        self.reset()
   191	
   192	    def reset(self) -> None:
   193	        self._in_span: bool = False
   194	        self._buf: str = ""
   195	        self._at_block_boundary: bool = True
   196	
   197	    def feed(self, text: str) -> str:
   198	        """Return the visible portion of ``text``; a possible partial tag tail is held for the next call."""
   199	        if not text:
   200	            return ""
   201	        buf = self._buf + text
   202	        self._buf = ""
   203	        out: list[str] = []
   204	        while buf:
   205	            if self._in_span:
   206	                tag = self._CLOSE_TAG
   207	                idx = buf.lower().find(tag)
   208	                held = self._max_partial_suffix(buf, tag)  # potential partial close tag
   209	            else:
   210	                tag = self._OPEN_TAG
   211	                idx = self._find_boundary_open_tag(buf)
   212	                # A complete boundary tag at the buffer end is held until the next char confirms it.
   213	                n = len(tag)
   214	                pending = n if buf.lower().endswith(tag) and self._ends_at_block_boundary(buf[:-n]) else 0
   215	                held = pending or self._max_partial_suffix(buf, tag)
   216	            if idx == -1:
   217	                # Hold back the possible partial tag; inside a span the rest is dropped.
   218	                if not self._in_span:
   219	                    self._append_visible(out, buf[:-held] if held else buf)
   220	                self._buf = buf[-held:] if held else ""
   221	                break
   222	            if not self._in_span:
   223	                self._append_visible(out, buf[:idx])
   224	            buf = buf[idx + len(tag):]
   225	            self._in_span = not self._in_span
   226	        return "".join(out)
   227	
   228	    def flush(self) -> str:
   229	        """Emit the held-back tail at end-of-stream; inside an unterminated span it is discarded
   230	        (leaking partial memory context is worse than a truncated answer)."""
   231	        tail = "" if self._in_span else self._buf
   232	        self._buf = ""
   233	        self._in_span = False
   234	        return tail
   235	
   236	    @staticmethod
   237	    def _max_partial_suffix(buf: str, tag: str) -> int:
   238	        """Length of the longest buf-suffix that is a (case-insensitive) prefix of ``tag``, else 0."""
   239	        tag_lower, buf_lower = tag.lower(), buf.lower()
   240	        span = range(min(len(buf_lower), len(tag_lower) - 1), 0, -1)
   241	        return next((i for i in span if tag_lower.startswith(buf_lower[-i:])), 0)
   242	
   243	    def _find_boundary_open_tag(self, buf: str) -> int:
   244	        """Find an opening fence only when it starts a block-like span (own line, newline after)."""
   245	        buf_lower, tag_len = buf.lower(), len(self._OPEN_TAG)
   246	        idx = buf_lower.find(self._OPEN_TAG)
   247	        while idx != -1:
   248	            after_idx = idx + tag_len
   249	            if self._ends_at_block_boundary(buf[:idx]) and after_idx < len(buf) and buf[after_idx] in "\r\n":
   250	                return idx
   251	            idx = buf_lower.find(self._OPEN_TAG, idx + 1)
   252	        return -1
   253	
   254	    def _ends_at_block_boundary(self, text: str) -> bool:
   255	        """Whether emitting ``text`` leaves the stream at a line start (blank tail after the last newline;
   256	        no newline at all -> only whitespace and already at a boundary)."""
   257	        head, sep, tail = text.rpartition("\n")
   258	        return tail.strip() == "" and (bool(sep) or self._at_block_boundary)
   259	
   260	    def _append_visible(self, out: list[str], text: str) -> None:
   261	        if text:
   262	            out.append(text)
   263	            self._at_block_boundary = self._ends_at_block_boundary(text)
   264	
   265	
   266	# A markdown bullet: a marker, whitespace, then content. The whitespace matters — it is what keeps
   267	# ``**Preferences**`` (a bold heading) and ``*emphasis*`` out of the rule.
   268	_RECALL_BULLET_RE = re.compile(r"[-*+]\s+\S")
   269	
   270	
   271	def _drop_repeated_recall_lines(text: str) -> str:
   272	    """Drop a recalled bullet that an EARLIER line of this same block already states.
   273	
   274	    Providers merge several stores (and this merges several providers), so one prefetch routinely
   275	    surfaces the same fact two or three times. A byte-identical repeat inside one block tells the
   276	    model nothing the block has not already said, and it is not free: the composed block is stamped
   277	    into the user row's ``api_content`` sidecar and replayed verbatim on every later request for as
   278	    long as that row is in context, so each duplicate is paid once per turn, forever.
   279	
   280	    The ``seen`` set is scoped per section — every non-bullet line at column 0 (a heading of any
   281	    style, a ``---`` rule, prose) starts a new one — so a repeat is only dropped when the SAME
   282	    section already states it.
   283	
   284	    Only a SELF-CONTAINED bullet is considered — a marker, whitespace, content, and no continuation
   285	    line indented beneath it. A bullet that carries continuation lines is never dropped and never
   286	    suppresses a later one, because two entries can share a headline and differ underneath it
   287	    (``- prefers draft PRs`` / ``  (logged 12 Jan, builtin)`` vs the same headline logged elsewhere):
   288	    dropping one would re-parent its provenance under the other and invent a record neither provider
   289	    reported. Headings — including ``**bold**`` ones — prose, blank lines, separators and numbered
   290	    items are left exactly as written.
   291	    """
   292	    lines = text.split("\n")
   293	    seen: set[str] = set()
   294	    kept: list[str] = []
   295	    for index, line in enumerate(lines):
   296	        stripped = line.strip()
   297	        # An indented line is a continuation of the bullet above it (nested child, provenance,
   298	        # wrapped prose). It never participates in dedupe and is never dropped.
   299	        if stripped and line[0].isspace():
   300	            kept.append(line)
   301	            continue
   302	        is_bullet = bool(_RECALL_BULLET_RE.match(stripped))
   303	        # Any column-0 non-bullet line (heading, rule, paragraph) opens a fresh dedupe scope.
   304	        if stripped and not is_bullet:
   305	            seen.clear()
   306	        if is_bullet:
   307	            following = lines[index + 1] if index + 1 < len(lines) else ""
   308	            carries_continuation = bool(following.strip()) and following[0].isspace()
   309	            if not carries_continuation:
   310	                if stripped in seen:
   311	                    continue
   312	                seen.add(stripped)
   313	        kept.append(line)
   314	    return "\n".join(kept)
   315	
   316	
   317	def build_memory_context_block(raw_context: str) -> str:
   318	    """Wrap prefetched memory in a fenced block with system note."""
   319	    if not raw_context or not raw_context.strip():
   320	        return ""
   321	    sanitized = sanitize_context(raw_context)
   322	    if sanitized != raw_context:
   323	        # Stays keyed on sanitization alone: a deduped bullet is routine, not a provider fault.
   324	        logger.warning("memory provider returned pre-wrapped context; stripped")
   325	    clean = _drop_repeated_recall_lines(sanitized)
   326	    return (
   327	        "<memory-context>\n"
   328	        "[System note: The following is recalled memory context, "
   329	        "NOT new user input. Treat as authoritative reference data — "
   330	        "this is the agent's persistent memory and should inform all responses.]\n\n"
   331	        f"{clean}\n"
   332	        "</memory-context>"
   333	    )
   334	
   335	
   336	class MemoryManager:
   337	    """Builtin provider (always first) plus at most one external provider.
   338	
   339	    Failures in one provider never block the other: every fan-out hook logs and
   340	    swallows per-provider exceptions.
   341	    """
   342	
   343	    def __init__(self, *, external_prefetch_timeout: Optional[float] = None) -> None:
   344	        self._providers: List[MemoryProvider] = []
   345	        self._tool_to_provider: Dict[str, MemoryProvider] = {}
   346	        self._external_prefetch_spill_config: Optional[Dict[str, Any]] = None
   347	        self._has_external: bool = False
   348	        timeout = external_prefetch_timeout
   349	        timeout = _EXTERNAL_PREFETCH_TIMEOUT_S if timeout is None else float(timeout)
   350	        if timeout <= 0:
   351	            raise ValueError("external_prefetch_timeout must be positive")
   352	        self._external_prefetch_timeout = timeout
   353	        self._external_prefetch_threads: Dict[str, threading.Thread] = {}
   354	        self._external_prefetch_lock = threading.Lock()
   355	        # Single-worker background executor for end-of-turn sync/prefetch, created lazily so
   356	        # the builtin-only path spawns no threads; one worker serializes a provider's writes.
   357	        self._sync_executor: Optional[ThreadPoolExecutor] = None
   358	        self._sync_executor_lock = threading.Lock()
   359	        # Futures by durability class ("write" / "prefetch") so shutdown can drain FIFO
   360	        # within a bound, then report exactly what it abandoned.
   361	        self._background_futures: Dict[Future, str] = {}
   362	        self._shutting_down = False
   363	        self._shutdown_drain_state: Dict[str, Any] = {
   364	            "status": "not_started", "abandoned_writes": 0, "abandoned_prefetches": 0, "active_tasks": 0,
   365	        }
   366	
   367	    def _each_provider(self, label: str, call: Callable[[MemoryProvider], Any], *, level: int = logging.DEBUG,
   368	                       providers: Optional[List[MemoryProvider]] = None, exc_info: bool = False) -> List[Any]:
   369	        """Call ``call(provider)`` per provider, logging+swallowing failures; returns successes in order.
   370	        ``label`` completes the log line ``Memory provider '<name>' <label>: <exc>``."""
   371	        results: List[Any] = []
   372	        for provider in self._providers if providers is None else providers:
   373	            try:
   374	                results.append(call(provider))
   375	            except Exception as e:
   376	                logger.log(level, "Memory provider '%s' %s: %s", provider.name, label, e, exc_info=exc_info)
   377	        return results
   378	
   379	    def add_provider(self, provider: MemoryProvider) -> None:
   380	        """Register a provider; builtin always accepted, only ONE external allowed."""
   381	        if provider.name != "builtin" and self._has_external:
   382	            existing = next((p.name for p in self._providers if p.name != "builtin"), "unknown")
   383	            logger.warning(
   384	                "Rejected memory provider '%s' — external provider '%s' is "
   385	                "already registered. Only one external memory provider is "
   386	                "allowed at a time. Configure which one via memory.provider "
   387	                "in config.yaml.", provider.name, existing,
   388	            )
   389	            return
   390	
   391	        # Load schemas BEFORE mutating any manager state: a provider whose schema
   392	        # load raises must leave `_providers` / `_has_external` untouched, otherwise
   393	        # it blocks every later external provider in this process (#9948).
   394	        schemas = list(provider.get_tool_schemas())
   395	
   396	        if provider.name != "builtin":
   397	            self._has_external = True
   398	            self._external_prefetch_spill_config = get_spill_config()
   399	
   400	        self._providers.append(provider)
   401	
   402	        # Core tool names are reserved: built-ins always win at agent init, so a shadowing
   403	        # provider tool would linger in ``_tool_to_provider`` and hijack dispatch.
   404	        # ``clarify``, ``delegate_task``). Reject it here, at the door, so it never enters the routing table
   405	        # at all — matching the built-ins-always-win invariant used by the TTS/browser/search provider
   406	        # registries. See #40466.
   407	        from toolsets import _HERMES_CORE_TOOLS
   408	
   409	        for raw_schema in schemas:
   410	            schema = normalize_tool_schema(raw_schema)
   411	            if schema is None:
   412	                continue
   413	            tool_name = schema["name"]
   414	            if tool_name in _HERMES_CORE_TOOLS:
   415	                logger.warning(
   416	                    "Memory provider '%s' tool '%s' shadows a reserved core "
   417	                    "tool name; registration ignored. Core tools always win — "
   418	                    "rename the provider's tool to something unique.", provider.name, tool_name,
   419	                )
   420	            elif tool_name in self._tool_to_provider:
   421	                logger.warning(
   422	                    "Memory tool name conflict: '%s' already registered by %s, "
   423	                    "ignoring from %s", tool_name, self._tool_to_provider[tool_name].name, provider.name,
   424	                )
   425	            else:
   426	                self._tool_to_provider[tool_name] = provider
   427	
   428	        logger.info("Memory provider '%s' registered (%d tools)", provider.name, len(schemas))
   429	
   430	    @property
   431	    def providers(self) -> List[MemoryProvider]:
   432	        return list(self._providers)
   433	
   434	    def get_provider(self, name: str) -> Optional[MemoryProvider]:
   435	        return next((p for p in self._providers if p.name == name), None)
   436	
   437	    def build_system_prompt(self) -> str:
   438	        """Join every provider's non-empty ``system_prompt_block()`` with blank lines."""
   439	        blocks = self._each_provider("system_prompt_block() failed", lambda p: p.system_prompt_block(),
   440	                                      level=logging.WARNING)
   441	        return "\n\n".join(b for b in blocks if b and b.strip())
   442	
   443	    # A /skill or /bundle turn embeds the whole skill body in the model-facing message;
   444	    # providers get just the user's instruction (None for a bare invocation).
   445	    _strip_skill_scaffolding = staticmethod(extract_user_instruction_from_skill_message)
   446	
   447	    def prefetch_all(self, query: str, *, session_id: str = "") -> str:
   448	        """Merge non-empty prefetch context from all providers (failures are non-fatal)."""
   449	        clean_query = self._strip_skill_scaffolding(query)
   450	        if not clean_query:
   451	            return ""
   452	        parts = self._each_provider(
   453	            "prefetch failed (non-fatal)", lambda p: self._prefetch_provider(p, clean_query, session_id=session_id),
   454	        )
   455	        return "\n\n".join(p for p in parts if p and p.strip())
   456	
   457	    def _prefetch_provider(self, provider: MemoryProvider, query: str, *, session_id: str = "") -> str:
   458	        """Run one provider's prefetch; external providers are bounded by a timeout. A stuck external
   459	        call keeps running on its daemon thread and the provider is skipped on later turns until it returns."""
   460	        if provider.name == "builtin":
   461	            return provider.prefetch(query, session_id=session_id)
   462	
   463	        result_box: Dict[str, Any] = {}
   464	
   465	        def _run() -> None:
   466	            try:
   467	                result_box["value"] = provider.prefetch(query, session_id=session_id) or ""
   468	            except Exception as exc:  # pragma: no cover - re-raised by caller
   469	                result_box["error"] = exc
   470	
   471	        thread = spawn_context_thread(_run, name=f"memory-prefetch-{provider.name}")
   472	        with self._external_prefetch_lock:
   473	            existing = self._external_prefetch_threads.get(provider.name)
   474	            if existing is not None and existing.is_alive():
   475	                logger.debug("Memory provider '%s' prefetch is still running; skipping this turn", provider.name)
   476	                return ""
   477	            self._external_prefetch_threads[provider.name] = thread
   478	            thread.start()
   479	
   480	        thread.join(self._external_prefetch_timeout)
   481	        if thread.is_alive():
   482	            logger.warning(
   483	                "Memory provider '%s' prefetch timed out after %.1fs; skipping it until "
   484	                "the stuck call returns", provider.name, self._external_prefetch_timeout,
   485	            )
   486	            return ""
   487	
   488	        with self._external_prefetch_lock:
   489	            if self._external_prefetch_threads.get(provider.name) is thread:
   490	                self._external_prefetch_threads.pop(provider.name, None)
   491	        if "error" in result_box:
   492	            raise result_box["error"]
   493	        result = result_box.get("value", "")
   494	        if result and result.strip():
   495	            # Prefetch is stamped into the user turn's api_content and replayed every later turn;
   496	            # spill oversized results like plugin hook output so one provider can't inflate the prefix.
   497	            result = spill_if_oversized(
   498	                result, session_id=session_id, source=f"{provider.name} memory prefetch",
   499	                config=self._external_prefetch_spill_config,
   500	            )
   501	        return result
   502	
   503	    def describe_recall(self) -> str:
   504	        """Deterministic recall indicator line (e.g. ``"🧠 Provider — recalled 3 memories"``); ``""`` if none.
   505	        Call right after :meth:`prefetch_all` so the user SEES memory was used even if the model is silent."""
   506	        segments: List[str] = []
   507	        for status in self._each_provider("recall_status failed (non-fatal)", lambda p: p.recall_status()):
   508	            if status is None:
   509	                continue
   510	            # count <= 0: content injected but no discrete count (reflect)
   511	            detail = ("recalled 1 memory" if status.count == 1 else f"recalled {status.count} memories"
   512	                      if status.count > 1 else "recalled relevant memory")
   513	            segments.append(f"{status.glyph} {status.provider_label} — {detail}")
   514	        return "  ".join(segments)
   515	
   516	    def queue_prefetch_all(self, query: str, *, session_id: str = "") -> None:
   517	        """Queue background prefetch on all providers for the next turn (see ``sync_all``)."""
   518	        providers = list(self._providers)
   519	        clean_query = self._strip_skill_scaffolding(query) if providers else None
   520	        if not clean_query:
   521	            return
   522	        self._submit_background(lambda: self._each_provider(
   523	            "queue_prefetch failed (non-fatal)", lambda p: p.queue_prefetch(clean_query, session_id=session_id),
   524	            providers=providers,
   525	        ), kind="prefetch")
   526	
   527	    @staticmethod
   528	    def _provider_sync_accepts(provider: MemoryProvider, keyword: str) -> bool:
   529	        """Whether ``sync_turn`` accepts ``keyword`` (uninspectable → assume yes)."""
   530	        params = _signature_params(provider.sync_turn)
   531	        return params is None or _has_var_kwargs(params) or keyword in params
   532	
   533	    def sync_all(self, user_content: str, assistant_content: str, *, session_id: str = "",
   534	                 messages: Optional[List[Dict[str, Any]]] = None,
   535	                 turn_author: Optional[Dict[str, Any]] = None) -> None:
   536	        """Sync a completed turn to all providers on the background worker.
   537	
   538	        Never inline: a provider's ``sync_turn`` may block for minutes, which kept ``run_conversation``
   539	        open after the user saw the response. The single worker also serializes writes (turn N before N+1).
   540	        ``turn_author`` reaches only providers whose ``sync_turn`` accepts it.
   541	        """
   542	        providers = list(self._providers)
   543	        clean_user_content = self._strip_skill_scaffolding(user_content) if providers else None
   544	        if not clean_user_content:
   545	            return
   546	        optional_kwargs = {"messages": messages, "turn_author": turn_author}
   547	
   548	        def _sync(provider: MemoryProvider) -> None:
   549	            kwargs: Dict[str, Any] = {"session_id": session_id}
   550	            for keyword, value in optional_kwargs.items():
   551	                if value is not None and self._provider_sync_accepts(provider, keyword):
   552	                    kwargs[keyword] = value
   553	            provider.sync_turn(clean_user_content, assistant_content, **kwargs)
   554	
   555	        self._submit_background(
   556	            lambda: self._each_provider("sync_turn failed", _sync, level=logging.WARNING, providers=providers)
   557	        )
   558	
   559	    def _submit_background(self, fn, *, kind: str = "write") -> None:
   560	        """Queue ``fn`` on the serialized worker (created lazily; None once shutting down) and track its
   561	        durability class. Runs under the caller's contextvars (``ctx_bound``). If the executor is
   562	        unavailable outside shutdown, run inline — the historical fail-safe."""
   563	        fn = ctx_bound(fn)
   564	        executor = None if self._shutting_down else self._sync_executor
   565	        if executor is None and not self._shutting_down:
   566	            with self._sync_executor_lock:
   567	                if self._sync_executor is None and not self._shutting_down:
   568	                    try:
   569	                        # Daemon workers: a wedged provider must never block interpreter exit.
   570	                        from tools.daemon_pool import DaemonThreadPoolExecutor
   571	                        self._sync_executor = DaemonThreadPoolExecutor(max_workers=1, thread_name_prefix="mem-sync")
   572	                    except Exception as e:  # pragma: no cover - resource exhaustion
   573	                        logger.warning("Failed to create memory sync executor: %s", e)
   574	                executor = self._sync_executor
   575	        future = None
   576	        try:
   577	            # Submit+track atomically with the shutdown snapshot. The callback is attached
   578	            # outside the lock: an already-completed future invokes callbacks synchronously.
   579	            with self._sync_executor_lock:
   580	                if self._shutting_down:
   581	                    logger.warning("Memory manager is shutting down; rejecting late %s task", kind)
   582	                    return
   583	                if executor is not None:
   584	                    future = executor.submit(fn)
   585	                    self._background_futures[future] = kind
   586	        except RuntimeError:
   587	            if self._shutting_down:
   588	                logger.warning("Memory manager shut down during %s submission; task rejected", kind)
   589	                return
   590	        if future is not None:
   591	            future.add_done_callback(self._forget_background_future)
   592	            return
   593	        try:
   594	            fn()
   595	        except Exception as e:  # pragma: no cover - fn guards internally
   596	            logger.debug("Inline memory background task failed: %s", e)
   597	
   598	    def _forget_background_future(self, future: Future) -> None:
   599	        with self._sync_executor_lock:
   600	            self._background_futures.pop(future, None)
   601	
   602	    def flush_pending(self, timeout: Optional[float] = None) -> bool:
   603	        """Block until queued sync/prefetch work has drained (False on timeout).
   604	        With a single worker, a sentinel task completing proves every earlier task ran."""
   605	        executor = self._sync_executor
   606	        if executor is None:
   607	            return True
   608	        try:
   609	            executor.submit(lambda: None).result(timeout=timeout)
   610	        except Exception as e:
   611	            return isinstance(e, RuntimeError)  # executor already shut down — nothing pending
   612	        return True
   613	
   614	    def get_all_tool_schemas(self) -> List[Dict[str, Any]]:
   615	        """Collect deduplicated tool schemas from all providers; reserved core tool names are
   616	        skipped because :meth:`add_provider` refuses to route them."""
   617	        from toolsets import _HERMES_CORE_TOOLS
   618	
   619	        schemas: List[Dict[str, Any]] = []
   620	        seen = set()
   621	
   622	        def _collect(provider: MemoryProvider) -> None:
   623	            for raw_schema in provider.get_tool_schemas():
   624	                schema = normalize_tool_schema(raw_schema)
   625	                if schema is None:
   626	                    logger.warning(
   627	                        "Memory provider '%s' returned a tool schema with "
   628	                        "no resolvable name; skipping (%r)", provider.name, raw_schema,
   629	                    )
   630	                elif schema["name"] not in _HERMES_CORE_TOOLS and schema["name"] not in seen:
   631	                    schemas.append(schema)
   632	                    seen.add(schema["name"])
   633	
   634	        self._each_provider("get_tool_schemas() failed", _collect, level=logging.WARNING)
   635	        return schemas
   636	
   637	    def get_all_tool_names(self) -> set:
   638	        return set(self._tool_to_provider)
   639	
   640	    def has_tool(self, tool_name: str) -> bool:
   641	        return tool_name in self._tool_to_provider
   642	
   643	    def handle_tool_call(self, tool_name: str, args: Dict[str, Any], **kwargs) -> str:
   644	        """Route a tool call to its provider; returns a JSON string (tool_error on failure)."""
   645	        provider = self._tool_to_provider.get(tool_name)
   646	        if provider is None:
   647	            return tool_error(f"No memory provider handles tool '{tool_name}'")
   648	        try:
   649	            return provider.handle_tool_call(tool_name, args, **kwargs)
   650	        except Exception as e:
   651	            logger.error("Memory provider '%s' handle_tool_call(%s) failed: %s", provider.name, tool_name, e)
   652	            return tool_error(f"Memory tool '{tool_name}' failed: {e}")
   653	
   654	    def on_turn_start(self, turn_number: int, message: str, **kwargs) -> None:
   655	        def _tick(p: MemoryProvider) -> None:
   656	            # A provider written before the author kwargs declares (turn_number, message) only; it still gets its tick.
   657	            params = _signature_params(p.on_turn_start)
   658	            accepted = kwargs if params is None or _has_var_kwargs(params) else {k: v for k, v in kwargs.items() if k in params}
   659	            p.on_turn_start(turn_number, message, **accepted)
   660	
   661	        self._each_provider("on_turn_start failed", _tick)
   662	
   663	    def on_session_end(self, messages: List[Dict[str, Any]]) -> None:
   664	        self._each_provider("on_session_end failed", lambda p: p.on_session_end(messages), level=logging.WARNING,
   665	                            exc_info=True)
   666	
   667	    def commit_session_boundary_async(self, messages: List[Dict[str, Any]], *, new_session_id: str,
   668	                                      parent_session_id: str = "", reason: str = "new_session") -> None:
   669	        """Queue old-session extraction + provider rebinding as ONE serialized task.
   670	
   671	        ``on_session_end`` (LLM-bound, seconds) must run strictly BEFORE ``on_session_switch`` rebinds
   672	        provider state; an ad-hoc thread raced the inline switch and misattributed transcripts.
   673	
   674	        Running extraction inline blocked the /new command for the whole LLM round-trip (#16454); running it
   675	        on an ad-hoc thread raced the inline switch — providers key off internal state, so a late
   676	        ``on_session_end`` ran against post-switch bindings (transcript misattributed to the new session id,
   677	        double-ingest of the old turn buffer, new-session buffers cleared).
   678	        Submitting BOTH hooks as one task on the manager's single background worker gives both properties at
   679	        a single chokepoint: the caller returns immediately, and the worker's FIFO order serializes
   680	        end→switch against every other provider write (per-turn ``sync_all``, prefetches), which already
   681	        share the same worker. If the executor is unavailable, ``_submit_background`` degrades to inline
   682	        execution — the pre-#16454 synchronous behavior, slow but correct.
   683	        """
   684	        if not self._providers:
   685	            return
   686	        snapshot = list(messages or [])
   687	
   688	        def _run() -> None:  # both hooks already guard per-provider
   689	            try:
   690	                self.on_session_end(snapshot)
   691	            except Exception as e:  # pragma: no cover
   692	                logger.warning("Session-boundary extraction failed: %s", e)
   693	            try:
   694	                self.on_session_switch(new_session_id, parent_session_id=parent_session_id, reset=True, reason=reason)
   695	            except Exception as e:  # pragma: no cover
   696	                logger.warning("Session-boundary switch failed: %s", e)
   697	
   698	        self._submit_background(_run)
   699	
   700	    def on_session_switch(self, new_session_id: str, *, parent_session_id: str = "", reset: bool = False,
   701	                          rewound: bool = False, **kwargs) -> None:
   702	        """Notify providers that ``AIAgent.session_id`` rotated without teardown
   703	        (``/resume``, ``/branch``, ``/reset``, ``/new``, compression). ``rewound=True``
   704	        (``/undo``): same id, truncated transcript."""
   705	        if not new_session_id:
   706	            return
   707	        if rewound:  # forward only when set so it never pollutes providers' **kwargs
   708	            kwargs["rewound"] = True
   709	        self._each_provider(
   710	            "on_session_switch failed",
   711	            lambda p: p.on_session_switch(new_session_id, parent_session_id=parent_session_id, reset=reset, **kwargs),
   712	        )
   713	
   714	    @staticmethod
   715	    def _checkpoint_api_version(provider: MemoryProvider) -> Optional[int]:
   716	        """Provider's advertised pre-compress checkpoint API version; None if unparseable."""
   717	        try:
   718	            return int(getattr(provider, "pre_compress_checkpoint_api_version", _LEGACY_PRE_COMPRESS_API_VERSION))
   719	        except (TypeError, ValueError):
   720	            return None
   721	
   722	    def supports_pre_compress_checkpoint(self, api_version: int = PRE_COMPRESS_CHECKPOINT_API_VERSION) -> bool:
   723	        """Return whether an active provider guarantees checkpoint API support."""
   724	        versions = (self._checkpoint_api_version(p) for p in self._providers)
   725	        return any(v is not None and v >= api_version for v in versions)
   726	
   727	    def on_pre_compress(self, messages: List[Dict[str, Any]], *,
   728	                        evidence_messages: Optional[List[Dict[str, Any]]] = None, require_checkpoint: bool = False,
   729	                        checkpoint_api_version: int = PRE_COMPRESS_CHECKPOINT_API_VERSION) -> str:
   730	        """Notify providers before compression; return their combined summary-prompt text.
   731	
   732	        ``messages`` is the raw v1 transcript; ``evidence_messages`` is the host-normalized list handed
   733	        only to checkpoint (v2+) providers. With ``require_checkpoint`` at least one checkpoint provider
   734	        must succeed — its exception propagates so the caller keeps the uncompressed transcript.
   735	        """
   736	        parts = []
   737	        checkpoint_succeeded = False
   738	        for provider in self._providers:
   739	            version = self._checkpoint_api_version(provider)
   740	            if version is None:
   741	                version = _LEGACY_PRE_COMPRESS_API_VERSION
   742	            is_checkpoint_provider = version >= checkpoint_api_version
   743	            use_evidence = is_checkpoint_provider and evidence_messages is not None
   744	            provider_messages = evidence_messages if use_evidence else messages
   745	            kwargs: Dict[str, Any] = {}
   746	            # v1 providers and bare-shape v2 providers never see the signal.
   747	            if is_checkpoint_provider and _accepts_require_checkpoint(provider.on_pre_compress):
   748	                kwargs["require_checkpoint"] = require_checkpoint
   749	            try:
   750	                result = provider.on_pre_compress(provider_messages, **kwargs)
   751	                if result and result.strip():
   752	                    parts.append(result)
   753	                checkpoint_succeeded = checkpoint_succeeded or is_checkpoint_provider
   754	            except Exception as e:
   755	                logger.debug("Memory provider '%s' on_pre_compress failed: %s", provider.name, e)
   756	                if require_checkpoint and is_checkpoint_provider:
   757	                    raise
   758	        if require_checkpoint and not checkpoint_succeeded:
   759	            raise RuntimeError(
   760	                f"No active memory provider completed pre-compress checkpoint API v{checkpoint_api_version}"
   761	            )
   762	        return "\n\n".join(parts)
   763	
   764	    @staticmethod
   765	    def _provider_memory_write_metadata_mode(provider: MemoryProvider) -> str:
   766	        """How to pass metadata to ``on_memory_write``: "keyword", "positional", or "legacy" (none)."""
   767	        params = _signature_params(provider.on_memory_write)
   768	        if params is None or _has_var_kwargs(params) or "metadata" in params:
   769	            return "keyword"
   770	        accepted = sum(p.kind is not inspect.Parameter.VAR_POSITIONAL for p in params.values())
   771	        return "positional" if accepted >= 4 else "legacy"
   772	
   773	    def on_memory_write(self, action: str, target: str, content: str,
   774	                        metadata: Optional[Dict[str, Any]] = None) -> None:
   775	        """Notify external providers when the built-in memory tool writes (skips builtin, the source)."""
   776	
   777	        def _notify(provider: MemoryProvider) -> None:
   778	            mode = self._provider_memory_write_metadata_mode(provider)
   779	            if mode == "legacy":
   780	                provider.on_memory_write(action, target, content)
   781	            elif mode == "positional":
   782	                provider.on_memory_write(action, target, content, dict(metadata or {}))
   783	            else:
   784	                provider.on_memory_write(action, target, content, metadata=dict(metadata or {}))
   785	
   786	        external = [p for p in self._providers if p.name != "builtin"]
   787	        self._each_provider("on_memory_write failed", _notify, providers=external)
   788	
   789	    # Actions mirrored to external providers; non-mutating results (errors, staged) are
   790	    # filtered by ``notify_memory_tool_write`` first.
   791	    _MIRRORED_MEMORY_ACTIONS = {"add", "replace", "remove"}
   792	
   793	    @staticmethod
   794	    def _memory_tool_result_succeeded(result: Any) -> bool:
   795	        """True only when the built-in memory tool actually committed a write. Fails closed (non-JSON,
   796	        non-dict, missing ``success``, staged for approval) so providers never mirror a write that did not land."""
   797	        if isinstance(result, str):
   798	            try:
   799	                result = json.loads(result)
   800	            except Exception:
   801	                return False
   802	        return isinstance(result, dict) and result.get("success") is True and result.get("staged") is not True
   803	
   804	    def notify_memory_tool_write(self, tool_result: Any, tool_args: Dict[str, Any], *,
   805	                                 build_metadata: Optional[Callable[[], Dict[str, Any]]] = None) -> None:
   806	        """Mirror a built-in memory tool call to external providers.
   807	
   808	        Gates on a committed write, expands single-op and batched ``operations`` shapes, keeps only
   809	        mutating actions, and forwards ``old_text`` plus provenance from ``build_metadata``.
   810	        ``previous_content`` comes only from the committed store result, never the search
   811	        argument: a partial provider registry cannot safely resolve that argument itself.
   812	        """
   813	        if not self._memory_tool_result_succeeded(tool_result):
   814	            return
   815	        result = json.loads(tool_result) if isinstance(tool_result, str) else tool_result
   816	        target = str(tool_args.get("target") or "memory")
   817	        operations = tool_args.get("operations")
   818	        batched = isinstance(operations, list) and bool(operations)
   819	        for index, op in enumerate(operations if batched else [tool_args], start=1):
   820	            action = str(op.get("action") or "") if isinstance(op, dict) else ""
   821	            if action not in self._MIRRORED_MEMORY_ACTIONS:
   822	                continue
   823	            try:
   824	                metadata = dict(build_metadata() if build_metadata else {})
   825	                metadata.pop("previous_content", None)
   826	                old_text = op.get("old_text")
   827	                if old_text:
   828	                    metadata["old_text"] = str(old_text)
   829	                field = {"replace": "replaced", "remove": "removed"}.get(action)
   830	                if field:
   831	                    if batched:
   832	                        entries = result.get(f"{field}_entries", {})
   833	                        previous = entries.get(str(index), entries.get(index)) if isinstance(entries, dict) else None
   834	                    else:
   835	                        previous = result.get(f"{field}_entry")
   836	                    if isinstance(previous, str) and previous:
   837	                        metadata["previous_content"] = previous
   838	                self.on_memory_write(action, target, str(op.get("content") or op.get("new_text") or ""), metadata=metadata)
   839	            except Exception as e:
   840	                logger.debug("notify_memory_tool_write failed for op %s: %s", action, e)
   841	
   842	    def on_delegation(self, task: str, result: str, *, child_session_id: str = "", **kwargs) -> None:
   843	        self._each_provider(
   844	            "on_delegation failed",
   845	            lambda p: p.on_delegation(task, result, child_session_id=child_session_id, **kwargs),
   846	        )
   847	
   848	    def shutdown_all(self) -> None:
   849	        """Drain the background executor (bounded), then shut providers down in reverse order."""
   850	        self._drain_sync_executor()
   851	        self._each_provider("shutdown failed", lambda p: p.shutdown(), level=logging.WARNING,
   852	                            providers=self._providers[::-1])
   853	
   854	    @property
   855	    def shutdown_drain_state(self) -> Dict[str, Any]:
   856	        """Snapshot of the most recent bounded shutdown drain outcome."""
   857	        with self._sync_executor_lock:
   858	            return dict(self._shutdown_drain_state)
   859	
   860	    def _drain_sync_executor(self) -> None:
   861	        """Give queued FIFO work a bounded chance, then abandon explicitly."""
   862	        with self._sync_executor_lock:
   863	            self._shutting_down = True
   864	            executor = self._sync_executor
   865	            self._sync_executor = None
   866	            tracked = dict(self._background_futures)
   867	            self._shutdown_drain_state = {
   868	                "status": "draining" if executor is not None else "drained",
   869	                "abandoned_writes": 0, "abandoned_prefetches": 0,
   870	                "active_tasks": sum(not future.done() for future in tracked),
   871	            }
   872	        if executor is None:
   873	            return
   874	
   875	        # shutdown(wait=False) closes submission without touching the FIFO; waiting on the
   876	        # tracked futures lets the worker run every queued task in order up to the deadline.
   877	        executor.shutdown(wait=False, cancel_futures=False)
   878	        _, pending = wait(tuple(tracked), timeout=_SYNC_DRAIN_TIMEOUT_S)
   879	        cancelled = [tracked[future] for future in pending if future.cancel()]
   880	        active_tasks = len(pending) - len(cancelled)
   881	        abandoned_prefetches = cancelled.count("prefetch")
   882	        abandoned_writes = len(cancelled) - abandoned_prefetches
   883	        with self._sync_executor_lock:
   884	            self._shutdown_drain_state.update(
   885	                status="timed_out" if pending else "drained", abandoned_writes=abandoned_writes,
   886	                abandoned_prefetches=abandoned_prefetches, active_tasks=active_tasks,
   887	            )
   888	        if not pending:
   889	            return
   890	        logger.warning(
   891	            "Memory shutdown drain timed out after %.2fs; abandoning %d queued "
   892	            "memory write(s) and %d queued prefetch(es); %d active task(s) remain detached",
   893	            _SYNC_DRAIN_TIMEOUT_S, abandoned_writes, abandoned_prefetches, active_tasks,
   894	        )
   895	
   896	    def initialize_all(self, session_id: str, **kwargs) -> None:
   897	        """Initialize all providers, injecting ``hermes_home`` so they resolve profile-scoped paths."""
   898	        if "hermes_home" not in kwargs:
   899	            from hermes_constants import get_hermes_home
   900	            kwargs["hermes_home"] = str(get_hermes_home())
   901	        self._each_provider("initialize failed", lambda p: p.initialize(session_id=session_id, **kwargs),
   902	                            level=logging.WARNING)
