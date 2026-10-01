     1	"""System-prompt assembly for :class:`AIAgent`.
     2	
     3	Built once per session and reused across turns (only context compression
     4	triggers a rebuild) so the upstream prefix cache stays warm.  Three tiers are
     5	joined with ``\\n\\n``: ``stable`` (identity, guidance, env hints, coding brief,
     6	platform hints), ``context`` (workspace snapshot, caller ``system_message``,
     7	context files) and ``volatile`` (skills index, memory, USER.md, external memory
     8	provider, timestamp line).  See ``references/system-prompt-invariant.md``.
     9	"""
    10	
    11	from __future__ import annotations
    12	
    13	import json
    14	import logging
    15	import os
    16	import re
    17	from pathlib import Path
    18	from typing import Any, Dict, List, Optional, Tuple
    19	
    20	from agent.delegation_context import owned_kanban_task
    21	from agent.prompt_builder import (
    22	    ASYNC_HANDOFF_GUIDANCE, DEFAULT_AGENT_IDENTITY, EXECUTION_GUIDANCE_MODELS, GOOGLE_MODEL_OPERATIONAL_GUIDANCE,
    23	    HERMES_AGENT_HELP_GUIDANCE, HERMES_AGENT_HELP_GUIDANCE_NO_SKILLS, KANBAN_GUIDANCE,
    24	    PARALLEL_TOOL_CALL_GUIDANCE, PLATFORM_HINTS, SESSION_SEARCH_GUIDANCE,
    25	    SKILLS_GUIDANCE, STEER_CHANNEL_NOTE, TASK_COMPLETION_GUIDANCE, TELEGRAM_RICH_MESSAGES_HINT,
    26	    TOOL_USE_ENFORCEMENT_GUIDANCE, TOOL_USE_ENFORCEMENT_MODELS, drain_truncation_warnings,
    27	)
    28	from agent import prompt_builder as _pb
    29	from agent.runtime_cwd import resolve_agent_cwd, resolve_context_cwd
    30	from hermes_constants import get_default_hermes_root, get_hermes_home
    31	from utils import is_truthy_value
    32	
    33	logger = logging.getLogger(__name__)
    34	_PLUGIN_SECTION_FRAME_RE = re.compile(
    35	    r"^## Plugin Context: (?P<id>[a-z0-9][a-z0-9._-]{0,127})\n<!-- hermes-plugin-section-chars:(?P<chars>[0-9]{1,4}) -->\n\n",
    36	    re.MULTILINE,
    37	)
    38	_GATE_WORDS = {**dict.fromkeys(("true", "always", "yes", "on"), True), **dict.fromkeys(("false", "never", "no", "off"), False)}
    39	
    40	
    41	def _model_gate(setting: Any, model: Optional[str], default_models) -> bool:
    42	    """Resolve a config gate: True/"true"-ish -> on, False/"false"-ish -> off,
    43	    list -> case-insensitive model-substring match, anything else ("auto") ->
    44	    match against *default_models*."""
    45	    if setting is True or setting is False:
    46	        return setting
    47	    if isinstance(setting, str) and setting.lower() in _GATE_WORDS:
    48	        return _GATE_WORDS[setting.lower()]
    49	    model_lower = (model or "").lower()
    50	    if isinstance(setting, list):
    51	        return any(p.lower() in model_lower for p in setting if isinstance(p, str))
    52	    return any(p in model_lower for p in default_models)
    53	
    54	
    55	def _resolve_platform_hint(agent: Any, platform_key: str, default_hint: str) -> str:
    56	    """Apply the ``platform_hints.<platform>`` config override: ``replace``
    57	    substitutes the default, ``append`` adds text (a bare string is shorthand
    58	    for append). Malformed entries fall back to the unmodified default so bad
    59	    config can never break prompt assembly or leak across platforms."""
    60	    overrides = getattr(agent, "_platform_hint_overrides", None)
    61	    spec = overrides.get(platform_key) if platform_key and isinstance(overrides, dict) else None
    62	    if isinstance(spec, str):
    63	        spec = {"append": spec}
    64	    if not isinstance(spec, dict):
    65	        return default_hint
    66	    replace_text, append_text = (v.strip() if isinstance(v, str) else "" for v in (spec.get("replace"), spec.get("append")))
    67	    base = replace_text or default_hint
    68	    return f"{base}\n\n{append_text}".strip() if append_text else base
    69	
    70	
    71	_TUI_EMBEDDED_PANE_CLARIFIER = (
    72	    " You're in its embedded terminal pane, beside the GUI chat — the user can "
    73	    "select your output (Option-drag on macOS, Shift-drag elsewhere) and press "
    74	    "Cmd/Ctrl+L to send it to the chat composer."
    75	)
    76	
    77	
    78	def _tui_embedded_pane_clarifier(hint: str) -> str:
    79	    """Append the desktop embedded-terminal clarifier when ``HERMES_DESKTOP_TERMINAL``
    80	    is set (only the desktop's TUI PTY, never the chat backend). Idempotent."""
    81	    if not hint or _TUI_EMBEDDED_PANE_CLARIFIER in hint or not is_truthy_value(os.getenv("HERMES_DESKTOP_TERMINAL")):
    82	        return hint
    83	    return hint + _TUI_EMBEDDED_PANE_CLARIFIER
    84	
    85	
    86	def _plugin_session_info(agent: Any) -> Dict[str, str]:
    87	    """Return immutable-at-render-time metadata exposed to prompt sections."""
    88	    try:
    89	        cwd = str(resolve_context_cwd() or "")
    90	    except Exception:
    91	        cwd = ""
    92	    info = {k: str(getattr(agent, k, None) or "") for k in ("session_id", "model", "provider", "platform")}
    93	    info.update(profile_name=_active_profile_name(agent, _ambient_plugin_profile_name), cwd=cwd)
    94	    return info
    95	
    96	
    97	def _ambient_plugin_profile_name() -> str:
    98	    from hermes_cli.profiles import get_active_profile_name
    99	    return str(get_active_profile_name() or "default")
   100	
   101	
   102	def _active_profile_name(agent: Any, ambient) -> str:
   103	    """Profile name from the agent's OWN home, else *ambient()*; "default" on any
   104	    failure. Ambient resolution misreports on threads that lost the HERMES_HOME
   105	    ContextVar, which is why the agent's home is preferred."""
   106	    try:
   107	        home = _agent_home(agent)
   108	        return _profile_name_for_home(home) if home is not None else ambient()
   109	    except Exception:
   110	        return "default"
   111	
   112	
   113	def _frozen_plugin_prompt_sections(agent: Any) -> tuple:
   114	    """Render plugin sections once per session and freeze them on the agent.
   115	    A restored ``_cached_system_prompt`` is parsed instead of re-running plugin
   116	    code; a render that raises at a rebuild boundary keeps the previous bytes
   117	    (stashed by ``invalidate_system_prompt``) instead of silently vanishing."""
   118	    if hasattr(agent, "_plugin_system_prompt_sections_snapshot"):
   119	        return agent._plugin_system_prompt_sections_snapshot
   120	    stored_prompt = getattr(agent, "_cached_system_prompt", None)
   121	    if isinstance(stored_prompt, str) and stored_prompt:
   122	        rendered = _restore_plugin_prompt_sections(stored_prompt)
   123	    else:
   124	        try:
   125	            from hermes_cli.plugins import render_system_prompt_sections
   126	            rendered = tuple(render_system_prompt_sections(_plugin_session_info(agent)))
   127	        except Exception as exc:
   128	            rendered = getattr(agent, "_plugin_system_prompt_sections_previous", None)
   129	            if rendered:
   130	                logger.warning("Plugin system prompt sections failed to re-render (%s); keeping the previous frozen sections", exc)
   131	            else:
   132	                logger.warning("Plugin system prompt sections could not be rendered: %s", exc)
   133	                rendered = ()
   134	    agent._plugin_system_prompt_sections_snapshot = rendered
   135	    return rendered
   136	
   137	
   138	def _restore_plugin_prompt_sections(prompt: str) -> tuple:
   139	    """Recover frozen section bytes from the persisted full prompt.  Only the
   140	    exact canonical container emitted by core is accepted — user/project text
   141	    may resemble a frame."""
   142	    from hermes_cli.plugins import (
   143	        MAX_SYSTEM_PROMPT_SECTION_CHARS, PLUGIN_SECTIONS_END, PLUGIN_SECTIONS_START,
   144	        RenderedPluginSystemPromptSection, format_system_prompt_sections,
   145	    )
   146	    start = prompt.rfind(PLUGIN_SECTIONS_START)
   147	    end = prompt.find(PLUGIN_SECTIONS_END, start + len(PLUGIN_SECTIONS_START)) if start >= 0 else -1
   148	    if end < 0:
   149	        return ()
   150	    after_end = end + len(PLUGIN_SECTIONS_END)
   151	    if not prompt[after_end:].startswith("\n\nConversation started:"):
   152	        return ()
   153	    framed = prompt[start:after_end]
   154	    restored = []
   155	    for match in _PLUGIN_SECTION_FRAME_RE.finditer(framed):
   156	        content_len = int(match.group("chars"))
   157	        content = framed[match.end() : match.end() + content_len]
   158	        if content_len > MAX_SYSTEM_PROMPT_SECTION_CHARS or len(content) != content_len:
   159	            continue
   160	        restored.append(RenderedPluginSystemPromptSection(id=match.group("id"), content=content,
   161	                                                          position="after_memory", plugin="persisted-prompt"))
   162	    return tuple(restored) if format_system_prompt_sections(restored) == framed else ()
   163	
   164	
   165	def restore_plugin_prompt_sections(agent: Any, prompt: str) -> None:
   166	    """Seed a resumed agent's frozen snapshot from persisted prompt bytes."""
   167	    agent._plugin_system_prompt_sections_snapshot = _restore_plugin_prompt_sections(prompt)
   168	
   169	
   170	def _plugin_section_blocks(sections: tuple, position: str) -> List[str]:
   171	    from hermes_cli.plugins import format_system_prompt_sections
   172	    block = format_system_prompt_sections([s for s in sections if s.position == position])
   173	    return [block] if block else []
   174	
   175	
   176	def _session_start_like(agent: Any, now: Any) -> Any:
   177	    """Best-known conversation start time, or ``now`` as a fallback.
   178	    ``Conversation started:`` must be byte-stable across rebuilds (compression,
   179	    resume, fresh gateway turns), so prefer immutable sources in order: the
   180	    lineage-root session id's embedded stamp (compaction rotates ids, each with
   181	    its own mint time), the current session id's stamp, ``agent.session_start``,
   182	    then ``now``.  Stamps are box-local wall-clock: attach that zone first, then
   183	    convert to ``now``'s zone so the date matches the per-turn clock.
   184	
   185	    0. the LINEAGE-ROOT session id's embedded timestamp — compaction can rotate the session id, and each
   186	    rotated id embeds its OWN mint time, so after months of compactions rung 1 alone would quietly re-birth
   187	    the conversation at its latest rotation. Walking to the lineage root (same walk as
   188	    ``_conversation_root_id``) recovers the ORIGINAL birth stamp — a Bot Mode forever-chat keeps knowing
   189	    when it was first born, across every compaction (maintainer-directed, #98426); 1. the timestamp embedded
   190	    in ``session_id`` (``YYYYMMDD_HHMMSS_...``) — immutable for the life of the session, so the line is
   191	    byte-stable across every rebuild boundary (preserving prefix-cache KV); 2. 3. ``now`` (initial/legacy
   192	    build without either).
   193	    """
   194	    from datetime import datetime
   195	    def _to_display_tz(dt: Any) -> Any:
   196	        if dt.tzinfo is None:
   197	            try:
   198	                dt = dt.replace(tzinfo=datetime.now().astimezone().tzinfo)
   199	            except (ValueError, OSError):
   200	                pass
   201	        if getattr(now, "tzinfo", None) is not None and dt.tzinfo is not None:
   202	            try:
   203	                dt = dt.astimezone(now.tzinfo)
   204	            except (ValueError, OSError):
   205	                pass
   206	        return dt
   207	    session_id = getattr(agent, "session_id", None)
   208	    db = getattr(agent, "_session_db", None)
   209	    try:
   210	        root_id = db.get_conversation_root(session_id) if db is not None and isinstance(session_id, str) and session_id else None
   211	    except Exception:
   212	        root_id = None
   213	    for candidate in (root_id, session_id):
   214	        m = re.match(r"^(\d{8})_(\d{6})", candidate) if isinstance(candidate, str) else None
   215	        if m:
   216	            try:
   217	                return _to_display_tz(datetime.strptime(f"{m.group(1)}_{m.group(2)}", "%Y%m%d_%H%M%S"))
   218	            except ValueError:
   219	                pass
   220	    session_start = getattr(agent, "session_start", None)
   221	    return _to_display_tz(session_start) if hasattr(session_start, "astimezone") else now
   222	
   223	
   224	def _agent_home(agent: Any) -> Optional[Path]:
   225	    """The agent's OWN profile home, or None to use ambient resolution.
   226	    A bound HERMES_HOME ContextVar override wins (the gateway multiplexes
   227	    profiles over one shared session DB and binds the home per turn); else the
   228	    parent of ``_session_db.db_path`` — ground truth on threads that lost the
   229	    ContextVar, where ambient resolution would leak the launch profile.
   230	
   231	    1. Surfaces that multiplex several profiles over ONE shared session DB (the messaging gateway:
   232	    ``gateway/run.py`` hands every agent the launch-home ``state.db`` and binds the profile home per turn
   233	    via ``_profile_runtime_scope`` + ``copy_context``) would otherwise have the db-derived launch home STOMP
   234	    the correctly-bound profile — inverting the leak this helper exists to fix (found by @kshitijk4poor's
   235	    post-merge probe on #86313). 2. Fallback: the home containing the agent's ``_session_db.db_path``
   236	    (``<home>/state.db``) — ground truth on threads that lost the ContextVar (ContextVars don't propagate
   237	    into ``threading.Thread``), where the unbound build previously fell back to the launch home and leaked
   238	    the default profile's skills/identity into a bot prompt.
   239	    """
   240	    try:
   241	        from hermes_constants import get_hermes_home_override
   242	        override = get_hermes_home_override()
   243	        if override:
   244	            return Path(override)
   245	    except Exception:
   246	        pass
   247	    try:
   248	        db_path = getattr(getattr(agent, "_session_db", None), "db_path", None)
   249	        return Path(db_path).parent if db_path else None
   250	    except Exception:
   251	        return None
   252	
   253	
   254	def _agent_skills_dir(agent: Any) -> Optional[Path]:
   255	    """The agent's own ``<home>/skills`` dir, or None to use ambient home."""
   256	    home = _agent_home(agent)
   257	    return home / "skills" if home is not None else None
   258	
   259	
   260	def _profile_name_for_home(home: Path) -> str:
   261	    """``<root>/profiles/X`` -> ``"X"``; anything else -> ``"default"``.
   262	    Uses ``get_default_hermes_root()`` (NOT ``get_hermes_home()``): on a bound
   263	    profile session the ambient home IS the profile dir, so every profile
   264	    would misreport as "default"."""
   265	    try:
   266	        from hermes_constants import get_default_hermes_root
   267	        rel = home.resolve().relative_to((get_default_hermes_root() / "profiles").resolve())
   268	        return rel.parts[0] if rel.parts else "default"
   269	    except (ValueError, OSError):
   270	        return "default"
   271	
   272	
   273	def _tool_guidance_block(agent: Any) -> Optional[str]:
   274	    """Tool-aware behavioral guidance, injected only when the tools are loaded."""
   275	    names = agent.valid_tool_names
   276	    # With both memory stores disabled no store is built, so the full guidance
   277	    # would steer the model at a tool that always answers "Memory is not
   278	    # available"; with only USER.md enabled the narrower block is used.
   279	    memory_guidance = None
   280	    if "memory" in names:
   281	        memory_guidance = _pb.build_memory_guidance(
   282	            getattr(agent, "_memory_enabled", True),
   283	            getattr(agent, "_user_profile_enabled", True),
   284	            skill_manage_available="skill_manage" in names,
   285	        )
   286	    # Kanban lifecycle: resolved once at __init__ (_kanban_worker_guidance);
   287	    # fallback paths must also limit task protocol guidance to dispatcher workers.
   288	    _kanban_guidance = getattr(agent, "_kanban_worker_guidance", None)
   289	    if _kanban_guidance is None and "kanban_show" in names and owned_kanban_task():
   290	        _kanban_guidance = KANBAN_GUIDANCE
   291	    tool_guidance = [
   292	        memory_guidance,
   293	        SESSION_SEARCH_GUIDANCE if "session_search" in names else None,
   294	        SKILLS_GUIDANCE if "skill_manage" in names else None,
   295	        _kanban_guidance,
   296	    ]
   297	    return " ".join(g for g in tool_guidance if g) or None
   298	
   299	
   300	def _skills_prompt(agent: Any) -> str:
   301	    """Skills index (empty without skills tools).  Focus mode demotes non-coding
   302	    categories to names-only — never hidden, every name stays visible."""
   303	    if not any(name in agent.valid_tool_names for name in ['skills_list', 'skill_view', 'skill_manage']):
   304	        return ""
   305	    import model_tools
   306	    avail_toolsets = {model_tools.get_toolset_for_tool(tool_name) for tool_name in agent.valid_tool_names} - {None, ""}
   307	    try:
   308	        from agent.coding_context import coding_compact_skill_categories
   309	        _compact_cats = coding_compact_skill_categories(platform=agent.platform, cwd=resolve_context_cwd())
   310	    except Exception:
   311	        _compact_cats = frozenset()
   312	    return _pb.build_skills_system_prompt(available_tools=agent.valid_tool_names, available_toolsets=avail_toolsets,
   313	                                         compact_categories=_compact_cats or None, skills_dir_override=_agent_skills_dir(agent))
   314	
   315	
   316	def _auto_load_parts(agent: Any) -> List[str]:
   317	    """``skills.auto_load`` blocks, resolved once per agent lifecycle (config, skill files and
   318	    HERMES_IGNORE_RULES are read on the first build only) so the prompt stays byte-stable
   319	    across model switches, compression and static-prefix restoration.
   320	
   321	    Same gate as ``_skills_prompt``: nothing without the skills toolset, and nothing for agents that skip
   322	    context files (delegate children, curator/review forks, gateway hygiene agents) — pinned skills are
   323	    operator guidance for the user's session, not payload for every internal fork."""
   324	    if getattr(agent, "skip_context_files", False) or not any(
   325	            name in agent.valid_tool_names for name in ("skills_list", "skill_view", "skill_manage")):
   326	        return []
   327	    if not getattr(agent, "_auto_load_skills_resolved", False):
   328	        result: Tuple[str, List[str], List[str]] = ("", [], [])
   329	        try:
   330	            if not is_truthy_value(os.environ.get("HERMES_IGNORE_RULES")):
   331	                from agent.skill_commands import build_auto_load_prompt
   332	                result = build_auto_load_prompt(task_id=getattr(agent, "session_id", None), home_override=_agent_home(agent))
   333	            if result[2]:
   334	                logger.warning("skills.auto_load: skill(s) not found or disabled, skipped: %s", ", ".join(result[2]))
   335	        except Exception:
   336	            logger.debug("skills.auto_load: injection skipped", exc_info=True)  # config errors never block session start
   337	        agent._auto_load_skills_result = result
   338	        agent._auto_load_skills_resolved = True
   339	    prompt = agent._auto_load_skills_result[0]
   340	    return [prompt] if prompt else []
   341	
   342	
   343	def _bot_mode_parts(agent: Any) -> List[str]:
   344	    """Bot Mode teammate protocol — only in a bot's canonical "Bot Chat" session.
   345	    Marks the prompt timeless (the volatile date line is dropped) since a birth
   346	    date pinned in a months-long session is misinformation."""
   347	    parts: List[str] = []
   348	    try:
   349	        from tools.bot_mode_probe import BOT_CHAT_TITLE, epoch_line, get_bot_mode_protocol_section
   350	        _title = str(getattr(agent, "_session_title_hint", "") or "").strip()
   351	        if not _title:
   352	            _sdb = getattr(agent, "_session_db", None)
   353	            _sid = getattr(agent, "session_id", None)
   354	            _title = str((_sdb.get_session_title(_sid) if (_sdb and _sid) else None) or "").strip()
   355	        _bot_section = get_bot_mode_protocol_section(_agent_home(agent)) if _title == BOT_CHAT_TITLE else None
   356	        if _bot_section:
   357	            parts.append(_bot_section)
   358	            # Capability epoch lets the restore path rebuild ONCE per
   359	            # user-initiated capability change in an eternal session.
   360	            parts.append(epoch_line(_agent_home(agent)))
   361	            agent._bot_chat_timeless_prompt = True
   362	    except Exception:
   363	        pass
   364	    return parts
   365	
   366	
   367	def _ambient_file_safety_profile_name() -> str:
   368	    from agent.file_safety import _resolve_active_profile_name
   369	    return _resolve_active_profile_name()
   370	
   371	
   372	def _active_profile_line(agent: Any) -> str:
   373	    """Name the running profile so the agent doesn't conflate ``~/.hermes/skills``
   374	    (default) with ``~/.hermes/profiles/<active>/skills``.  Resolved from the
   375	    agent's OWN home first (a build thread that lost the ContextVar would
   376	    otherwise print "default" for a bot profile)."""
   377	    _agent_home_path = _agent_home(agent)
   378	    active_profile = _active_profile_name(agent, _ambient_file_safety_profile_name)
   379	    if active_profile == "default":
   380	        # With an explicit agent home, the default profile's data lives at the
   381	        # ROOT (get_hermes_home() on a bound profile session is the PROFILE dir).
   382	        # Without one, keep the ambient (patchable) resolution byte-identical.
   383	        _root_str = str(get_default_hermes_root() if _agent_home_path is not None else get_hermes_home())
   384	        return (
   385	            "Active Hermes profile: default. Other profiles (if any) live "
   386	            "under " + _root_str + "/profiles/<name>/. Each profile has its own "
   387	            "skills/, plugins/, cron/, and memories/ that affect a different "
   388	            "session than this one. Do not modify another profile's "
   389	            "skills/plugins/cron/memories unless the user explicitly directs "
   390	            "you to."
   391	        )
   392	    # A non-default name is only returned when the resolved home is ALREADY
   393	    # <root>/profiles/<name>, so the profile home is the session home itself.
   394	    profile_home = str(_agent_home_path) if _agent_home_path is not None else str(get_hermes_home())
   395	    # A non-default name is only ever returned when the resolved home is ALREADY <root>/profiles/<name> —
   396	    # that is exactly how both _profile_name_for_home() and _resolve_active_profile_name() derive it. So the
   397	    # profile home is the session home itself; appending /profiles/<name> again doubled it (#72894). The
   398	    # default profile's data sits at the ROOT (get_default_hermes_root()), which in ambient profile mode is
   399	    # NOT get_hermes_home().
   400	    default_root = get_default_hermes_root()
   401	    return (
   402	        f"Active Hermes profile: {active_profile}. This session reads "
   403	        f"and writes {profile_home}/. The default "
   404	        f"profile's data lives at {default_root}/skills/, {default_root}/plugins/, "
   405	        f"{default_root}/cron/, {default_root}/memories/ — those belong to a "
   406	        f"different session run from a different shell. Do NOT modify "
   407	        f"another profile's skills/plugins/cron/memories unless the user "
   408	        f"explicitly directs you to."
   409	    )
   410	
   411	
   412	def _default_platform_hint(platform_key: str) -> str:
   413	    """Built-in hint, else the plugin adapter's ``platform_hint``, else ``""``."""
   414	    hint = PLATFORM_HINTS.get(platform_key, "")
   415	    if not hint and platform_key:
   416	        try:
   417	            from gateway.platform_registry import platform_registry
   418	            _entry = platform_registry.get(platform_key)
   419	            hint = (_entry and _entry.platform_hint) or ""
   420	        except Exception:
   421	            pass
   422	    if platform_key == "telegram" and hint and _telegram_rich_messages_enabled():
   423	        hint = hint.rstrip() + " " + TELEGRAM_RICH_MESSAGES_HINT
   424	    return hint
   425	
   426	
   427	def _cron_delivery_hint(agent: Any) -> str:
   428	    """The destination channel's hint (default + its ``platform_hints`` override) for a cron agent.
   429	
   430	    A cron agent runs as platform ``cron`` but its final response lands on the job's ``deliver``
   431	    channel, so without this the model never learns that MEDIA: tags become Slack/Telegram
   432	    attachments or that tables do not render there — and a user's ``platform_hints.slack.append``
   433	    never reached scheduled jobs at all. The scheduler publishes the primary auto-deliver target
   434	    into the session ContextVar before the agent runs (same seam ``send_message`` routes by).
   435	    """
   436	    from gateway.session_context import get_session_env
   437	    deliver_key = get_session_env("HERMES_CRON_AUTO_DELIVER_PLATFORM", "").lower().strip()
   438	    if not deliver_key or deliver_key == "cron":
   439	        return ""
   440	    hint = _resolve_platform_hint(agent, deliver_key, _default_platform_hint(deliver_key))
   441	    return f"Delivery destination ({deliver_key}): {hint}" if hint else ""
   442	
   443	
   444	def platform_hint(agent: Any) -> str:
   445	    """Built-in/plugin platform hint + Telegram rich-messages opt-in + config
   446	    override + desktop TUI clarifier; cron agents also carry their delivery channel's hint."""
   447	    platform_key = (agent.platform or "").lower().strip()
   448	    _effective_hint = _resolve_platform_hint(agent, platform_key, _default_platform_hint(platform_key))
   449	    if platform_key == "tui" and _effective_hint:
   450	        _effective_hint = _tui_embedded_pane_clarifier(_effective_hint)
   451	    if platform_key == "cron":
   452	        _delivery = _cron_delivery_hint(agent)
   453	        if _delivery:
   454	            _effective_hint = f"{_effective_hint}\n\n{_delivery}".strip()
   455	    return _effective_hint
   456	
   457	
   458	def _telegram_rich_messages_enabled() -> bool:
   459	    """``rich_messages`` from the Telegram ``extra`` config; same precedence the
   460	    adapter uses (top-level ``platforms.telegram.extra`` overrides
   461	    ``gateway.platforms.telegram.extra`` at the leaf). False on any read failure."""
   462	    try:
   463	        from hermes_cli.config import load_config_readonly
   464	        _cfg = load_config_readonly()
   465	        _gw = (((_cfg.get("gateway") or {}).get("platforms") or {}).get("telegram") or {}).get("extra")
   466	        _top = ((_cfg.get("platforms") or {}).get("telegram") or {}).get("extra")
   467	        merged = {**(_gw if isinstance(_gw, dict) else {}), **(_top if isinstance(_top, dict) else {})}
   468	        return bool(merged.get("rich_messages"))
   469	    except Exception:
   470	        return False
   471	
   472	
   473	def _zone_bits(now: Any, tz: Any) -> List[str]:
   474	    """IANA key, abbreviation (if different) and UTC offset — all constant for
   475	    the day, so the byte-stable date line stays cacheable."""
   476	    _iana = getattr(tz, "key", None)
   477	    from hermes_time import safe_strftime
   478	    _abbrev = safe_strftime(now, "%Z")
   479	    _offset = safe_strftime(now, "%z")  # '-0400' -> 'UTC-04:00'
   480	    bits = [_iana] if _iana else []
   481	    if _abbrev and _abbrev != _iana:
   482	        bits.append(_abbrev)
   483	    if _offset:
   484	        bits.append(f"UTC{_offset[:3]}:{_offset[3:]}")
   485	    return bits
   486	
   487	
   488	def _timestamp_line(agent: Any) -> str:
   489	    """Date-only so the prompt is byte-stable for the day; zone + offset so
   490	    tools needn't guess EST vs EDT. Long-lived sessions get an "as of" line on
   491	    rebuild days (the cache prefix is already invalidated at that boundary)."""
   492	    from hermes_time import get_timezone as _hermes_tz, now as _hermes_now, safe_strftime
   493	    now = _hermes_now()
   494	    _bits = _zone_bits(now, _hermes_tz())
   495	    _zone_suffix = f" ({', '.join(_bits)})" if _bits else ""
   496	    _start = _session_start_like(agent, now)
   497	    timestamp_line = f"Conversation started: {safe_strftime(_start, '%A, %B %d, %Y')}{_zone_suffix}"
   498	    # Second line (maintainer design, salvaging #96224's anchor): long-lived sessions — Bot Mode
   499	    # forever-chats, messenger channels people never close — span many days and many compactions. A lone
   500	    # birth date leads the model to believe it is still living in that old day. The prompt is rebuilt at
   501	    # every compaction boundary, so stamp the rebuild day too: 'started' stays anchored and byte-stable, 'as
   502	    # of' refreshes exactly when the cache prefix is already being invalidated (compaction), so the added
   503	    # line costs no extra cache churn. Same-day sessions skip the second line entirely — nothing to correct,
   504	    # and the single-line shape stays byte-identical for the day (prefix-cache safe).
   505	    if now.strftime("%Y%m%d") != _start.strftime("%Y%m%d"):
   506	        timestamp_line += (f"\nToday's date (as of the last context rebuild): {safe_strftime(now, '%A, %B %d, %Y')} "
   507	                           "— trust this over the start date for what day it is now; query tools for exact time.")
   508	    if getattr(agent, "_bot_chat_timeless_prompt", False):
   509	        timestamp_line = f"Timezone: {', '.join(_bits)}" if _bits else ""
   510	    trailer = (("Session ID", agent.session_id if agent.pass_session_id else None), ("Model", agent.model),
   511	               ("Provider", agent.provider), ("Platform", agent.platform))
   512	    return timestamp_line + "".join(f"\n{label}: {value}" for label, value in trailer if value)
   513	
   514	
   515	def _memory_parts(agent: Any) -> List[str]:
   516	    """Built-in memory/USER.md blocks plus the external provider block (gated on
   517	    the same check ``inject_memory_provider_tools`` uses, so we never advertise
   518	    tools the toolset config gated off)."""
   519	    parts: List[str] = []
   520	    if agent._memory_store:
   521	        for enabled, kind in ((agent._memory_enabled, "memory"), (agent._user_profile_enabled, "user")):
   522	            block = agent._memory_store.format_for_system_prompt(kind) if enabled else None
   523	            if block:
   524	                parts.append(block)
   525	    # External memory provider system prompt block (additive to built-in). Gated on the same check
   526	    # ``inject_memory_provider_tools`` uses so we never advertise provider tools that the agent's toolset
   527	    # configuration has already gated off (#81014).
   528	    if agent._memory_manager:
   529	        try:
   530	            from agent.memory_manager import memory_provider_tools_exposed as _mem_exposed
   531	        except Exception:
   532	            _mem_exposed = None
   533	        if _mem_exposed is None or _mem_exposed(agent):
   534	            try:
   535	                _ext_mem_block = agent._memory_manager.build_system_prompt()
   536	            except Exception:
   537	                _ext_mem_block = None
   538	            if _ext_mem_block:
   539	                parts.append(_ext_mem_block)
   540	    return parts
   541	
   542	
   543	def _identity_parts(agent: Any, ctx_len: Optional[int]) -> Tuple[List[str], bool]:
   544	    """SOUL.md (primary identity; cron keeps the persona while skipping cwd
   545	    instructions, scoped to the agent's OWN home) or the default identity.
   546	    Returns ``(parts, soul_loaded)``."""
   547	    wants_soul = agent.load_soul_identity or not agent.skip_context_files
   548	    _soul_content = _pb.load_soul_md(ctx_len, home_override=_agent_home(agent)) if wants_soul else None
   549	    return ([_soul_content], True) if _soul_content else ([DEFAULT_AGENT_IDENTITY], False)
   550	
   551	
   552	def _guidance_parts(agent: Any) -> List[str]:
   553	    """Universal + tool-aware + model-gated guidance blocks, each gated by its config.yaml key."""
   554	    parts: List[str] = []
   555	    if agent.valid_tool_names:
   556	        parts += [
   557	            text for flag, text in (
   558	                ("_task_completion_guidance", TASK_COMPLETION_GUIDANCE),
   559	                ("_parallel_tool_call_guidance", PARALLEL_TOOL_CALL_GUIDANCE),
   560	            ) if getattr(agent, flag, True)
   561	        ]
   562	    parts.append(_tool_guidance_block(agent))  # None/empty entries are dropped by _join_tier
   563	    if not agent.valid_tool_names:
   564	        return parts
   565	    # Steering only lands inside tool results, so only reachable with tools.
   566	    parts.append(STEER_CHANNEL_NOTE)
   567	    # agent.tool_use_enforcement / agent.execution_guidance: "auto" (default)
   568	    # matches the hardcoded model lists; true/false force; a list gives custom
   569	    # model-name substrings.  Execution guidance is an independent gate so
   570	    # DeepSeek/Kimi/Qwen-class models get it even with enforcement off.
   571	    if _model_gate(agent._tool_use_enforcement, agent.model, TOOL_USE_ENFORCEMENT_MODELS):
   572	        parts.append(TOOL_USE_ENFORCEMENT_GUIDANCE)
   573	        if any(g in (agent.model or "").lower() for g in ("gemini", "gemma")):
   574	            parts.append(GOOGLE_MODEL_OPERATIONAL_GUIDANCE)
   575	    if _model_gate(getattr(agent, "_execution_guidance", "auto"), agent.model, EXECUTION_GUIDANCE_MODELS):
   576	        from agent.prompt_builder import execution_guidance_text
   577	        parts.append(execution_guidance_text())
   578	    # delegate_task background delivery is intentionally between turns. Put this after the generic persistence
   579	    # blocks so their "keep working" rule cannot turn the required yield into no-op/polling activity.
   580	    if "delegate_task" in agent.valid_tool_names:
   581	        parts.append(ASYNC_HANDOFF_GUIDANCE)
   582	    return parts
   583	
   584	
   585	def _alibaba_identity_part(agent: Any) -> List[str]:
   586	    """Alibaba Coding Plan always reports "glm-4.7" as the model name; inject
   587	    the real identity so the agent can answer correctly."""
   588	    if agent.provider != "alibaba":
   589	        return []
   590	    _model_short = agent.model.rsplit("/", 1)[-1]
   591	    return [
   592	        f"You are powered by the model named {_model_short}. "
   593	        f"The exact model ID is {agent.model}. "
   594	        f"When asked what model you are, always answer based on this information, "
   595	        f"not on any model name returned by the API."
   596	    ]
   597	
   598	
   599	def _workspace_pin_key() -> str:
   600	    """The directory the workspace probe inspects, which is also the prompt's ``Current working
   601	    directory``: a build with no cwd bound (launch dir) and a later one binding that same dir
   602	    (TUI ``/compress``) are one workspace, not two."""
   603	    try:
   604	        return str(resolve_context_cwd() or resolve_agent_cwd())
   605	    except OSError:  # deleted cwd
   606	        return ""
   607	
   608	
   609	def _persisted_workspace_block(prompt: str, key: str) -> Optional[str]:
   610	    """The workspace snapshot inside ``prompt`` taken for ``key`` (its ``- Root:`` is ``key`` or an
   611	    ancestor); "" when the prompt has none; None when it has one for another root."""
   612	    from agent.coding_context import WORKSPACE_BLOCK_HEADER
   613	    head = f"\n\n{WORKSPACE_BLOCK_HEADER}\n- Root: "
   614	    start = prompt.find(head)
   615	    if start < 0:
   616	        return ""
   617	    cwd = Path(key).resolve()
   618	    while start >= 0:
   619	        block = prompt[start + 2:].split("\n\n", 1)[0]
   620	        root = Path(block.split("\n", 2)[1][len("- Root: "):]).resolve()
   621	        if root == cwd or root in cwd.parents:
   622	            return block
   623	        start = prompt.find(head, start + 2)
   624	    return None
   625	
   626	
   627	def _session_prompt(agent: Any) -> Optional[str]:
   628	    """Prompt bytes this session already sends: the cached copy, else its persisted row."""
   629	    cached = getattr(agent, "_cached_system_prompt", None)
   630	    if isinstance(cached, str) and cached:
   631	        return cached
   632	    db, session_id = getattr(agent, "_session_db", None), getattr(agent, "session_id", None)
   633	    if db is None or not isinstance(session_id, str) or not session_id:
   634	        return None
   635	    try:
   636	        row = db.get_session(session_id)
   637	    except Exception:
   638	        logger.debug("workspace snapshot: session row read failed (session=%s)", session_id, exc_info=True)
   639	        return None
   640	    prompt = row.get("system_prompt") if isinstance(row, dict) else None
   641	    return prompt if isinstance(prompt, str) and prompt else None
   642	
   643	
   644	def _seed_workspace_pin(agent: Any, key: str) -> None:
   645	    """Pin the snapshot the session's existing prompt already carries.  An agent that did not
   646	    build those bytes (resumed, or a fresh gateway/TUI agent whose first act is ``/compress``)
   647	    would otherwise re-probe git at its first rebuild and rewrite the prompt for any repo that
   648	    moved since session start.  Only a snapshot provably taken in this cwd is adopted."""
   649	    from agent.surface_switch import runtime_host_value
   650	    prompt = _session_prompt(agent)
   651	    if not prompt:
   652	        return
   653	    stored_cwd = runtime_host_value(prompt, "Current working directory")
   654	    if stored_cwd and stored_cwd != key:
   655	        return
   656	    block = _persisted_workspace_block(prompt, key)
   657	    # Only a real snapshot is adopted: a prompt without one (built on a surface without the
   658	    # coding posture, or with tools off) leaves the pin open so this build captures one.
   659	    if block:
   660	        agent._frozen_workspace_snapshot = (key, block)
   661	
   662	
   663	def _coding_parts(agent: Any) -> Tuple[List[str], List[str], List[str]]:
   664	    """``(prefix, workspace, trailing)`` coding-posture blocks; all empty
   665	    without tools or when probing fails (it must never block prompt build).
   666	
   667	    The workspace block is a live git probe after project context, ahead of the whole
   668	    volatile band; re-probing at the compaction rebuild re-emits different bytes for any
   669	    repo that moved and defeats the keep-prompt fast path.  So the bytes are pinned per
   670	    session on the agent, keyed by the probed cwd (a gateway serves many cwds), seeded from
   671	    the session's existing prompt when this agent did not build it, and replayed on
   672	    rebuilds; ``reset_session_state`` drops the pin at a session boundary.
   673	    """
   674	    try:
   675	        from agent.coding_context import coding_system_prompt_parts
   676	        if not agent.valid_tool_names:
   677	            return [], [], []
   678	        cwd = resolve_context_cwd()
   679	        cwd_key = _workspace_pin_key()
   680	        if getattr(agent, "_frozen_workspace_snapshot", None) is None:
   681	            _seed_workspace_pin(agent, cwd_key)
   682	        pinned = getattr(agent, "_frozen_workspace_snapshot", None)
   683	        # "" is a real pinned value (no workspace here) — only a cwd mismatch re-probes.
   684	        replay = pinned[1] if pinned is not None and pinned[0] == cwd_key else None
   685	        parts = coding_system_prompt_parts(platform=agent.platform, cwd=cwd, model=agent.model,
   686	                                           valid_tool_names=agent.valid_tool_names, workspace_block=replay)
   687	        if replay is None:
   688	            agent._frozen_workspace_snapshot = (cwd_key, parts[1][0] if parts[1] else "")
   689	        return parts
   690	    except Exception:
   691	        pass
   692	    return [], [], []
   693	
   694	
   695	def _post_workspace_parts(agent: Any) -> List[str]:
   696	    """Blocks that follow the worktree-specific context: environment probe
   697	    (config.yaml agent.environment_probe; one line, nothing when clean, skipped
   698	    for remote backends), bot-mode protocol, profile line, platform hint."""
   699	    parts: List[str] = []
   700	    if getattr(agent, "_environment_probe", True):
   701	        try:
   702	            from tools.env_probe import get_environment_probe_line
   703	            parts.append(get_environment_probe_line())
   704	        except Exception:
   705	            pass  # Probe failure must never block prompt build.
   706	    if getattr(agent, "_bot_mode_protocol", True):
   707	        parts.extend(_bot_mode_parts(agent))
   708	    parts += [_active_profile_line(agent), platform_hint(agent)]
   709	    return parts
   710	
   711	
   712	def _context_files_part(agent: Any, ctx_len: Optional[int], soul_loaded: bool) -> List[str]:
   713	    """Project context files (AGENTS.md etc.) for the context tier. TERMINAL_CWD
   714	    when set (gateway); None lets discovery fall back to the launch dir.  The
   715	    install-tree fallback is only legitimate for cli/tui where the launch dir
   716	    IS the user's shell cwd; desktop-pinned launch dirs are treated as the
   717	    fallback they really are so the guard can reject Hermes's bundled AGENTS.md."""
   718	    if agent.skip_context_files:
   719	        return []
   720	    launch_artifact = getattr(agent, "_context_cwd_is_launch_artifact", False)
   721	    return [_pb.build_context_files_prompt(
   722	        cwd=None if launch_artifact else resolve_context_cwd(), skip_soul=soul_loaded, context_length=ctx_len,
   723	        allow_install_tree_fallback=agent.platform in ("cli", "tui"), home_override=_agent_home(agent))]
   724	
   725	
   726	def _join_tier(parts: List[Optional[str]]) -> str:
   727	    """Join non-empty parts; None/blank entries are dropped."""
   728	    return "\n\n".join(p.strip() for p in parts if p and p.strip())
   729	
   730	
   731	def build_system_prompt_parts(agent: Any, system_message: Optional[str] = None) -> Dict[str, str]:
   732	    """Assemble the system prompt as three ordered cache tiers: ``stable`` (identity,
   733	    guidance and the coding brief), ``context`` (caller ``system_message``, project
   734	    context files, workspace snapshot and remaining workspace guidance) and
   735	    ``volatile`` (skills index, memory, user profile, external memory block,
   736	    timestamp line, runtime environment hints).  Worktree-dependent blocks follow project context so a
   737	    shared context file can remain in the longest common prefix across worktrees.
   738	    Never re-rendered mid-session."""
   739	    # Model context window scales the context-file caps; stable per conversation.
   740	    _cc_len = getattr(getattr(agent, "context_compressor", None), "context_length", None)
   741	    _ctx_len = _cc_len if isinstance(_cc_len, int) and _cc_len > 0 else None
   742	    # ── Stable tier ────────────────────────────────────────────────
   743	    stable_parts, _soul_loaded = _identity_parts(agent, _ctx_len)
   744	    # The skill_view() pointer dangles without skill tools OR without the
   745	    # hermes-agent skill installed, so the variant is chosen after the skills
   746	    # index is built; this slot holds its position.
   747	    _help_guidance_slot = len(stable_parts)
   748	    stable_parts.append(HERMES_AGENT_HELP_GUIDANCE_NO_SKILLS)
   749	    stable_parts.extend(_guidance_parts(agent))
   750	    skills_prompt = _skills_prompt(agent)
   751	    # Skill-pointer variant requires BOTH skill_view AND the hermes-agent skill
   752	    # in the rendered index (pure string check — inherits the index's stability).
   753	    if "skill_view" in (agent.valid_tool_names or set()) and "- hermes-agent:" in skills_prompt:
   754	        stable_parts[_help_guidance_slot] = HERMES_AGENT_HELP_GUIDANCE
   755	    stable_parts.extend(_alibaba_identity_part(agent))
   756	    # Pinned skills are per-agent constants (resolved once), so they live in the stable prefix.
   757	    stable_parts.extend(_auto_load_parts(agent))
   758	    # Coding posture: the operating brief stays in the stable prefix. The
   759	    # environment block contains the current cwd/backend and belongs after
   760	    # project context, not ahead of a large shared AGENTS.md block.
   761	    environment_hints = _pb.build_environment_hints()
   762	    coding_prefix_parts, coding_workspace_parts, coding_trailing_parts = _coding_parts(agent)
   763	    stable_parts.extend(coding_prefix_parts)
   764	    post_workspace_parts = _post_workspace_parts(agent)
   765	    # ── Context tier (project/worktree-dependent, may change between sessions) ──
   766	    context_parts: List[str] = []
   767	    # ephemeral_system_prompt is injected at API-call time only, never cached.
   768	    if system_message is not None:
   769	        context_parts.append(system_message)
   770	    context_parts.extend(_context_files_part(agent, _ctx_len, _soul_loaded))
   771	    if coding_workspace_parts:
   772	        context_parts.extend([*coding_workspace_parts, *coding_trailing_parts, *post_workspace_parts])
   773	    else:
   774	        # Preserve the stable placement for non-workspace sessions; there is no
   775	        # worktree snapshot whose later position would improve their prefix.
   776	        stable_parts.extend([*coding_trailing_parts, *post_workspace_parts])
   777	    # ── Volatile tier (most likely to differ on a rebuild; kept last so the stable prefix stays reusable) ──
   778	    # Skills are runtime-mutable, so the index leads the volatile band: on a longest-prefix
   779	    # backend an unchanged index stays inside the reused prefix; a changed one re-prefills from here.
   780	    volatile_parts: List[str] = [skills_prompt, *_memory_parts(agent)]
   781	    # Plugin sections are confined to one coarse anchor in the volatile tail so
   782	    # a resumed process can reconstruct the stable prefix without re-running plugins.
   783	    volatile_parts.extend(_plugin_section_blocks(_frozen_plugin_prompt_sections(agent), "after_memory"))
   784	    volatile_parts.append(_timestamp_line(agent))
   785	    # Keep the renderer-owned runtime anchor after all user/plugin prose so quoted
   786	    # host examples cannot shadow it during persisted-prompt validation.
   787	    if environment_hints:
   788	        # Embedder hints are prose too; reserve the delimiter for the renderer.
   789	        environment_hints = environment_hints.replace(_pb.RUNTIME_ENVIRONMENT_HEADING, "> " + _pb.RUNTIME_ENVIRONMENT_HEADING)
   790	        volatile_parts.append(f"{_pb.RUNTIME_ENVIRONMENT_HEADING}\n\n{environment_hints}\n\n{_pb.RUNTIME_ENVIRONMENT_END}")
   791	    return {"stable": _join_tier(stable_parts), "context": _join_tier(context_parts), "volatile": _join_tier(volatile_parts)}
   792	
   793	
   794	def build_system_prompt(agent: Any, system_message: Optional[str] = None) -> str:
   795	    """Assemble the full prompt; cached on ``agent._cached_system_prompt`` and
   796	    only rebuilt after compression.  Tiers are ordered stable -> context ->
   797	    volatile so implicit longest-prefix caches keep the unchanged scaffold."""
   798	    parts = build_system_prompt_parts(agent, system_message=system_message)
   799	    agent._cached_system_prompt_static = parts["stable"]
   800	    # Surface context-file truncation warnings in chat, not only in logs.
   801	    for warning in drain_truncation_warnings():
   802	        agent._emit_diagnostic_status(warning)
   803	    return "\n\n".join(p for p in (parts["stable"], parts["context"], parts["volatile"]) if p)
   804	
   805	
   806	def invalidate_system_prompt(agent: Any) -> None:
   807	    """Force a rebuild on the next turn (after compression): reload memory from
   808	    disk and clear the frozen plugin snapshot (previous bytes stashed as the
   809	    fail-open fallback) so plugins re-render at the same boundary.
   810	
   811	    Called after context compression events. Also reloads memory from disk so the rebuilt prompt captures
   812	    any writes from this session, and clears the frozen plugin-section snapshot so plugins re-render at the
   813	    same boundary (maintainer-directed, #95681 arc): a plugin section is just another prompt block carrying
   814	    state — freezing it while memory, skills, and guidance refresh would recreate the stale-block disease
   815	    inside plugin-land. The previous bytes are stashed so a plugin whose render RAISES falls back to its
   816	    last good section instead of vanishing (fail-open guard, not a freeze).
   817	    """
   818	    agent._cached_system_prompt = None
   819	    agent._cached_system_prompt_static = None
   820	    if hasattr(agent, "_plugin_system_prompt_sections_snapshot"):
   821	        agent._plugin_system_prompt_sections_previous = agent._plugin_system_prompt_sections_snapshot
   822	        del agent._plugin_system_prompt_sections_snapshot
   823	    if agent._memory_store:
   824	        agent._memory_store.load_from_disk()
   825	
   826	
   827	def reconstruct_static_prefix(agent: Any, system_message: Optional[str] = None, *, log_label: str = "restore") -> None:
   828	    """Reconstruct ``_cached_system_prompt_static`` for a stored prompt.
   829	    Only the full prompt is persisted, so restore / keep-prompt compression /
   830	    mid-turn failover to a cache-on provider must rebuild the stable tier to
   831	    regain the ``[static, volatile]`` layout.  The rebuilt tier is used ONLY
   832	    when the stored prompt literally starts with it; otherwise static stays
   833	    None and the stored bytes are sent untouched.  A failed rebuild is memoized
   834	    per stored prompt so the retry-loop hot path doesn't redo the file I/O."""
   835	    stored = getattr(agent, "_cached_system_prompt", None)
   836	    existing = getattr(agent, "_cached_system_prompt_static", None)
   837	    if (
   838	        not getattr(agent, "_use_prompt_caching", False)
   839	        or not isinstance(stored, str) or not stored
   840	        or (isinstance(existing, str) and existing and stored.startswith(existing))
   841	        or getattr(agent, "_static_rebuild_failed_for", None) == stored
   842	    ):
   843	        return
   844	    try:
   845	        static = build_system_prompt_parts(agent, system_message=system_message)["stable"]
   846	        if static and stored.startswith(static):
   847	            agent._cached_system_prompt_static = static
   848	            agent._static_rebuild_failed_for = None
   849	            return
   850	    except Exception:
   851	        logger.debug("static system-prefix reconstruction failed on %s", log_label, exc_info=True)
   852	    agent._cached_system_prompt_static = None
   853	    agent._static_rebuild_failed_for = stored
   854	
   855	
   856	def format_tools_for_system_message(agent: Any) -> str:
   857	    """JSON tool definitions in the trajectory format."""
   858	    if not agent.tools:
   859	        return "[]"
   860	    return json.dumps([{"name": t["function"]["name"], "description": t["function"].get("description", ""),
   861	                        "parameters": t["function"].get("parameters", {}),
   862	                        "required": None}  # Match the format in the example
   863	                       for t in agent.tools], ensure_ascii=False)
   864	
   865	
   866	__all__ = ["build_system_prompt_parts", "build_system_prompt", "invalidate_system_prompt",
   867	           "platform_hint", "restore_plugin_prompt_sections", "format_tools_for_system_message"]
   868	
   869	
   870	# ---- BEGIN PLUGIN-COMPAT (revert-scheduled; see COMPAT_MANIFEST.md) ----
   871	# Names external plugins imported from this module before the Sep 2026 decomposition.
   872	# Internal code MUST NOT use these (scripts/check_compat_pointers.py fails CI if it does).
   873	# The whole block is removed by reverting the commit that added it.
   874	
   875	
   876	_PLUGIN_COMPAT_LAZY = {
   877	    'OPENAI_MODEL_EXECUTION_GUIDANCE': ('agent.prompt_builder', 'OPENAI_MODEL_EXECUTION_GUIDANCE'),
   878	}
   879	
   880	
   881	def __getattr__(name):  # PEP 562 — lazy so no import cycles
   882	    target = _PLUGIN_COMPAT_LAZY.get(name)
   883	    if target is None:
   884	        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
   885	    import importlib
   886	    from hermes_cli.plugin_compat import warn_once
   887	    warn_once(__name__, name, *target)
   888	    return getattr(importlib.import_module(target[0]), target[1])
   889	# ---- END PLUGIN-COMPAT ----
