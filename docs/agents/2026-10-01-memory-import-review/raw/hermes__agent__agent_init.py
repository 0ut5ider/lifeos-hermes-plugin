     1	"""Implementation of :meth:`AIAgent.__init__` as ``init_agent(agent, ...)``.
     2	
     3	``init_agent`` is a thin, ordered orchestrator over ``_init_*`` / ``_build_*`` phase
     4	helpers (routing → callbacks → client → tools → session → config sections → compression →
     5	context engine). Phase ORDER is load-bearing: later phases read attributes earlier ones set.
     6	Symbols that tests patch on ``run_agent.*`` (``OpenAI``, ``get_tool_definitions``,
     7	``logger``, …) are resolved through :func:`_ra` so the patch contract is preserved.
     8	"""
     9	
    10	from __future__ import annotations
    11	
    12	import logging
    13	import os
    14	import re
    15	import sys
    16	import threading
    17	import time
    18	from collections import deque
    19	from contextlib import suppress
    20	from datetime import datetime
    21	from types import SimpleNamespace
    22	from typing import Any, Callable, Dict, List, Optional
    23	from urllib.parse import parse_qs, urlparse, urlunparse
    24	
    25	from agent.context_compressor import ContextCompressor
    26	from agent.agent_runtime_helpers import _ra
    27	from agent.iteration_budget import IterationBudget, normalize_budget_warning_ratio
    28	from agent.memory_manager import StreamingContextScrubber
    29	from agent.memory_provider import is_core_memory_provider
    30	from agent.session_activity import ActivityProvenance
    31	from agent.model_metadata import (
    32	    MINIMUM_CONTEXT_LENGTH, fetch_model_metadata, is_local_endpoint, query_ollama_num_ctx
    33	)
    34	from agent.process_bootstrap import _install_safe_stdio
    35	from agent.subdirectory_hints import SubdirectoryHintTracker
    36	from agent.think_scrubber import StreamingThinkScrubber
    37	from agent.tool_guardrails import (
    38	    ToolCallGuardrailConfig, ToolCallGuardrailController
    39	)
    40	from hermes_cli.config import DEFAULT_CONFIG, cfg_get
    41	from hermes_cli.route_identity import normalize_route_base_url
    42	from hermes_cli.timeouts import get_provider_request_timeout
    43	from hermes_constants import get_hermes_home
    44	from hermes_state_ids import new_session_id
    45	from utils import base_url_host_matches, is_truthy_value
    46	
    47	# Same logger name as run_agent so caplog/patches on "run_agent" see our records.
    48	logger = logging.getLogger("run_agent")
    49	
    50	
    51	# Deduped: the gateway builds a fresh AIAgent per message, so it would warn every turn.
    52	_warned_unavailable_providers: set[str] = set()
    53	
    54	
    55	def _warn_memory_provider_unavailable(name: str, reason: str = "") -> None:
    56	    """Warn once per provider that a configured memory provider is unavailable.
    57	
    58	    ``is_available()`` is a side-effect-free hot-path check and can't log itself; without this
    59	    the provider is silently dropped. ``reason`` (the provider's ``unavailable_reason()`` hint)
    60	    can only reach the user here, so it is appended when present.
    61	    """
    62	    if name in _warned_unavailable_providers:
    63	        return
    64	    _warned_unavailable_providers.add(name)
    65	    logger.warning(
    66	        "Memory provider %r is selected but reports unavailable — external memory "
    67	        "is disabled for this session (built-in memory still works). Check the "
    68	        "provider's credentials/config with 'hermes memory status'. Note: "
    69	        "systemd/gateway services do not inherit ~/.hermes/.env automatically; set "
    70	        "any required variables in the service environment.%s",
    71	        name,
    72	        f" {reason}" if reason else "",
    73	    )
    74	
    75	
    76	def _provider_default_routes(provider: str) -> set[str]:
    77	    """Return known exact default routes for a canonical provider id."""
    78	    routes: set[str] = set()
    79	
    80	    def add(value):
    81	        route = normalize_route_base_url(value)
    82	        if route:
    83	            routes.add(route)
    84	
    85	    with suppress(Exception):
    86	        from hermes_cli.providers import HERMES_OVERLAYS, get_provider
    87	        overlay = HERMES_OVERLAYS.get(provider)
    88	        provider_def = get_provider(provider, allow_network=False)
    89	        add(getattr(overlay, "base_url_override", ""))
    90	        add(getattr(provider_def, "base_url", ""))
    91	
    92	    with suppress(Exception):
    93	        from providers import get_provider_profile
    94	        add(getattr(get_provider_profile(provider), "base_url", ""))
    95	
    96	    with suppress(Exception):
    97	        from hermes_cli.auth import PROVIDER_REGISTRY
    98	        from hermes_cli.models import normalize_provider as normalize_model_provider
    99	        from hermes_cli.providers import normalize_provider as normalize_registry_provider
   100	        for provider_id, config in PROVIDER_REGISTRY.items():
   101	            if normalize_registry_provider(normalize_model_provider(provider_id)) == provider:
   102	                add(getattr(config, "inference_base_url", ""))
   103	
   104	    if provider == "gemini":
   105	        routes.update(f"{route.rstrip('/')}/openai" for route in list(routes))
   106	    return routes
   107	
   108	
   109	def _context_route_mismatch(
   110	    configured_base_url: Any, active_base_url: Any, configured_provider: Any, active_provider: Any,
   111	    *, already_normalized: bool = False,
   112	) -> bool:
   113	    """Return whether a context pin's configured route differs from runtime."""
   114	    _norm = (lambda v: str(v or "")) if already_normalized else normalize_route_base_url
   115	    configured_route, active_route = _norm(configured_base_url), _norm(active_base_url)
   116	    if configured_route:
   117	        return configured_route != active_route
   118	
   119	    configured_provider = str(configured_provider or "").strip()
   120	    active_provider = str(active_provider or "").strip()
   121	    if not configured_provider:
   122	        return False
   123	    try:
   124	        from hermes_cli.models import normalize_provider as normalize_model_provider
   125	        configured_provider = normalize_model_provider(configured_provider)
   126	        active_provider = normalize_model_provider(active_provider)
   127	    except Exception:
   128	        configured_provider = configured_provider.lower()
   129	        active_provider = active_provider.lower()
   130	    with suppress(Exception):
   131	        from hermes_cli.providers import normalize_provider as normalize_registry_provider
   132	        configured_provider = normalize_registry_provider(configured_provider)
   133	        active_provider = normalize_registry_provider(active_provider)
   134	
   135	    if active_route:
   136	        configured_routes = _provider_default_routes(configured_provider)
   137	        if configured_routes:
   138	            return active_route not in configured_routes
   139	        # Named/custom providers have no catalog default routes: an empty configured URL
   140	        # with a matching provider identity is the same route (gateway display paths
   141	        # compare the raw empty model.base_url and must not drop model.context_length).
   142	        return not (active_provider and configured_provider == active_provider)
   143	    return bool(
   144	        configured_provider and active_provider and configured_provider != active_provider
   145	    )
   146	
   147	
   148	def _normalize_custom_provider_name(value: Any) -> str:
   149	    """Mirror runtime normalization for a requested custom-provider identity."""
   150	    return str(value or "").strip().lower().replace(" ", "-")
   151	
   152	
   153	def _custom_provider_runtime_ids(value: Any) -> set[str]:
   154	    """Return raw/menu identities that runtime accepts for a configured name."""
   155	    normalized = _normalize_custom_provider_name(value)
   156	    if not normalized:
   157	        return set()
   158	    return {normalized, f"custom:{normalized}"}
   159	
   160	
   161	def _build_codex_gpt5_autoraise_notice(
   162	    autoraise: Dict[str, Any], context_length: Optional[int] = None
   163	) -> str:
   164	    """One-time notice when Codex gpt-5.x raises compaction (``autoraise``: model/from/to).
   165	
   166	    ``context_length`` is the live-resolved window (Codex's catalog shifts server-side) so the
   167	    banner reports what this session got. Printed for CLI and replayed via status_callback for
   168	    gateway users, so it must be self-contained and include the exact opt-back-out command.
   169	    """
   170	    model = str(autoraise.get("model") or "gpt-5.4/5.5").strip().lower().rsplit("/", 1)[-1]
   171	    if isinstance(context_length, int) and context_length > 0:
   172	        cap = f"{round(context_length / 1000)}K"
   173	    else:
   174	        # Static fallback: codex-spark is natively 128K; gpt-5.4/5.5/5.6 are capped at 272K.
   175	        cap = "128K" if model.startswith("gpt-5.3-codex-spark") else "272K"
   176	    from_pct = int(round(autoraise["from"] * 100))
   177	    to_pct = int(round(autoraise["to"] * 100))
   178	    return (
   179	        f"ℹ Codex {model} caps context at {cap}, so auto-compaction was raised "
   180	        f"to {to_pct}% (from {from_pct}%) to use more of the window before "
   181	        f"summarizing.\n"
   182	        f"  Opt back out: hermes config set compression.codex_gpt55_autoraise false"
   183	    )
   184	
   185	
   186	def _resolve_compression_threshold(
   187	    global_threshold: float, model_cthresh: Optional[float], *, model: Optional[str] = None,
   188	    is_codex_autoraise: bool,
   189	) -> tuple[float, Optional[Dict[str, Any]]]:
   190	    """Global compaction threshold merged with a per-model override.
   191	
   192	    Returns ``(threshold, autoraise_notice)``; the notice is set only when a Codex autoraise
   193	    actually RAISES the threshold — it never lowers a higher user value (the user deliberately
   194	    keeps more raw context). Other overrides (Arcee Trinity) stay unconditional.
   195	    """
   196	    if model_cthresh is None:
   197	        return global_threshold, None
   198	    if is_codex_autoraise:
   199	        if model_cthresh <= global_threshold + 1e-9:
   200	            return global_threshold, None
   201	        return model_cthresh, {"model": model, "from": global_threshold, "to": model_cthresh}
   202	    return model_cthresh, None
   203	
   204	
   205	def _codex_gpt55_autoraise_notice_marker():
   206	    """Per-profile marker path (``$HERMES_HOME`` is profile-scoped; not a config key)."""
   207	    return get_hermes_home() / ".codex_gpt55_autoraise_notice"
   208	
   209	
   210	def _codex_gpt55_autoraise_notice_state(autoraise: Dict[str, Any]) -> str:
   211	    """Notice identity keyed on what it displays (model + from→to percentages).
   212	
   213	    An unchanged threshold stays silent across restarts; a changed global threshold or a
   214	    different autoraised Codex model re-notifies once.
   215	    """
   216	    model = str(autoraise.get("model") or "").strip().lower().rsplit("/", 1)[-1]
   217	    from_pct = int(round(float(autoraise["from"]) * 100))
   218	    to_pct = int(round(float(autoraise["to"]) * 100))
   219	    return f"{model}:{from_pct}:{to_pct}"
   220	
   221	
   222	def _codex_gpt55_autoraise_notice_seen(autoraise: Dict[str, Any]) -> bool:
   223	    """True if this exact notice was already shown for this profile (unreadable = unseen)."""
   224	    try:
   225	        current = _codex_gpt55_autoraise_notice_state(autoraise)
   226	        return _codex_gpt55_autoraise_notice_marker().read_text(
   227	            encoding="utf-8"
   228	        ).strip() == current
   229	    except (OSError, KeyError, TypeError, ValueError):
   230	        return False
   231	
   232	
   233	def _record_codex_gpt55_autoraise_notice(autoraise: Dict[str, Any]) -> None:
   234	    """Persist that the notice was shown. Best-effort: a failure only re-shows it later."""
   235	    with suppress(OSError, KeyError, TypeError, ValueError):
   236	        marker = _codex_gpt55_autoraise_notice_marker()
   237	        marker.parent.mkdir(parents=True, exist_ok=True)
   238	        marker.write_text(_codex_gpt55_autoraise_notice_state(autoraise), encoding="utf-8")
   239	
   240	
   241	def _normalized_custom_base_url(value: Any) -> str:
   242	    if not isinstance(value, str):
   243	        return ""
   244	    return value.strip().rstrip("/")
   245	
   246	
   247	def _custom_provider_model_matches(agent_model: str, entry: Dict[str, Any]) -> bool:
   248	    agent_model_norm = str(agent_model or "").strip().lower()
   249	    # Multi-model entries (`providers.<name>.models` mapping / legacy `models:` list):
   250	    # matching ANY catalog entry counts, else a provider whose `model` differs from the
   251	    # session model drops its extra_body (e.g. OpenAI service_tier) → wrong billing tier.
   252	    models = entry.get("models")
   253	    catalog = [str(m).strip().lower() for m in models] if isinstance(models, (dict, list, tuple)) else []
   254	    if catalog and agent_model_norm in catalog:
   255	        return True
   256	    provider_model = str(entry.get("model", "") or "").strip().lower()
   257	    return (not provider_model and not catalog) or provider_model == agent_model_norm
   258	
   259	
   260	def _custom_provider_extra_body_for_agent(
   261	    *, provider: str, model: str, base_url: str, custom_providers: List[Dict[str, Any]]
   262	) -> Optional[Dict[str, Any]]:
   263	    provider_norm = (provider or "").strip().lower()
   264	    if provider_norm != "custom" and not provider_norm.startswith("custom:"):
   265	        return None
   266	    provider_key_filter = provider_norm.partition(":")[2].strip()
   267	    target_url = _normalized_custom_base_url(base_url)
   268	    if not target_url:
   269	        return None
   270	
   271	    fallback: Optional[Dict[str, Any]] = None
   272	    for entry in custom_providers or []:
   273	        if not isinstance(entry, dict):
   274	            continue
   275	        entry_keys = {
   276	            str(entry.get("provider_key", "") or "").strip().lower(),
   277	            str(entry.get("name", "") or "").strip().lower(),
   278	        }
   279	        if provider_key_filter and provider_key_filter not in entry_keys:
   280	            continue
   281	        if _normalized_custom_base_url(entry.get("base_url")) != target_url:
   282	            continue
   283	        extra_body = entry.get("extra_body")
   284	        if not isinstance(extra_body, dict) or not extra_body:
   285	            continue
   286	        if str(entry.get("model", "") or "").strip():
   287	            if _custom_provider_model_matches(model, entry):
   288	                return dict(extra_body)
   289	        elif fallback is None:
   290	            fallback = dict(extra_body)
   291	    return fallback
   292	
   293	
   294	def _merge_custom_provider_extra_body(agent, custom_providers: List[Dict[str, Any]]) -> None:
   295	    extra_body = _custom_provider_extra_body_for_agent(
   296	        provider=agent.provider, model=agent.model, base_url=agent.base_url,
   297	        custom_providers=custom_providers,
   298	    )
   299	    if not extra_body:
   300	        return
   301	    overrides = dict(getattr(agent, "request_overrides", {}) or {})
   302	    merged_extra_body = dict(extra_body)
   303	    existing_extra_body = overrides.get("extra_body")
   304	    if isinstance(existing_extra_body, dict):
   305	        merged_extra_body.update(existing_extra_body)
   306	    overrides["extra_body"] = merged_extra_body
   307	    agent.request_overrides = overrides
   308	
   309	
   310	def _normalize_run_budget_seconds(value) -> Optional[float]:
   311	    """Positive float or None (feature off). ``bool`` rejected: YAML ``true`` → 1s budget."""
   312	    if value is None or isinstance(value, bool):
   313	        return None
   314	    try:
   315	        seconds = float(value)
   316	    except (TypeError, ValueError):
   317	        return None
   318	    return seconds if seconds > 0 else None  # NaN compares False → None
   319	
   320	
   321	
   322	def _refuse_checkpoint_required_on_codex_app_server(
   323	    checkpoint_required: bool, api_mode: Optional[str]
   324	) -> None:
   325	    """Fail closed at init: the codex app-server compacts its own thread without a truthful
   326	    pre-compaction boundary (default "native" mode), so a required checkpoint can't be
   327	    guaranteed — the compress_context() guard alone cannot cover native turns."""
   328	    if checkpoint_required and api_mode == "codex_app_server":
   329	        raise RuntimeError(
   330	            "BLOCKED_MISSING_PREREQUISITE: compression.checkpoint_required "
   331	            "is incompatible with the codex_app_server API mode: the codex "
   332	            "agent compacts its own thread without a truthful pre-compaction "
   333	            "transcript boundary, so a required pre-compress checkpoint "
   334	            "cannot be guaranteed. Disable compression.checkpoint_required "
   335	            "or use a non-app-server API mode."
   336	        )
   337	
   338	
   339	def _parse_config_int(raw: Any, default: int) -> int:
   340	    """Strict int coercion: rejects bool (YAML ``true`` → 1) and fractional floats."""
   341	    if isinstance(raw, bool):
   342	        return default
   343	    if isinstance(raw, int):
   344	        return raw
   345	    if isinstance(raw, float):
   346	        return int(raw) if raw.is_integer() else default
   347	    try:
   348	        return int(str(raw).strip())
   349	    except (TypeError, ValueError):
   350	        return default
   351	
   352	
   353	def _cfg_flag(cfg: Dict[str, Any], key: str, default: bool) -> bool:
   354	    """Legacy string-set truthiness used by the ``compression`` section."""
   355	    return str(cfg.get(key, default)).lower() in {"true", "1", "yes"}
   356	
   357	
   358	def _cfg_dict(cfg: Dict[str, Any], key: str) -> Dict[str, Any]:
   359	    """``cfg[key]`` if it is a mapping, else ``{}`` (malformed sections are ignored)."""
   360	    section = cfg.get(key, {})
   361	    return section if isinstance(section, dict) else {}
   362	
   363	
   364	class CompressionSettings(SimpleNamespace):
   365	    """Parsed ``compression`` config section (see ``_parse_compression_config``)."""
   366	
   367	
   368	_EXPLICIT_API_MODES = {
   369	    "chat_completions", "codex_responses", "anthropic_messages", "bedrock_converse",
   370	    "codex_app_server",
   371	}
   372	
   373	
   374	def _resolve_api_mode(agent, api_mode, provider_name, base_url):
   375	    """Set ``agent.api_mode`` (and provider rewrites) — ordered ladder, first match wins."""
   376	    from hermes_cli.providers import is_actual_route
   377	    from agent.transports import registered_api_modes
   378	    host, url = agent._base_url_hostname, agent._base_url_lower
   379	    if is_actual_route(agent.provider, base_url):
   380	        agent.api_mode = "chat_completions"
   381	    elif api_mode in _EXPLICIT_API_MODES or (api_mode and api_mode in registered_api_modes()):
   382	        # A provider plugin's own dialect (``register_transport(api_mode, cls)``) is as explicit
   383	        # as the in-tree modes; rewriting it to chat_completions silently dropped its transport.
   384	        agent.api_mode = api_mode
   385	    elif agent.provider in {"openai-codex", "xai", "xai-oauth"}:
   386	        agent.api_mode = "codex_responses"
   387	    elif provider_name is None and host == "chatgpt.com" and "/backend-api/codex" in url:
   388	        agent.api_mode = "codex_responses"
   389	        agent.provider = "openai-codex"
   390	    elif provider_name is None and host == "api.x.ai":
   391	        agent.api_mode = "codex_responses"
   392	        agent.provider = "xai"
   393	    elif agent.provider == "anthropic" or (provider_name is None and host == "api.anthropic.com"):
   394	        agent.api_mode = "anthropic_messages"
   395	        agent.provider = "anthropic"
   396	    elif url.rstrip("/").endswith("/anthropic"):
   397	        # Third-party Anthropic-compatible endpoints (MiniMax, DashScope) end in /anthropic.
   398	        agent.api_mode = "anthropic_messages"
   399	    elif agent.provider == "bedrock" or (
   400	        host.startswith("bedrock-runtime.") and base_url_host_matches(url, "amazonaws.com")
   401	    ):
   402	        agent.api_mode = "bedrock_converse"
   403	    elif agent.provider in {"nous", "nous-portal", "nousresearch"}:
   404	        # Portal is dual-wire (anthropic/* → Messages, else chat_completions); covers direct
   405	        # AIAgent construction without a resolved runtime.
   406	        from hermes_cli.providers import nous_api_mode
   407	        agent.api_mode = nous_api_mode(agent.model)
   408	    else:
   409	        # Host-mandated wire check — LAST, so the provider-slug rewrites above always win.
   410	        # Covers api.meta.ai → codex_responses (prompt caching: 0% on chat vs 93-99%).
   411	        # URL-driven, not provider-name-driven: `providers.meta` may point anywhere.
   412	        try:
   413	            # Note: provider="meta" without an api.meta.ai base_url (or with a non-api.meta.ai base_url)
   414	            # intentionally falls through to chat_completions here. The wire protocol for Meta is URL-driven
   415	            # BY DESIGN, not provider-name-driven, because user config `providers.meta` may point at any
   416	            # OpenAI-compatible endpoint, and forcing `codex_responses` on the provider name alone would
   417	            # break custom endpoints named "meta" that do not host the Responses API. See #63425.
   418	            from hermes_cli.providers import host_mandated_api_mode as _host_mandated_api_mode
   419	            _mandated = _host_mandated_api_mode(base_url or "")
   420	        except Exception:
   421	            _mandated = None
   422	        agent.api_mode = _mandated if _mandated is not None else "chat_completions"
   423	
   424	
   425	def _finalize_routing(agent, api_mode, credential_pool):
   426	    from hermes_cli.providers import is_actual_route
   427	    # Credential-pool validation runs AFTER provider auto-detection so a pool scoped to
   428	    # "anthropic" isn't rejected for provider=None + anthropic.com URL.
   429	    # Regression from #63048 which placed this check before the URL-based auto-detection block above (fixed
   430	    # #63425).
   431	    if credential_pool is not None:
   432	        try:
   433	            from agent.credential_pool import credential_pool_matches_provider
   434	            if not credential_pool_matches_provider(
   435	                credential_pool, agent.provider, base_url=agent.base_url,
   436	            ):
   437	                agent._credential_pool = None
   438	        except Exception:
   439	            agent._credential_pool = None
   440	
   441	    # Warm the transport cache so import errors surface at init (non-fatal: some modes lack one).
   442	    with suppress(Exception):
   443	        agent._get_transport()
   444	
   445	    # The Nous agent key lives ~1 h. Without the proactive refresher every agent in the process
   446	    # discovers expiry reactively, on its own next request, all in the same minute: with 200
   447	    # in-process subagents that was a 401 storm each hour (620 in one run) and the credential
   448	    # pool benched the provider for all of them. The gateway and web server start this thread
   449	    # at boot; the CLI process (and everything spawned inside it) never did. Idempotent,
   450	    # process-wide, daemon.
   451	    if agent.provider == "nous":
   452	        with suppress(Exception):
   453	            from hermes_cli.nous_auth_keepalive import start_nous_auth_keepalive
   454	            start_nous_auth_keepalive()
   455	
   456	    with suppress(Exception):
   457	        from hermes_cli.model_normalize import (
   458	            _AGGREGATOR_PROVIDERS, normalize_model_for_provider
   459	        )
   460	
   461	        if agent.provider not in _AGGREGATOR_PROVIDERS:
   462	            agent.model = normalize_model_for_provider(agent.model, agent.provider)
   463	
   464	    # Nous model policy follows the ROUTE (the welcome host serves one model); a credential-pool
   465	    # swap can change the route later, so ``_swap_credential`` applies the same helper again.
   466	    from hermes_cli.anon_auth import pin_model_for_route
   467	    agent.model = pin_model_for_route(agent.provider, agent.base_url, agent.model)
   468	
   469	    # Auto-upgrade to Responses for GPT-5.x-style models and direct OpenAI URLs, unless
   470	    # api_mode was explicit, the runtime is ACP (`acp://` clients route themselves, no
   471	    # Responses surface) or Azure OpenAI (gpt-5.x on /chat/completions only). Provider
   472	    # exceptions live in _provider_model_requires_responses_api.
   473	    from hermes_cli.runtime_provider_backends import _is_external_process_provider
   474	
   475	    _base_lower = str(agent.base_url or "").lower()
   476	    if (
   477	        # GPT-5.x models usually require the Responses API path, but some providers have exceptions (for
   478	        # example Copilot's gpt-5-mini still uses chat completions). ACP runtimes are excluded: an ACP
   479	        # client handles its own routing and does not implement the Responses API surface. Keyed on the
   480	        # `acp://` scheme AND the profile's external_process auth_type (an `<X>_ACP_BASE_URL` override
   481	        # can carry an https marker), not one vendor, so every ACP client is covered. When api_mode was explicitly
   482	        # provided, respect it — the user knows what their endpoint supports (#10473). Exception: Azure
   483	        # OpenAI serves gpt-5.x on /chat/completions and does NOT support the Responses API — skip the
   484	        # upgrade for Azure (openai.azure.com), even though it looks OpenAI-compatible.
   485	        api_mode is None
   486	        and agent.api_mode == "chat_completions"
   487	        and not is_actual_route(agent.provider, agent.base_url)
   488	        and not _base_lower.startswith(("acp://", "acp+tcp://"))
   489	        and not _is_external_process_provider(agent.provider)
   490	        and not agent._is_azure_openai_url()
   491	        and (
   492	            agent._is_direct_openai_url()
   493	            or agent._provider_model_requires_responses_api(agent.model, provider=agent.provider)
   494	        )
   495	    ):
   496	        agent.api_mode = "codex_responses"
   497	        # Invalidate the eager-warmed transport cache — api_mode changed after the warm.
   498	        if hasattr(agent, "_transport_cache"):
   499	            agent._transport_cache.clear()
   500	
   501	    # Pre-warm the OpenRouter metadata cache (1h TTL) off-thread so the first pricing estimate
   502	    # doesn't block. Process-level Event guard: an unguarded spawn leaks a thread per message.
   503	    if (agent.provider == "openrouter" or agent._is_openrouter_url()) and \
   504	            not _ra()._openrouter_prewarm_done.is_set():
   505	        _ra()._openrouter_prewarm_done.set()
   506	        threading.Thread(
   507	            target=fetch_model_metadata, daemon=True, name="openrouter-prewarm",
   508	        ).start()
   509	
   510	
   511	def _set_defaults(agent, table: Dict[str, Any]) -> None:
   512	    """Assign each ``name -> value`` on ``agent``; callables are factories (fresh per agent)."""
   513	    for name, value in table.items():
   514	        setattr(agent, name, value() if callable(value) else value)
   515	
   516	
   517	# Control-flow state (interrupts / steer / redirect / delegation / background review).
   518	_CONTROL_STATE: Dict[str, Any] = {
   519	    "_executing_tools": False,  # lets _vprint print while tools run with stream consumers on
   520	    "_trim_after_tool_batch": False,  # a >=1 MB tool result was committed; trim once the batch unwinds
   521	    "_tool_guardrails": ToolCallGuardrailController,
   522	    "_tool_guardrail_halt_decision": None,
   523	    # Interrupts. Hard cancellation is separate from redirect/message state; the Event makes
   524	    # the cause atomic for auxiliary stream pollers.
   525	    "_interrupt_requested": False,
   526	    "_interrupt_message": None,  # optional message that triggered the interrupt
   527	    "_hard_interrupt_requested": threading.Event,
   528	    "_execution_thread_id": None,  # set at run_conversation() start
   529	    "_interrupt_thread_signal_pending": False,
   530	    "_client_lock": threading.RLock,
   531	    "_model_request_active": threading.Event,
   532	    "_supports_active_turn_redirect": True,
   533	    # /steer: the drain hook appends the note to the last tool result after the current
   534	    # batch — no interrupt, no new user turn (role alternation preserved).
   535	    "_pending_steer": None,
   536	    "_pending_steer_lock": threading.Lock,
   537	    # Active-turn redirect: keep the valid turn prefix, cancel only the in-flight request,
   538	    # rebuild the tail with the correction. Drained at a role-safe boundary.
   539	    "_pending_redirect": None,
   540	    "_pending_redirect_lock": threading.Lock,
   541	    # Concurrent-tool worker tids: `_set_interrupt` on `_execution_thread_id` alone doesn't
   542	    # reach ThreadPoolExecutor workers, so interrupt()/clear_interrupt() fan out to these.
   543	    "_tool_worker_threads": set,
   544	    "_tool_worker_threads_lock": threading.Lock,
   545	    # Subagent delegation: depth (0 = top-level) and running children (interrupt propagation).
   546	    "_delegate_depth": 0,
   547	    "_active_children": list,
   548	    "_active_children_lock": threading.Lock,
   549	    # Background review (agent/background_review.py): the run is installed before the worker
   550	    # starts and fences its first provider phase; the agent pointer enables interrupt fan-out.
   551	    "_background_review_agent": None,
   552	    "_background_review_run": None,
   553	    "_background_review_lock": threading.Lock,
   554	}
   555	
   556	# Per-turn bookkeeping: budgets, activity tracking, rate-limit/credits telemetry.
   557	_TURN_STATE: Dict[str, Any] = {
   558	    # Intermediate pressure warnings made models give up early; ordinary conversations
   559	    # remain opt-in. Dispatcher workers receive a bounded completion checkpoint.
   560	    "_iteration_budget_warning_injected": False,
   561	    "_budget_exhausted_injected": False,
   562	    "_budget_grace_call": False,
   563	    "_run_budget_started_at": None,  # set by turn_context.prepare_turn when a budget is active
   564	    "_run_budget_wrapup_injected": False,  # one-shot latch for the 80% wrap-up notice
   565	    # Activity tracking (API call / tool / stream chunk) for the gateway timeout handler and
   566	    # "still working" notifications. Named provenances are stamped only by compression writers.
   567	    "_last_activity_ts": lambda: time.time(),
   568	    "_last_activity_desc": "initializing",
   569	    "_last_activity_provenance": ActivityProvenance.UNKNOWN,
   570	    "_session_activity_last_persist_mono": 0.0,  # rate-limits durable SessionDB stamps
   571	    "_current_tool": None,
   572	    "_api_call_count": 0,
   573	    # Opt-out for the between-turns MCP refresh; set on forks that need byte-identical tools[].
   574	    "_skip_mcp_refresh": False,
   575	    # Registry generation of the tool snapshot (set in _load_tools): a late refresh rejects
   576	    # a stale rebuild instead of clobbering a newer one.
   577	    "_tool_snapshot_generation": 0,
   578	    "_rate_limit_state": None,  # from x-ratelimit-* headers; read by /usage
   579	    # Credits tracking (dev-only, HERMES_DEV_CREDITS) from x-nous-credits-* headers; session
   580	    # start is latched on the first header so cumulative spend can be reported.
   581	    "_credits_state": None,
   582	    "_credits_session_start_micros": None,
   583	    "_or_cache_hits": 0,  # X-OpenRouter-Cache-Status: HIT count
   584	}
   585	
   586	# Session persistence state.
   587	_SESSION_STATE: Dict[str, Any] = {
   588	    "_session_messages": list,
   589	    # Responses encrypted-reasoning replay: routes that 400 with ``invalid_encrypted_content``
   590	    # make the loop disable it for the session (stateless continuity).
   591	    "_codex_reasoning_replay_enabled": True,
   592	    "_memory_write_origin": "assistant_tool",
   593	    "_memory_write_context": "foreground",
   594	    # Cached system prompt (built once, rebuilt on compression) + its cross-session-stable
   595	    # prefix, kept separately only to place an early cache marker.
   596	    "_cached_system_prompt": None,
   597	    "_cached_system_prompt_static": None,
   598	    # skills.auto_load rendered ONCE per agent: every rebuild (model switch, compression,
   599	    # static-prefix restoration) reuses these exact bytes instead of re-reading config/skills.
   600	    "_auto_load_skills_resolved": False,
   601	    "_auto_load_skills_result": ("", [], []),
   602	    # ``(cwd, workspace_block)`` pinned on the first build: the git/workspace snapshot is
   603	    # probed once per session and replayed on every rebuild, so a moving repo can't push the
   604	    # prefix-cache divergence point ahead of the volatile band at a compaction boundary.
   605	    "_frozen_workspace_snapshot": None,
   606	    # Whether close() also closes _session_db. False: a caller-supplied handle is usually the
   607	    # SHARED launch handle; callers handing over a DEDICATED handle set True.
   608	    "_owns_session_db": False,
   609	    # Close flush and turn-start flush can overlap; the durable marker lives on each message
   610	    # dict, so its test-and-append is serialized per agent.
   611	    "_session_persist_lock": threading.RLock,
   612	    # CLI's just-accepted user dict, reused by turn setup so its durable marker survives a
   613	    # close-persistence race.
   614	    "_pending_cli_user_message": None,
   615	    "_last_flushed_db_idx": 0,  # DB-write cursor (prevents duplicate writes)
   616	    "_session_db_created": False,  # DB row deferred to run_conversation()
   617	    # False on helper agents (compression / hygiene / review forks) that hand the session to
   618	    # a continuation row that must stay open.
   619	    "_end_session_on_close": True,
   620	    # True on the background review fork: never persist or publish session lifecycle hooks,
   621	    # so its harness turn can't hijack or appear under the live session.
   622	    "_persist_disabled": False,
   623	}
   624	
   625	# Streaming delivery state.
   626	_STREAM_STATE: Dict[str, Any] = {
   627	    "_stream_callback": None,  # streaming TTS; set early so _vprint can reference it
   628	    "_stream_needs_break": False,  # one "\n\n" before the next real text delta after tools
   629	    # Stateful scrubbers: <memory-context> / thinking spans split across deltas defeat
   630	    # per-delta regexes (both tags must be in one string).
   631	    "_stream_context_scrubber": StreamingContextScrubber,
   632	    "_stream_think_scrubber": StreamingThinkScrubber,
   633	    "_current_streamed_assistant_text": "",  # so a later completed interim isn't re-sent
   634	    "_delivered_interim_texts": set,  # interims this user turn (spans Codex continuations)
   635	    # Single-writer guard for the delta sink: each attempt claims a monotonic writer token and
   636	    # the sink drops chunks from threads holding a stale one, so a superseded stream can't
   637	    # interleave with the retry's. Threads that never claimed are never fenced.
   638	    "_stream_writer_lock": threading.Lock,
   639	    "_stream_writer_token": 0,
   640	    "_stream_writer_tls": threading.local,
   641	    "_stream_writer_dropped": 0,
   642	    # Set once a strict endpoint 400/422s on ``stream_options``; later streams omit it (#9705).
   643	    "_stream_options_unsupported": False,
   644	    # API-facing user message override when it differs from the persisted transcript (voice).
   645	    "_persist_user_message_idx": None,
   646	    "_persist_user_message_override": None,
   647	    "_persist_user_message_timestamp": None,
   648	    # Image-to-text fallbacks cached per payload/URL so one tool loop doesn't re-run vision.
   649	    "_anthropic_image_fallback_cache": dict,
   650	}
   651	
   652	
   653	def _init_prompt_cache_config(agent):
   654	    # Anthropic prompt caching (~75% input savings): auto-enabled for Claude on native
   655	    # Anthropic, OpenRouter and anthropic_messages gateways. See _anthropic_prompt_cache_policy.
   656	    agent._use_prompt_caching, agent._use_native_cache_layout = (
   657	        agent._anthropic_prompt_cache_policy()
   658	    )
   659	    agent._cache_disabled = False
   660	    # cache_ttl: "5m" (default), "1h" (2x write cost; pays off with >5-minute pauses) or "auto"
   661	    # (1h when a person paces the session, 5m when a machine does); unknown values keep "5m". A falsy/off value disables caching entirely (OAuth plans
   662	    # billing cache writes, proxies adding their own cache_control); the disable survives
   663	    # /model switches and fallback re-derivation.
   664	    # Anthropic supports "5m" (default) and "1h" cache TTL tiers. Read from config.yaml under
   665	    # prompt_caching.cache_ttl; unknown values keep "5m". 1h tier costs 2x on write vs 1.25x for 5m, but
   666	    # amortizes across long sessions with >5-minute pauses between turns (#14971). This is useful for OAuth
   667	    # subscription users where cache writes bill against "extra usage" or for third-party proxies that
   668	    # inject their own cache_control markers (#13477).
   669	    agent._cache_ttl = "5m"
   670	    with suppress(Exception):
   671	        from hermes_cli.config import load_config_readonly as _load_pc_cfg
   672	        from agent.agent_runtime_helpers import cache_ttl_means_disabled
   673	        from agent.prompt_caching import AUTO_CACHE_TTL, auto_cache_ttl_for_source
   674	        _pc_cfg = _load_pc_cfg().get("prompt_caching", {}) or {}
   675	        _ttl = _pc_cfg.get("cache_ttl", "5m")
   676	        if _ttl in {"5m", "1h"}:
   677	            agent._cache_ttl = _ttl
   678	        elif _ttl == AUTO_CACHE_TTL:
   679	            # Decided once per session from its source (a delegated child is clamped to 5m again
   680	            # in delegate_tool regardless).
   681	            from run_agent import _session_source_for_agent  # late: run_agent imports this module
   682	            agent._cache_ttl = auto_cache_ttl_for_source(_session_source_for_agent(getattr(agent, "platform", None)))
   683	        elif cache_ttl_means_disabled(_ttl):
   684	            agent._use_prompt_caching = False
   685	            agent._use_native_cache_layout = False
   686	            agent._cache_ttl = None
   687	            agent._cache_disabled = True
   688	
   689	
   690	def _init_turn_state(agent, run_budget_seconds):
   691	    _set_defaults(agent, _TURN_STATE)
   692	    # Wall-clock run budget per turn: constructor arg wins, else agent.run_budget_seconds
   693	    # (in _apply_agent_section). None = fully off (no clock reads, injection, or capping).
   694	    agent.run_budget_seconds = _normalize_run_budget_seconds(run_budget_seconds)
   695	    from agent.credits_tracker import new_credits_latch
   696	    agent._credits_latch = new_credits_latch()  # threshold-notice latch (sticky keys + gates)
   697	
   698	
   699	def _setup_logging(agent):
   700	    # agent.log (INFO+) + errors.log (WARNING+); idempotent so per-message gateway agents
   701	    # don't duplicate handlers.
   702	    from hermes_logging import setup_logging, setup_verbose_logging
   703	    setup_logging(hermes_home=_ra()._hermes_home)
   704	
   705	    if agent.verbose_logging:
   706	        setup_verbose_logging()
   707	        _ra().logger.info("Verbose logging enabled (third-party library logs suppressed)")
   708	    # Quiet mode must NOT raise per-logger levels: isEnabledFor() runs before propagation and
   709	    # would starve the root file handlers. Noise reduction belongs in hermes_logging.
   710	
   711	
   712	def _print_key_banner(key, label: str, warn_missing: bool = False) -> None:
   713	    """Masked credential line. ``key`` may be a callable Entra ID bearer provider (Azure
   714	    Foundry) — never invoke or inspect it. Keys ≤ 12 chars (incl. "dummy-key") are not shown."""
   715	    from agent.azure_identity_adapter import is_token_provider
   716	    if is_token_provider(key):
   717	        print("🔑 Using credentials: Microsoft Entra ID")
   718	    elif isinstance(key, str) and len(key) > 12:
   719	        print(f"🔑 Using {label}: {key[:8]}...{key[-4:]}")
   720	    elif warn_missing:
   721	        print("⚠️  Warning: API key appears invalid or missing")
   722	
   723	
   724	def _init_anthropic_client(agent, api_key, base_url, _provider_timeout):
   725	    """anthropic_messages: native Anthropic SDK (or AnthropicBedrock for Bedrock+Claude)."""
   726	    from agent.anthropic_adapter import build_anthropic_client
   727	    from agent.anthropic_credentials import resolve_anthropic_token
   728	    agent.client = None
   729	    agent._client_kwargs = {}
   730	    agent._anthropic_base_url = base_url
   731	    if agent.provider == "bedrock":
   732	        # AnthropicBedrock SDK for full feature parity (prompt caching, thinking budgets).
   733	        from agent.bedrock_adapter import bind_bedrock_runtime
   734	        bind_bedrock_runtime(agent, base_url, "anthropic_messages")
   735	        if not agent.quiet_mode:
   736	            print(f"🤖 AI Agent initialized with model: {agent.model} (AWS Bedrock + AnthropicBedrock SDK, {agent._bedrock_region})")
   737	        return
   738	    # ANTHROPIC_TOKEN fallback only for native Anthropic — other anthropic_messages providers
   739	    # must use their own key or Anthropic credentials leak to third-party endpoints.
   740	    # Falling back would send Anthropic credentials to third-party endpoints (Fixes #1739, #minimax-401).
   741	    _is_native_anthropic = agent.provider == "anthropic"
   742	    effective_key = api_key or (resolve_anthropic_token(model=getattr(agent, "model", None)) if _is_native_anthropic else None) or ""
   743	
   744	    # MiniMax OAuth tokens live ~15 min and the SDK freezes api_key at construction, so use a
   745	    # callable provider: build_anthropic_client mints a fresh bearer per request (re-reading
   746	    # auth.json, so other processes' refreshes are seen).
   747	    if agent.provider == "minimax-oauth" and isinstance(effective_key, str) and effective_key:
   748	        try:
   749	            from hermes_cli.auth import build_minimax_oauth_token_provider
   750	            effective_key = build_minimax_oauth_token_provider()
   751	        except Exception as _mm_exc:  # noqa: BLE001 — never block startup on this
   752	            logging.getLogger(__name__).warning(
   753	                "MiniMax OAuth: failed to install per-request token provider "
   754	                "(%s); falling back to static bearer that will expire ~15min in.",
   755	                _mm_exc,
   756	            )
   757	
   758	    agent.api_key = effective_key
   759	    agent._anthropic_api_key = effective_key
   760	    # OAuth only for native Anthropic routes (the anthropic provider, or a custom provider whose host
   761	    # is exactly api.anthropic.com, incl. a key_cmd callable token — #114967). Third-party
   762	    # providers (MiniMax, Kimi, GLM, LiteLLM proxies) that accept the Anthropic protocol must never
   763	    # trip OAuth code paths — doing so injects Claude-Code identity headers and system prompts that
   764	    # cause 401/403 on their endpoints. See #1739.
   765	    from agent.anthropic_credentials import anthropic_route_is_oauth
   766	    agent._is_anthropic_oauth = anthropic_route_is_oauth(base_url, effective_key, provider=agent.provider)
   767	    agent._anthropic_client = build_anthropic_client(effective_key, base_url, timeout=_provider_timeout)
   768	    if not agent.quiet_mode:
   769	        print(f"🤖 AI Agent initialized with model: {agent.model} (Anthropic native)")
   770	        _print_key_banner(effective_key, "token")
   771	
   772	
   773	def _init_moa_client(agent, api_key):
   774	    """provider == "moa": virtual Mixture-of-Agents facade, no real HTTP client."""
   775	    from agent.moa_loop import bind_moa_runtime
   776	    # build_moa_facade relays "moa.*" events through tool_progress_callback so every surface
   777	    # shows each reference's answer before the aggregator acts. Display-only; shared with
   778	    # fallback-restore so a restored facade keeps emitting.
   779	    # build_moa_facade wires the reference relay that routes reference-model outputs to the agent's
   780	    # tool_progress_callback so every surface that already consumes it (CLI spinner/scrollback, TUI,
   781	    # desktop, gateway) can show each reference's answer as a labelled block before the aggregator acts. The
   782	    # facade emits "moa.reference", "moa.progress", "moa.phase", and "moa.aggregating" events, forwarded
   783	    # through the same callback the tool lifecycle uses. Best-effort and cache-safe — display-only events,
   784	    # they never touch the message history. See #53802.
   785	    bind_moa_runtime(agent, agent.model, api_key)
   786	    if not agent.quiet_mode:
   787	        print(f"🤖 AI Agent initialized with MoA preset: {agent.model}")
   788	
   789	
   790	def _init_bedrock_client(agent, base_url):
   791	    """bedrock_converse: boto3 directly, no OpenAI client."""
   792	    from agent.bedrock_adapter import bind_bedrock_runtime
   793	    bind_bedrock_runtime(agent, base_url, "bedrock_converse")
   794	    if not agent.quiet_mode:
   795	        _gr_label = " + Guardrails" if agent._bedrock_guardrail_config else ""
   796	        print(f"🤖 AI Agent initialized with model: {agent.model} (AWS Bedrock, {agent._bedrock_region}{_gr_label})")
   797	
   798	
   799	def _explicit_client_kwargs(agent, api_key, base_url, _provider_timeout) -> Dict[str, Any]:
   800	    """OpenAI-client kwargs from explicit CLI/gateway credentials (auth already resolved)."""
   801	    _parsed_url = urlparse(base_url)
   802	    client_kwargs = {"api_key": api_key, "base_url": base_url}
   803	    if _parsed_url.query:
   804	        client_kwargs["base_url"] = urlunparse(_parsed_url._replace(query=""))
   805	        client_kwargs["default_query"] = {k: v[0] for k, v in parse_qs(_parsed_url.query).items()}
   806	    if _provider_timeout is not None:
   807	        client_kwargs["timeout"] = _provider_timeout
   808	    # ACP/subprocess providers take launch kwargs instead of HTTP credentials. Keyed on the
   809	    # provider profile's auth_type, not one vendor slug, so out-of-tree external_process
   810	    # plugin providers get the same launch path as the built-in copilot-acp (#102421).
   811	    from hermes_cli.runtime_provider_backends import _is_external_process_provider
   812	
   813	    if _is_external_process_provider(agent.provider):
   814	        client_kwargs["command"] = agent.acp_command
   815	        client_kwargs["args"] = agent.acp_args
   816	    _headers_for = _host_default_headers_factory(base_url)
   817	    if _headers_for is not None:
   818	        client_kwargs["default_headers"] = _headers_for(api_key, base_url)
   819	    elif "default_headers" not in client_kwargs:
   820	        # Fall back to profile.default_headers for providers that declare custom headers
   821	        # (Vercel AI Gateway attribution, Kimi User-Agent on non-kimi.com endpoints).
   822	        with suppress(Exception):
   823	            from providers import get_provider_profile as _gpf
   824	            _ph = _gpf(agent.provider)
   825	            if _ph and _ph.default_headers:
   826	                client_kwargs["default_headers"] = dict(_ph.default_headers)
   827	    return client_kwargs
   828	
   829	
   830	def _routed_client_kwargs(agent, fallback_model, _provider_timeout) -> Optional[Dict[str, Any]]:
   831	    """OpenAI-client kwargs via the centralized provider router (no explicit creds).
   832	
   833	    Falls through to the init-time fallback chain, then raises with the missing-key /
   834	    no-provider diagnostic. ``None`` when the chain landed on a MoA preset: the facade is
   835	    already bound and there is no OpenAI client to construct.
   836	    """
   837	    from agent.auxiliary_client import resolve_provider_client
   838	    _routed_client, _ = resolve_provider_client(
   839	        agent.provider or "auto", model=agent.model, raw_codex=True)
   840	    if _routed_client is not None:
   841	        from hermes_cli.providers import is_actual_route, normalize_provider
   842	        effective_provider = getattr(_routed_client, "_hermes_aux_effective_provider", "")
   843	        if is_actual_route(effective_provider):
   844	            agent.provider = normalize_provider(effective_provider)
   845	        return _client_kwargs_from_routed(_routed_client, _provider_timeout)
   846	    # No credentials: try the fallback chain BEFORE failing (an exhausted single-entry pool
   847	    # must not die with a misleading "No LLM provider configured"); only explicitly named
   848	    # providers keep the missing-key diagnostic.
   849	    # An exhausted single-entry pool (typically ``openrouter`` under free-tier daily quotas) must still
   850	    # reach the chain instead of dying at init with a misleading "No LLM provider configured" error. See
   851	    # #17929.
   852	    _explicit = (agent.provider or "").strip().lower()
   853	    _refused_entries = []
   854	    for _fb in _fallback_entries(fallback_model):
   855	        _fb_provider = str(_fb["provider"])
   856	        try:
   857	            from hermes_cli.fallback_config import resolve_entry_api_key
   858	            _fb_explicit_key = resolve_entry_api_key(_fb)
   859	            _fb_client, _fb_model = resolve_provider_client(
   860	                _fb["provider"], model=_fb["model"], raw_codex=True,
   861	                explicit_base_url=_fb.get("base_url"), explicit_api_key=_fb_explicit_key,
   862	            )
   863	        except Exception as _fb_exc:
   864	            logger.debug("Init-time fallback entry %s failed: %s", _fb_provider, _fb_exc)
   865	            # A bare exception (``KeyError()``) stringifies empty; name its type instead.
   866	            _refused_entries.append((_fb_provider, str(_fb_exc) or type(_fb_exc).__name__))
   867	            continue
   868	        if _fb_client is None:
   869	            # The router returns None when no credentials are usable for the entry — a skip
   870	            # that leaves no trace otherwise, hiding key-less fallback entries from the log.
   871	            logger.debug(
   872	                "Init-time fallback entry %s resolved no usable credentials", _fb_provider
   873	            )
   874	            _refused_entries.append((_fb_provider, "no usable credentials"))
   875	            continue
   876	        agent._fallback_activated = True
   877	        if _fb_provider.strip().lower() == "moa":
   878	            # The chokepoint handed back the preset's aggregator client, which only proves the
   879	            # preset resolves and its aggregator has credentials. A MoA entry means the preset
   880	            # itself (same as ``provider: moa`` in config), so bind the facade, not the aggregator.
   881	            from agent.moa_loop import bind_moa_runtime
   882	            bind_moa_runtime(agent, _fb["model"])
   883	            return None
   884	        agent.provider = _fb["provider"]
   885	        agent.model = _fb_model or _fb["model"]
   886	        return _client_kwargs_from_routed(_fb_client, _provider_timeout)
   887	    # A burned credential pool (#119533) is otherwise indistinguishable from missing config,
   888	    # so name it even when no fallback entries are configured.
   889	    _pool_exhausted = False
   890	    _pool = None
   891	    if _explicit and _explicit != "auto":
   892	        with suppress(Exception):
   893	            from agent.credential_pool import load_pool
   894	            _pool = load_pool(_explicit)
   895	            _pool_exhausted = _pool.has_credentials() and not _pool.has_available(model=agent.model)
   896	    if _refused_entries or _pool_exhausted:
   897	        # Neutral wording: the explicit-provider branch below raises the provider-specific
   898	        # missing-credentials message, not the generic "No LLM provider configured" one.
   899	        logger.warning(
   900	            "Init-time provider resolution failed: primary %r unresolvable (%s); fallback entries refused: %s",
   901	            agent.provider,
   902	            "credential pool exhausted" if _pool_exhausted else "no usable credentials",
   903	            "; ".join(f"{_p} ({_r})" for _p, _r in _refused_entries) or "none configured",
   904	        )
   905	    # A fully-exhausted pool is a billing/quota failure, NOT a config problem: name it for EVERY
   906	    # explicit provider. ``openrouter`` / ``custom`` have no provider-specific missing-credentials
   907	    # branch, so a burned override pool there fell through to the generic "No LLM provider
   908	    # configured" setup message even though the config default was fine (#94785). Prefer a billing
   909	    # verdict (402 / classifier "billing") and fall back to the existing cooldown wording (which
   910	    # names the 429 reset time, #56810); raise before the missing-credentials branch so a genuine
   911	    # 402 is never described as a missing key or a transient rate limit.
   912	    if _pool_exhausted:
   913	        from agent.auxiliary_unavailable import (
   914	            ProviderCredentialsExhaustedError,
   915	            pool_billing_message,
   916	            pool_cooldown_message,
   917	        )
   918	        _exhausted_message = (
   919	            pool_billing_message(_explicit, model=agent.model, pool=_pool)
   920	            or pool_cooldown_message(_explicit)
   921	        )
   922	        if _exhausted_message:
   923	            raise ProviderCredentialsExhaustedError(_exhausted_message, provider=_explicit)
   924	    if _explicit and _explicit not in {"auto", "openrouter", "custom"}:
   925	        # Explicit non-OpenRouter provider with no creds and no usable fallback: fail fast.
   926	        from agent.auxiliary_unavailable import missing_provider_credentials_message
   927	        raise RuntimeError(missing_provider_credentials_message(_explicit))
   928	    from hermes_constants import profile_cli_selector
   929	    _sel = profile_cli_selector()
   930	    raise RuntimeError(
   931	        "No LLM provider configured. Run `hermes model` to "
   932	        "select a provider, or run `hermes setup` for first-time "
   933	        "configuration."
   934	    )
   935	
   936	
   937	def _apply_openai_header_policy(agent, client_kwargs: Dict[str, Any]) -> None:
   938	    """Mutate ``client_kwargs`` (== ``agent._client_kwargs``) with header/TLS policy, in order:
   939	    OpenRouter Claude beta header → model.default_headers → custom-provider TLS/extra_headers."""
   940	    # Fine-grained tool streaming for Claude on OpenRouter: without the beta header
   941	    # Anthropic buffers the whole tool call and OpenRouter's proxy times out.
   942	    from agent.anthropic_adapter import _TOOL_STREAMING_BETA
   943	
   944	    _effective_base = str(client_kwargs.get("base_url", "")).lower()
   945	    if base_url_host_matches(_effective_base, "openrouter.ai") and "claude" in (agent.model or "").lower():
   946	        headers = client_kwargs.get("default_headers") or {}
   947	        existing_beta = headers.get("x-anthropic-beta", "")
   948	        if _TOOL_STREAMING_BETA not in existing_beta:
   949	            headers["x-anthropic-beta"] = ",".join(filter(None, (existing_beta, _TOOL_STREAMING_BETA)))
   950	            client_kwargs["default_headers"] = headers
   951	    # model.default_headers override provider/SDK defaults (WAFs rejecting SDK headers).
   952	    agent._apply_user_default_headers()
   953	    try:
   954	        from hermes_cli.config import (
   955	            apply_custom_provider_extra_headers_to_client_kwargs,
   956	            apply_custom_provider_tls_to_client_kwargs, get_compatible_custom_providers,
   957	            load_config,
   958	        )
   959	        _cp_entries = get_compatible_custom_providers(load_config())
   960	        _cp_base_url = str(client_kwargs.get("base_url") or agent.base_url or "")
   961	        apply_custom_provider_tls_to_client_kwargs(client_kwargs, _cp_base_url, _cp_entries)
   962	        # Per-provider extra_headers applied last so the most specific config level wins.
   963	        # SECURITY: values may carry credentials — never log them.
   964	        apply_custom_provider_extra_headers_to_client_kwargs(client_kwargs, _cp_base_url, _cp_entries)
   965	    except Exception:
   966	        logger.debug("custom-provider TLS resolution skipped", exc_info=True)
   967	
   968	
   969	def _init_openai_client(agent, api_key, base_url, fallback_model, _provider_timeout):
   970	    """OpenAI-wire client: resolve kwargs, apply header/TLS policy, construct."""
   971	    if api_key and base_url:
   972	        client_kwargs = _explicit_client_kwargs(agent, api_key, base_url, _provider_timeout)
   973	    else:
   974	        client_kwargs = _routed_client_kwargs(agent, fallback_model, _provider_timeout)
   975	        if client_kwargs is None:  # init-time fallback bound the MoA facade
   976	            if not agent.quiet_mode:
   977	                print(f"🤖 AI Agent initialized with MoA preset: {agent.model}")
   978	            return
   979	    from hermes_cli.providers import is_actual_route
   980	    if is_actual_route(agent.provider, client_kwargs.get("base_url", "")):
   981	        agent.api_mode = "chat_completions"
   982	        if hasattr(agent, "_transport_cache"):
   983	            agent._transport_cache.clear()
   984	    try:
   985	        from agent.bedrock_adapter import configure_bedrock_openai_client_kwargs
   986	        configure_bedrock_openai_client_kwargs(client_kwargs, timeout=_provider_timeout)
   987	    except Exception:
   988	        if agent.provider == "bedrock" and "bedrock-mantle." in str(client_kwargs.get("base_url", "")):
   989	            raise
   990	
   991	    agent._client_kwargs = client_kwargs  # stored for rebuilding after interrupt
   992	    _apply_openai_header_policy(agent, client_kwargs)
   993	    agent.api_key = client_kwargs.get("api_key", "")
   994	    agent.base_url = client_kwargs.get("base_url", agent.base_url)
   995	    try:
   996	        agent.client = agent._create_openai_client(client_kwargs, reason="agent_init", shared=True)
   997	        if not agent.quiet_mode:
   998	            print(f"🤖 AI Agent initialized with model: {agent.model}")
   999	            if base_url:
  1000	                print(f"🔗 Using custom base URL: {base_url}")
  1001	            from gateway.warning_notifications import warning_notifications_enabled
  1002	            _print_key_banner(client_kwargs.get("api_key", "none"), "API key",
  1003	                              warn_missing=warning_notifications_enabled(agent.platform))
  1004	    except Exception as e:
  1005	        raise RuntimeError(f"Failed to initialize OpenAI client: {e}")
  1006	
  1007	
  1008	def _build_client(agent, api_key, base_url, fallback_model):
  1009	    # LLM client per wire mode (raw_codex=True: the main agent needs direct
  1010	    # responses.stream()). One provider/model timeout up front so every path applies it.
  1011	    agent._anthropic_client = None
  1012	    agent._is_anthropic_oauth = False
  1013	    _provider_timeout = get_provider_request_timeout(agent.provider, agent.model)
  1014	    if agent.api_mode == "anthropic_messages":
  1015	        _init_anthropic_client(agent, api_key, base_url, _provider_timeout)
  1016	    elif agent.provider == "moa":
  1017	        _init_moa_client(agent, api_key)
  1018	    elif agent.api_mode == "bedrock_converse":
  1019	        _init_bedrock_client(agent, base_url)
  1020	    else:
  1021	        _init_openai_client(agent, api_key, base_url, fallback_model, _provider_timeout)
  1022	
  1023	
  1024	def _lazy_headers(module: str, name: str, pass_key: bool = False, pass_base: bool = False):
  1025	    """Header factory ``(api_key, base_url) -> dict`` importing ``module.name`` at call time.
  1026	    ``pass_key`` forwards ``(key, base_url=base)``; ``pass_base`` forwards ``(base)``."""
  1027	    def factory(key, base):
  1028	        import importlib
  1029	        fn = getattr(importlib.import_module(module), name)
  1030	        if pass_key:
  1031	            return fn(key, base_url=base)
  1032	        return fn(base) if pass_base else fn()
  1033	    return factory
  1034	
  1035	
  1036	# Host → default_headers factory for explicit base_url client construction. Ordered: first
  1037	# host match wins; no match falls back to the provider profile's declared headers.
  1038	_HOST_DEFAULT_HEADERS: List[tuple[str, Callable[[Any, str], Dict[str, str]]]] = [
  1039	    ("openrouter.ai", _lazy_headers("agent.auxiliary_client", "build_or_headers")),
  1040	    ("integrate.api.nvidia.com",
  1041	     _lazy_headers("agent.auxiliary_client", "build_nvidia_nim_headers", pass_base=True)),
  1042	    ("api.routermint.com", _lazy_headers("agent.client_lifecycle", "_routermint_headers")),
  1043	    ("githubcopilot.com", _lazy_headers("hermes_cli.models", "copilot_default_headers")),
  1044	    ("api.kimi.com", lambda _k, _b: {"User-Agent": "claude-code/0.1.0"}),
  1045	    ("portal.qwen.ai", _lazy_headers("agent.client_lifecycle", "_qwen_portal_headers")),
  1046	    ("chatgpt.com", _lazy_headers("agent.codex_headers", "codex_cloudflare_headers", pass_key=True)),
  1047	    ("x.ai", _lazy_headers("tools.xai_http", "hermes_xai_default_headers")),
  1048	]
  1049	
  1050	
  1051	def _host_default_headers_factory(base_url: str):
  1052	    for host, factory in _HOST_DEFAULT_HEADERS:
  1053	        if base_url_host_matches(base_url, host):
  1054	            return factory
  1055	    return None
  1056	
  1057	
  1058	def _client_kwargs_from_routed(client, timeout) -> Dict[str, Any]:
  1059	    """OpenAI-client kwargs mirroring a router-resolved client, keeping its provider headers
  1060	    (SDK stores them in ``_custom_headers``; older/mocked clients expose ``default_headers``)."""
  1061	    kwargs = {"api_key": client.api_key, "base_url": str(client.base_url)}
  1062	    if timeout is not None:
  1063	        kwargs["timeout"] = timeout
  1064	    headers = (
  1065	        getattr(client, "_custom_headers", None)
  1066	        or getattr(client, "default_headers", None)
  1067	        or getattr(client, "_default_headers", None)
  1068	    )
  1069	    if headers:
  1070	        kwargs["default_headers"] = dict(headers)
  1071	    return kwargs
  1072	
  1073	
  1074	def _fallback_entries(fallback_model) -> List[Dict[str, Any]]:
  1075	    """Normalize legacy single-dict ``fallback_model`` / list ``fallback_providers``."""
  1076	    if isinstance(fallback_model, dict):
  1077	        fallback_model = [fallback_model]
  1078	    if not isinstance(fallback_model, list):
  1079	        return []
  1080	    return [
  1081	        f for f in fallback_model if isinstance(f, dict) and f.get("provider") and f.get("model")
  1082	    ]
  1083	
  1084	
  1085	def _init_fallback_chain(agent, fallback_model):
  1086	    # Stable pool-entry identity: OAuth refreshes can replace the token before a failed
  1087	    # request is recovered, so the key value alone can't attribute the failure.
  1088	    from agent.agent_runtime_helpers import sync_credential_pool_entry_id
  1089	    sync_credential_pool_entry_id(agent)
  1090	
  1091	    # Ordered backups tried when the primary is exhausted (legacy single-dict or list).
  1092	    agent._fallback_chain = _fallback_entries(fallback_model)
  1093	    agent._fallback_index = 0
  1094	    agent._fallback_activated = getattr(agent, "_fallback_activated", False)
  1095	    # Legacy attribute kept for backward compat (tests, external callers)
  1096	    agent._fallback_model = agent._fallback_chain[0] if agent._fallback_chain else None
  1097	    chain = agent._fallback_chain
  1098	    if chain and not agent.quiet_mode:
  1099	        labels = [f"{f['model']} ({f['provider']})" for f in chain]
  1100	        if len(chain) == 1:
  1101	            print(f"🔄 Fallback model: {labels[0]}")
  1102	        else:
  1103	            print(f"🔄 Fallback chain ({len(chain)} providers): " + " → ".join(labels))
  1104	
  1105	
  1106	def _load_tools(agent, enabled_toolsets, disabled_toolsets):
  1107	    # A multiplexed gateway may have switched HERMES_HOME since model_tools was imported;
  1108	    # make sure this profile's plugins are discovered before the tool snapshot.
  1109	    try:
  1110	        from hermes_cli.plugins import discover_plugins
  1111	        discover_plugins()
  1112	    except Exception:
  1113	        logger.warning("Plugin discovery failed during agent setup", exc_info=True)
  1114	
  1115	    # Capture the registry generation FIRST so a concurrent refresh can detect staleness.
  1116	    try:
  1117	        from tools.registry import registry as _snapshot_registry
  1118	        agent._tool_snapshot_generation = _snapshot_registry._generation
  1119	    except Exception:
  1120	        agent._tool_snapshot_generation = 0
  1121	    import model_tools
  1122	    agent.tools = model_tools.get_tool_definitions(
  1123	        enabled_toolsets=enabled_toolsets, disabled_toolsets=disabled_toolsets,
  1124	        quiet_mode=agent.quiet_mode,
  1125	    )
  1126	    # A finite -q run has no later session to learn for: no skill authoring tool (agent/oneshot_footprint.py).
  1127	    from agent.oneshot_footprint import prune_oneshot_tools
  1128	    agent.tools = prune_oneshot_tools(agent.tools or [])
  1129	    from tools.connectors.turn import side_agent_tool_drops
  1130	    drops = side_agent_tool_drops(agent)
  1131	    if drops:
  1132	        agent.tools = [t for t in agent.tools if t["function"]["name"] not in drops]
  1133	
  1134	    agent.valid_tool_names = {tool["function"]["name"] for tool in agent.tools} if agent.tools else set()
  1135	    # Kanban guidance is session-static for the dispatcher-owned worker only. Profiles may
  1136	    # expose kanban_show interactively, and children/cron runs inherit the env var, without
  1137	    # owning a task.
  1138	    from agent.delegation_context import owned_kanban_task
  1139	    from agent.prompt_builder import KANBAN_GUIDANCE
  1140	    agent._kanban_worker_guidance = (
  1141	        KANBAN_GUIDANCE if owned_kanban_task() and "kanban_show" in agent.valid_tool_names else ""
  1142	    )
  1143	    if agent.quiet_mode:
  1144	        return
  1145	    if agent.tools:
  1146	        print(f"🛠️  Loaded {len(agent.tools)} tools: {', '.join(sorted(agent.valid_tool_names))}")
  1147	        if enabled_toolsets:
  1148	            print(f"   ✅ Enabled toolsets: {', '.join(enabled_toolsets)}")
  1149	        if disabled_toolsets:
  1150	            print(f"   ❌ Disabled toolsets: {', '.join(disabled_toolsets)}")
  1151	        import model_tools
  1152	        requirements = model_tools.check_toolset_requirements()
  1153	        missing_reqs = [name for name, available in requirements.items() if not available]
  1154	        if missing_reqs:
  1155	            agent._safe_print(f"⚠️  Some tools may not work due to missing requirements: {missing_reqs}", diagnostic=True)
  1156	    else:
  1157	        print("🛠️  No tools loaded (all tools filtered out or unavailable)")
  1158	    if agent.save_trajectories:
  1159	        print("📝 Trajectory saving enabled")
  1160	    if agent.ephemeral_system_prompt:
  1161	        prompt_preview = agent.ephemeral_system_prompt[:60] + "..." if len(agent.ephemeral_system_prompt) > 60 else agent.ephemeral_system_prompt
  1162	        print(f"🔒 Ephemeral system prompt: '{prompt_preview}' (not saved to trajectories)")
  1163	    if agent._use_prompt_caching:
  1164	        if agent._use_native_cache_layout and agent.provider == "anthropic":
  1165	            source = "native Anthropic"
  1166	        elif agent._use_native_cache_layout:
  1167	            source = "Anthropic-compatible endpoint"
  1168	        else:
  1169	            source = "Claude via OpenRouter"
  1170	        print(f"💾 Prompt caching: ENABLED ({source}, {agent._cache_ttl} TTL)")
  1171	
  1172	
  1173	def _publish_session_id(session_id: str) -> None:
  1174	    """Expose the session ID to tools via ContextVar (+ legacy os.environ fallback).
  1175	
  1176	    If the ContextVar bridge fails to import, keep the root-agent env fallback but never let
  1177	    delegated construction publish a child ID process-wide.
  1178	    """
  1179	    try:
  1180	        from gateway.session_context import set_current_session_id
  1181	        set_current_session_id(session_id)
  1182	    except Exception:
  1183	        try:
  1184	            from agent.delegation_context import is_delegated_child_context
  1185	            delegated_child = is_delegated_child_context()
  1186	        except Exception:
  1187	            delegated_child = False
  1188	        if not delegated_child:
  1189	            os.environ["HERMES_SESSION_ID"] = session_id
  1190	
  1191	
  1192	def _init_session_state(agent, session_id, session_db, parent_session_id, reasoning_config, max_tokens,
  1193	    checkpoints_enabled, checkpoint_max_snapshots, checkpoint_max_total_size_mb, checkpoint_max_file_size_mb):
  1194	    agent.session_start = datetime.now()
  1195	    agent.session_id = session_id or new_session_id(agent.session_start)
  1196	    _publish_session_id(agent.session_id)
  1197	
  1198	    # ~/.hermes/sessions/ — kept unconditionally for request_dump_*.json debug breadcrumbs.
  1199	    agent.logs_dir = get_hermes_home() / "sessions"
  1200	    agent.logs_dir.mkdir(parents=True, exist_ok=True)
  1201	    _set_defaults(agent, _SESSION_STATE)
  1202	
  1203	    # Filesystem checkpoint manager (transparent — not a tool)
  1204	    from tools.checkpoint_manager import CheckpointManager
  1205	    agent._checkpoint_mgr = CheckpointManager(
  1206	        enabled=checkpoints_enabled, max_snapshots=checkpoint_max_snapshots,
  1207	        max_total_size_mb=checkpoint_max_total_size_mb,
  1208	        max_file_size_mb=checkpoint_max_file_size_mb,
  1209	    )
  1210	
  1211	    agent._session_db = session_db  # optional SQLite store (CLI/gateway-provided)
  1212	    agent._parent_session_id = parent_session_id
  1213	    agent._session_init_model_config = {
  1214	        "max_iterations": agent.max_iterations,
  1215	        "reasoning_config": reasoning_config,
  1216	        "max_tokens": max_tokens,
  1217	    }
  1218	    # Process-scoped --yolo is persisted so `hermes --resume` restores the bypass
  1219	    # (SessionDB.session_yolo_enabled); session-scoped /yolo toggles persist separately.
  1220	    with suppress(Exception):
  1221	        from tools.approval import _YOLO_MODE_FROZEN
  1222	        if _YOLO_MODE_FROZEN:
  1223	            agent._session_init_model_config["yolo_mode"] = True
  1224	
  1225	    # In-memory todo list for task planning (one per agent/session)
  1226	    from tools.todo_tool import TodoStore
  1227	    agent._todo_store = TodoStore()
  1228	
  1229	
  1230	def _apply_display_config(agent, _agent_cfg, platform):
  1231	    # show_commentary: Codex phase=commentary → interim path (true) or reasoning channel.
  1232	    agent.show_commentary = bool(_cfg_dict(_agent_cfg, "display").get("show_commentary", True))
  1233	
  1234	    # Window (seconds) for the bounded /fast auto|cold modes (agent.fast_mode).
  1235	    agent.fast_auto_seconds = (_agent_cfg.get("agent") or {}).get("fast_auto_seconds", 60)
  1236	
  1237	    # lmstudio_load_mode: "explicit" (preload via management API) or "jit" (Auto-Evict path).
  1238	    _model_section = _cfg_dict(_agent_cfg, "model")
  1239	    _load_mode = str(_model_section.get("lmstudio_load_mode", "explicit") or "explicit").strip().lower()
  1240	    agent.lmstudio_load_mode = _load_mode if _load_mode in {"explicit", "jit"} else "explicit"
  1241	    if agent.lmstudio_load_mode != _load_mode:
  1242	        logger.warning(
  1243	            "Invalid model.lmstudio_load_mode=%r; expected 'explicit' or 'jit'. Using explicit.",
  1244	            _model_section.get("lmstudio_load_mode"),
  1245	        )
  1246	
  1247	    # model.streaming=false seeds _disable_streaming (the loop's runtime fallback) for
  1248	    # backends with broken streaming tool calls. Session-scoped; orthogonal to display.streaming.
  1249	    _streaming = str(_model_section.get("streaming", "true")).strip().lower()
  1250	    agent._disable_streaming = _streaming in {"false", "0", "no", "off"}
  1251	    if not agent._disable_streaming and _streaming not in {"true", "1", "yes", "on"}:
  1252	        logger.warning(
  1253	            "Invalid model.streaming=%r; expected a boolean. Using streaming (default).",
  1254	            _model_section.get("streaming"),
  1255	        )
  1256	    agent._stream_5xx_probe_ts = None  # monotonic time of the last streaming-5xx unmask probe
  1257	
  1258	    try:
  1259	        agent._tool_guardrails = ToolCallGuardrailController(
  1260	            ToolCallGuardrailConfig.from_mapping(
  1261	                _agent_cfg.get("tool_loop_guardrails", {}), platform=platform,
  1262	            )
  1263	        )
  1264	    except Exception as _tlg_err:
  1265	        _ra().logger.warning("Tool loop guardrail config ignored: %s", _tlg_err)
  1266	
  1267	
  1268	def _memory_provider_init_kwargs(agent, platform) -> Dict[str, Any]:
  1269	    """Scoping kwargs for ``MemoryManager.initialize_all`` (status_callback is CLI-only:
  1270	    gateway status travels a different path and the indicator no-ops without it)."""
  1271	    kwargs = {
  1272	        "session_id": agent.session_id,
  1273	        "platform": platform or "cli",
  1274	        "hermes_home": str(get_hermes_home()),
  1275	        # platform="cron" (scheduler) / "subagent" (delegate_task) → providers skip writes (MemoryProvider.initialize).
  1276	        "agent_context": platform if platform in ("cron", "subagent") else "primary",
  1277	    }
  1278	    if kwargs["platform"] == "cli":
  1279	        kwargs["warning_callback"] = agent._emit_warning
  1280	        kwargs["status_callback"] = agent._emit_status
  1281	    # Session title (e.g. honcho derives chat-scoped session keys from it).
  1282	    if agent._session_db:
  1283	        with suppress(Exception):
  1284	            _st = agent._session_db.get_session_title(agent.session_id)
  1285	            if _st:
  1286	                kwargs["session_title"] = _st
  1287	                _source = agent._session_db.get_session_title_source(agent.session_id)
  1288	                if _source:
  1289	                    kwargs["session_title_source"] = _source
  1290	    # Gateway user/chat identity for per-user scoping (gateway_session_key: stable per-chat
  1291	    # Honcho session isolation).
  1292	    for _ident in _GATEWAY_IDENTITY_PARAMS:
  1293	        _val = getattr(agent, f"_{_ident}")
  1294	        if _val:
  1295	            kwargs[_ident] = _val
  1296	    if agent.session_cwd:
  1297	        kwargs["cwd"] = agent.session_cwd
  1298	    # Profile identity for per-profile provider scoping
  1299	    with suppress(Exception):
  1300	        from hermes_cli.profiles import get_active_profile_name
  1301	        kwargs["agent_identity"] = get_active_profile_name()
  1302	        kwargs["agent_workspace"] = "hermes"
  1303	    return kwargs
  1304	
  1305	
  1306	def _init_memory(agent, _agent_cfg, skip_memory, platform, memory_manager=None):
  1307	    # Persistent memory (MEMORY.md + USER.md) — loaded from disk
  1308	    agent._memory_store = None
  1309	    agent._memory_enabled = False
  1310	    agent._user_profile_enabled = False
  1311	    agent._memory_nudge_interval = 10
  1312	    agent._turns_since_memory = 0
  1313	    agent._iters_since_skill = 0
  1314	    # skip_memory skips the external *provider*; enabled_toolsets=["memory"] still gets the
  1315	    # built-in store so the memory tool never sees store=None.
  1316	    # Flush/background agents can still pass enabled_toolsets=["memory"] so the built-in file store exists
  1317	    # and the memory tool does not fail with store=None (#65429). A toolset on disabled_toolsets is not a
  1318	    # request: a caller that denylists memory while its default toolset still names it must not get
  1319	    # MEMORY.md loaded by an enabled-only check. (Cron agents now run with skip_memory=False and take the
  1320	    # normal path here.)
  1321	    _memory_toolset_requested = (
  1322	        "memory" in (agent.enabled_toolsets or [])
  1323	        and "memory" not in (agent.disabled_toolsets or [])
  1324	    )
  1325	    if not skip_memory or _memory_toolset_requested:
  1326	        # Memory is optional — don't break agent init
  1327	        with suppress(Exception):
  1328	            from tools.memory_tool import (
  1329	                MemoryStore, get_builtin_memory_config, get_builtin_memory_store_flags,
  1330	            )
  1331	            mem_config = get_builtin_memory_config(_agent_cfg)
  1332	            agent._memory_enabled, agent._user_profile_enabled = get_builtin_memory_store_flags(
  1333	                _agent_cfg
  1334	            )
  1335	            agent._memory_nudge_interval = int(mem_config.get("nudge_interval", 10))
  1336	            if agent._memory_enabled or agent._user_profile_enabled:
  1337	                agent._memory_store = MemoryStore(
  1338	                    memory_char_limit=mem_config.get("memory_char_limit", 2200),
  1339	                    user_char_limit=mem_config.get("user_char_limit", 1375),
  1340	                    memory_enabled=agent._memory_enabled,
  1341	                    user_profile_enabled=agent._user_profile_enabled,
  1342	                )
  1343	                agent._memory_store.load_from_disk()
  1344	
  1345	    # External memory provider plugin (one at a time, alongside built-in): memory.provider.
  1346	    agent._memory_manager = None
  1347	    if memory_manager is not None and not skip_memory:
  1348	        # A caller that rebuilds the agent per turn (gateway api_server) hands back the session's
  1349	        # already-initialized manager: providers keep their prefetch/retain state across turns instead
  1350	        # of being re-initialized (#120116). No initialize_all — the providers are already bound.
  1351	        agent._memory_manager = memory_manager
  1352	    elif not skip_memory:
  1353	        try:
  1354	            _mem_provider_name = mem_config.get("provider", "") if mem_config else ""
  1355	            if not is_core_memory_provider(_mem_provider_name):
  1356	                from agent.memory_manager import MemoryManager as _MemoryManager
  1357	                from plugins.memory import load_memory_provider as _load_mem
  1358	                agent._memory_manager = _MemoryManager()
  1359	                _mp = _load_mem(_mem_provider_name)
  1360	                if _mp is None:
  1361	                    # The provider left core for the catalog (or was never installed): fetch it once.
  1362	                    from hermes_cli.memory_provider_migration import recover_at_startup
  1363	                    if recover_at_startup(_mem_provider_name):
  1364	                        _mp = _load_mem(_mem_provider_name)
  1365	                if _mp and _mp.is_available():
  1366	                    agent._memory_manager.add_provider(_mp)
  1367	                elif _mp is not None and _mem_provider_name not in _warned_unavailable_providers:
  1368	                    # unavailable_reason() reads config/probes importlib — skip it once warned.
  1369	                    _unavailable_reason = ""
  1370	                    with suppress(Exception):
  1371	                        _unavailable_reason = _mp.unavailable_reason()
  1372	                    _warn_memory_provider_unavailable(_mem_provider_name, _unavailable_reason)
  1373	                if agent._memory_manager.providers:
  1374	                    agent._memory_manager.initialize_all(**_memory_provider_init_kwargs(agent, platform))
  1375	                    _ra().logger.info("Memory provider '%s' activated", _mem_provider_name)
  1376	                else:
  1377	                    _ra().logger.debug("Memory provider '%s' not found or not available", _mem_provider_name)
  1378	                    agent._memory_manager = None
  1379	        except Exception as _mpe:
  1380	            _ra().logger.warning("Memory provider plugin init failed: %s", _mpe)
  1381	            agent._memory_manager = None
  1382	
  1383	    from agent.memory_manager import inject_memory_provider_tools
  1384	    inject_memory_provider_tools(agent)
  1385	
  1386	
  1387	def _apply_agent_section(agent, _agent_cfg):
  1388	    # Skills config: nudge interval for skill creation reminders
  1389	    agent._skill_nudge_interval = 10
  1390	    with suppress(Exception):
  1391	        agent._skill_nudge_interval = int(_agent_cfg.get("skills", {}).get("creation_nudge_interval", 10))
  1392	
  1393	    _agent_section = _cfg_dict(_agent_cfg, "agent")
  1394	    agent.budget_warning_ratio = normalize_budget_warning_ratio(
  1395	        _agent_section.get("budget_warning_ratio")
  1396	    )
  1397	    # Both: "auto" (model-list match), true, false, or list of model substrings; independent
  1398	    # of each other (gates in agent/system_prompt.py).
  1399	    agent._tool_use_enforcement = _agent_section.get("tool_use_enforcement", "auto")
  1400	    agent._execution_guidance = _agent_section.get("execution_guidance", "auto")
  1401	
  1402	    # Wall-clock run budget from config — only when the constructor arg was not given.
  1403	    if agent.run_budget_seconds is None:
  1404	        agent.run_budget_seconds = _normalize_run_budget_seconds(
  1405	            _agent_section.get("run_budget_seconds")
  1406	        )
  1407	
  1408	    # Empty-response guard: a malformed section falls back to schema defaults (on, $0.25).
  1409	    from agent.empty_response_guard import resolve_guard_settings
  1410	    (
  1411	        agent._empty_guard_enabled, agent._empty_guard_cost_threshold_usd
  1412	    ) = resolve_guard_settings(_agent_section.get("empty_response_guard"))
  1413	
  1414	    # "auto" (codex_responses only), true (all api_modes), false, or model substrings.
  1415	    agent._intent_ack_continuation = _agent_section.get("intent_ack_continuation", "auto")
  1416	
  1417	    # Responses `text.verbosity`: "" / unknown value = not sent (never flips the provider default).
  1418	    _verbosity = str(_agent_section.get("text_verbosity") or "").strip().lower()
  1419	    if _verbosity and _verbosity not in {"low", "medium", "high"}:
  1420	        logger.warning("Unknown agent.text_verbosity %r; expected low, medium or high — ignoring", _verbosity)
  1421	        _verbosity = ""
  1422	    agent.text_verbosity = _verbosity or None
  1423	
  1424	    # Default-on boolean gates: anti-stall guards (notice-only), universal guidance toggles
  1425	    # (ALL models, unlike enforcement), the local toolchain probe, Bot Mode protocol section.
  1426	    for _key in (
  1427	        "stall_guards", "task_completion_guidance", "parallel_tool_call_guidance",
  1428	        "environment_probe", "bot_mode_protocol",
  1429	    ):
  1430	        setattr(agent, f"_{_key}", bool(_agent_section.get(_key, True)))
  1431	    # Warm the probe (~0.5s of subprocesses) off-thread so the first prompt build finds it cached.
  1432	    if agent._environment_probe:
  1433	        with suppress(Exception):
  1434	            from tools.env_probe import warm_environment_probe_async
  1435	            warm_environment_probe_async()
  1436	
  1437	    # "Bot Chat" gate hint for hosts that defer the DB title write past the first prompt build.
  1438	    agent._session_title_hint = None
  1439	
  1440	    # platform_hints: <platform>: {append|replace}, stored verbatim (agent/system_prompt.py).
  1441	    agent._platform_hint_overrides = _cfg_dict(_agent_cfg, "platform_hints")
  1442	
  1443	    # App-level API retry count (wraps each model API call). Default 3; 1 = single attempt.
  1444	    try:
  1445	        _api_retries = max(int(_agent_section.get("api_max_retries", 3)), 1)
  1446	    except (TypeError, ValueError):
  1447	        _api_retries = 3
  1448	    agent._api_max_retries = _api_retries
  1449	    # Bounded post-exhaustion auto-recovery cycles once retries AND the fallback chain are spent
  1450	    # on a transient outage (agent/turn_recovery_autorecover.py). 0 disables the ladder.
  1451	    try:
  1452	        agent._auto_recovery_cycles = max(int(_agent_section.get("auto_recovery_cycles", 5)), 0)
  1453	    except (TypeError, ValueError):
  1454	        agent._auto_recovery_cycles = 5
  1455	
  1456	
  1457	def _positive_int(raw: Any, *, reject: tuple = ()) -> Optional[int]:
  1458	    """``int(raw)`` when positive, else None. ``reject`` lists types refused outright (bool, float)."""
  1459	    if reject and isinstance(raw, reject):
  1460	        return None
  1461	    try:
  1462	        parsed = int(raw)
  1463	    except (TypeError, ValueError):
  1464	        return None
  1465	    return parsed if parsed > 0 else None
  1466	
  1467	
  1468	def _compression_threshold(agent, cfg: Dict[str, Any]) -> tuple[float, bool]:
  1469	    """Global threshold merged with the per-model override; stashes the autoraise notice.
  1470	    Codex gpt-5.4/5.5 raise to 85% (272K cap → 50% would compact at ~136K); the opt-out flag
  1471	    restores the global value, and the notice has its own display gate."""
  1472	    threshold = float(cfg.get("threshold", 0.50))
  1473	    autoraise = _cfg_flag(cfg, "codex_gpt55_autoraise", True)
  1474	    notice_enabled = _cfg_flag(cfg, "codex_gpt55_autoraise_notice", True)
  1475	    agent._compression_threshold_autoraised = None
  1476	    with suppress(Exception):
  1477	        from agent.auxiliary_client import (
  1478	            _compression_threshold_for_model as _cthresh_fn,
  1479	            _is_codex_gpt54_or_gpt55 as _is_codex_gpt54_or_gpt55_fn,
  1480	            _is_codex_spark as _is_codex_spark_fn,
  1481	        )
  1482	        _model_cthresh = _cthresh_fn(
  1483	            agent.model, agent.provider, allow_codex_gpt55_autoraise=autoraise,
  1484	        )
  1485	        # Codex autoraises apply only when they RAISE; Arcee Trinity keeps its
  1486	        # unconditional override.
  1487	        threshold, agent._compression_threshold_autoraised = _resolve_compression_threshold(
  1488	            threshold,
  1489	            _model_cthresh,
  1490	            model=agent.model,
  1491	            is_codex_autoraise=(
  1492	                _is_codex_gpt54_or_gpt55_fn(agent.model, agent.provider)
  1493	                or _is_codex_spark_fn(agent.model, agent.provider)
  1494	            ),
  1495	        )
  1496	    return threshold, notice_enabled
  1497	
  1498	
  1499	def _compression_codex_settings(cfg: Dict[str, Any]) -> tuple[str, bool, Optional[int]]:
  1500	    """``codex_app_server_auto`` / ``codex_responses_native`` / ``codex_responses_compact_threshold``."""
  1501	    app_server_auto = str(cfg.get("codex_app_server_auto", "native") or "native").lower()
  1502	    if app_server_auto not in {"native", "hermes", "off"}:
  1503	        _ra().logger.warning(
  1504	            "Invalid compression.codex_app_server_auto=%r; using 'native'. "
  1505	            "Valid values are: native, hermes, off.",
  1506	            app_server_auto,
  1507	        )
  1508	        app_server_auto = "native"
  1509	    # Native Responses server-side compaction (opt-in; gate in agent/native_compaction.py).
  1510	    # Truthy coercion so "false"/"off" strings stay disabled.
  1511	    responses_native = is_truthy_value(cfg.get("codex_responses_native", False))
  1512	    _raw = cfg.get("codex_responses_compact_threshold")
  1513	    compact_threshold = None
  1514	    if _raw is not None:
  1515	        compact_threshold = _positive_int(_raw, reject=(bool, float))
  1516	        if compact_threshold is None:
  1517	            _ra().logger.warning(
  1518	                "Invalid compression.codex_responses_compact_threshold=%r; "
  1519	                "using the automatic threshold derived from local compression.",
  1520	                _raw,
  1521	            )
  1522	    return app_server_auto, responses_native, compact_threshold
  1523	
  1524	
  1525	def _parse_compression_config(agent, _agent_cfg) -> CompressionSettings:
  1526	    """Parse the ``compression`` section. Defaults here MUST match DEFAULT_CONFIG."""
  1527	    cfg = _cfg_dict(_agent_cfg, "compression")
  1528	    threshold, autoraise_notice_enabled = _compression_threshold(agent, cfg)
  1529	    # Plain int()/float() coercions raise on garbage; evaluated up front, in config order.
  1530	    target_ratio = float(cfg.get("target_ratio", 0.20))
  1531	    protect_last = int(cfg.get("protect_last_n", 20))
  1532	    # max_attempts: retry rounds before "max compression attempts reached"; some sessions
  1533	    # need >3 (incompressible tool schemas). Default 3, floor 1, cap 10.
  1534	    max_attempts = _parse_config_int(cfg.get("max_attempts", 3), 3)
  1535	    if max_attempts < 1:
  1536	        max_attempts = 3
  1537	    # threshold_tokens: absolute cap (lower of ratio threshold and this); clamped to the window at
  1538	    # apply-time. Explicit null is the ratio-only opt-out and stays None.
  1539	    threshold_tokens = cfg.get("threshold_tokens", cfg_get(DEFAULT_CONFIG, "compression", "threshold_tokens"))
  1540	    if threshold_tokens is not None:
  1541	        threshold_tokens = _positive_int(threshold_tokens)
  1542	    # Non-system head messages to protect (system prompt is always protected); 0 is a
  1543	    # legitimate "system prompt + summary + tail".
  1544	    protect_first = max(0, int(cfg.get("protect_first_n", 3)))
  1545	    checkpoint_required = is_truthy_value(cfg.get("checkpoint_required"), default=False)
  1546	    _refuse_checkpoint_required_on_codex_app_server(
  1547	        checkpoint_required, getattr(agent, "api_mode", None)
  1548	    )
  1549	    app_server_auto, responses_native, compact_threshold = _compression_codex_settings(cfg)
  1550	    # Opt-in idle compaction: compact up front when a session resumes after this many
  1551	    # seconds idle (0 = disabled). Consumed by build_turn_context().
  1552	    idle_compact_after_seconds = max(0, int(cfg.get("idle_compact_after_seconds", 0)))
  1553	    return CompressionSettings(
  1554	        threshold=threshold,
  1555	        autoraise_notice_enabled=autoraise_notice_enabled,
  1556	        enabled=_cfg_flag(cfg, "enabled", True),
  1557	        target_ratio=target_ratio,
  1558	        protect_last=protect_last,
  1559	        # "lean" keeps a clamped 2.5%/10K-25K verbatim tail (continuity rides the summary);
  1560	        # "legacy" restores the 0.20*threshold tail. Unknown → lean inside the compressor.
  1561	        tail_mode=str(cfg.get("tail_mode", "lean")).strip().lower(),
  1562	        # Actionable user messages guaranteed to survive in the tail (default 1, floor 1).
  1563	        min_tail_users=max(1, _parse_config_int(cfg.get("min_tail_user_messages", 1), 1)),
  1564	        max_attempts=min(max_attempts, 10),
  1565	        # Opt-in proactive tool-result prune trigger (0 = disabled; negatives = disabled).
  1566	        proactive_prune_tokens=max(0, _parse_config_int(cfg.get("proactive_prune_tokens", 0), 0)),
  1567	        proactive_prune_min_chars=_parse_config_int(
  1568	            cfg.get("proactive_prune_min_result_chars", 8000), 8000
  1569	        ),
  1570	        proactive_prune_min_reclaim=max(
  1571	            0, _parse_config_int(cfg.get("proactive_prune_min_reclaim_tokens", 4096), 4096)
  1572	        ),
  1573	        protect_first=protect_first,
  1574	        abort_on_summary_failure=_cfg_flag(cfg, "abort_on_summary_failure", False),
  1575	        # Per-model threshold overrides: keys substring-matched against the model name
  1576	        # (longest match wins); {} = global threshold for all models.
  1577	        model_thresholds={
  1578	            str(k): float(v) for k, v in _cfg_dict(cfg, "model_thresholds").items()
  1579	            if isinstance(v, (int, float)) and not isinstance(v, bool)
  1580	        },
  1581	        threshold_tokens=threshold_tokens,
  1582	        checkpoint_required=checkpoint_required,
  1583	        # In-place compaction: no session-id rotation. default=True MUST match DEFAULT_CONFIG
  1584	        # (a False default flipped agents into rotation mode when the key was omitted).
  1585	        in_place=is_truthy_value(cfg.get("in_place"), default=True),
  1586	        # Opt-in: micro-compaction rewrites sent history per turn (breaks the cache prefix).
  1587	        micro_compact=is_truthy_value(cfg.get("micro_compact"), default=False),
  1588	        # Pass cadence in completed turns; each pass costs one prompt-cache break (>= 1).
  1589	        micro_compact_every_n_turns=max(
  1590	            1, _parse_config_int(cfg.get("micro_compact_every_n_turns", 1), 1)
  1591	        ),
  1592	        # Rolling-summary defrag threshold, in tokens.
  1593	        micro_compact_defrag_tokens=max(
  1594	            1, _parse_config_int(cfg.get("micro_compact_defrag_threshold_tokens", 2000), 2000)
  1595	        ),
  1596	        codex_app_server_auto=app_server_auto,
  1597	        codex_responses_native=responses_native,
  1598	        codex_responses_compact_threshold=compact_threshold,
  1599	        idle_compact_after_seconds=idle_compact_after_seconds,
  1600	    )
  1601	
  1602	
  1603	def _warn_invalid_config_int(
  1604	    what: str, value: Any, requirement: str, fallback: str, print_fallback: str = "",
  1605	    agent: Any = None,
  1606	) -> None:
  1607	    """Log + stderr-print an invalid integer config value (``print_fallback``: user-facing
  1608	    wording where it differs from the log line). The print is an automatic diagnostic and
  1609	    honors the warning-notification policy; the log line never does."""
  1610	    _ra().logger.warning(
  1611	        "Invalid %s: %r — %s. Falling back to %s.", what, value, requirement, fallback,
  1612	    )
  1613	    from gateway.warning_notifications import warning_notifications_enabled
  1614	    try:
  1615	        if not warning_notifications_enabled(
  1616	            getattr(agent, "_notification_platform", getattr(agent, "platform", "cli")),
  1617	            getattr(agent, "_notification_config", None),
  1618	        ):
  1619	            return
  1620	    except Exception:
  1621	        pass
  1622	    print(
  1623	        f"\n⚠ Invalid {what}: {value!r}\n"
  1624	        f"  {requirement[0].upper() + requirement[1:]}.\n"
  1625	        f"  Falling back to {print_fallback or fallback}.\n",
  1626	        file=sys.stderr,
  1627	    )
  1628	
  1629	
  1630	def _custom_provider_configured_base_url(
  1631	    _configured_provider: str, _agent_cfg, _custom_providers
  1632	) -> str:
  1633	    """Base URL of a named custom provider (``providers.<name>`` first, then
  1634	    ``custom_providers``), normalized for route comparison; "" if unknown.
  1635	    Disabled ``providers.*`` entries also mask their ``custom_providers`` twin.
  1636	    """
  1637	    _wanted = _normalize_custom_provider_name(_configured_provider)
  1638	    _user_providers = _agent_cfg.get("providers")
  1639	    _disabled_ids: set[str] = set()
  1640	    if isinstance(_user_providers, dict):
  1641	        from hermes_cli.config import is_provider_enabled
  1642	        for _key, _entry in _user_providers.items():
  1643	            if not isinstance(_entry, dict):
  1644	                continue
  1645	            _ids = _custom_provider_runtime_ids(_key) | _custom_provider_runtime_ids(_entry.get("name"))
  1646	            if not is_provider_enabled(_entry):
  1647	                _disabled_ids.update(_ids)
  1648	                continue
  1649	            if _wanted in _ids:
  1650	                _url = normalize_route_base_url(
  1651	                    _entry.get("api") or _entry.get("url") or _entry.get("base_url")
  1652	                )
  1653	                if _url:
  1654	                    return _url
  1655	    for _entry in _custom_providers:
  1656	        if not isinstance(_entry, dict):
  1657	            continue
  1658	        _key_ids = _custom_provider_runtime_ids(_entry.get("provider_key"))
  1659	        if _key_ids & _disabled_ids:
  1660	            continue
  1661	        if _wanted in _key_ids | _custom_provider_runtime_ids(_entry.get("name")):
  1662	            _url = normalize_route_base_url(_entry.get("base_url"))
  1663	            if _url:
  1664	                return _url
  1665	    return ""
  1666	
  1667	
  1668	# Provider ids whose runtime is resolved first-hand (never a named custom provider).
  1669	_RUNTIME_FIRST_PROVIDER_IDS = {
  1670	    "auto", "moa", "vertex", "google-vertex", "vertex-ai", "gcp-vertex", "vertexai",
  1671	}
  1672	
  1673	
  1674	def _configured_default_base_url(_agent_cfg, _model_cfg, _custom_providers) -> str:
  1675	    """Normalized route of the configured default model (``model.base_url``, else the named
  1676	    custom provider's URL when ``model.provider`` is not a first-class/auth provider)."""
  1677	    _configured_base_url = normalize_route_base_url(_model_cfg.get("base_url"))
  1678	    _configured_provider = str(_model_cfg.get("provider") or "").strip()
  1679	    _norm = _normalize_custom_provider_name(_configured_provider)
  1680	    _custom_provider_candidate = bool(_norm)
  1681	    if _norm in _RUNTIME_FIRST_PROVIDER_IDS:
  1682	        _custom_provider_candidate = False
  1683	    elif _custom_provider_candidate and _norm != "custom" and not _norm.startswith("custom:"):
  1684	        with suppress(Exception):
  1685	            from hermes_cli.auth import resolve_provider as resolve_auth_provider
  1686	            _custom_provider_candidate = (
  1687	                str(resolve_auth_provider(_norm) or "").strip().lower() != _norm
  1688	            )
  1689	    if not _configured_base_url and _custom_provider_candidate:
  1690	        _configured_base_url = _custom_provider_configured_base_url(
  1691	            _configured_provider, _agent_cfg, _custom_providers
  1692	        )
  1693	    return _configured_base_url
  1694	
  1695	
  1696	def _active_route_url(agent, base_url) -> str:
  1697	    """The runtime route, keeping the requested URL's query string when it is the same route."""
  1698	    _active = str(agent.base_url or "")
  1699	    _requested = str(base_url or "")
  1700	    if "?" in _requested.split("#", 1)[0]:
  1701	        with suppress(TypeError, ValueError):
  1702	            _without_query = urlunparse(urlparse(_requested)._replace(query=""))
  1703	            if normalize_route_base_url(_without_query) == normalize_route_base_url(_active):
  1704	                _active = _requested
  1705	    return normalize_route_base_url(_active)
  1706	
  1707	
  1708	def _scope_context_length_to_default_runtime(
  1709	    agent, _agent_cfg, _model_cfg, _custom_providers, _config_context_length, base_url
  1710	) -> Optional[int]:
  1711	    """Return ``model.context_length`` only if it describes the active runtime.
  1712	
  1713	    It describes the configured default model; a ``--model`` launch has already replaced
  1714	    ``agent.model``, so carrying the default's window into that runtime is stale. Live
  1715	    switch/fallback paths already clear it — direct-start stays consistent with them.
  1716	    """
  1717	    _default = _model_cfg.get("default")
  1718	    if isinstance(_default, dict):
  1719	        from hermes_cli.config import split_model_config_default
  1720	        _default, _ = split_model_config_default(_default)
  1721	    _configured_default_model = str(_default or "").strip()
  1722	    _configured_default_runtime_model = _configured_default_model
  1723	    _active_runtime_model = agent.model
  1724	    if _configured_default_model:
  1725	        with suppress(Exception):
  1726	            from hermes_cli.model_normalize import normalize_model_for_provider
  1727	            _configured_default_runtime_model = normalize_model_for_provider(
  1728	                _configured_default_model, agent.provider
  1729	            )
  1730	            _active_runtime_model = normalize_model_for_provider(agent.model, agent.provider)
  1731	    _configured_base_url = _configured_default_base_url(_agent_cfg, _model_cfg, _custom_providers)
  1732	    _active_base_url = _active_route_url(agent, base_url)
  1733	    _route_mismatch = _context_route_mismatch(
  1734	        _configured_base_url, _active_base_url, str(_model_cfg.get("provider") or "").strip(),
  1735	        agent.provider, already_normalized=True,
  1736	    )
  1737	    _model_mismatch = bool(
  1738	        _configured_default_runtime_model
  1739	        and _configured_default_runtime_model != _active_runtime_model
  1740	    )
  1741	    if _model_mismatch or _route_mismatch:
  1742	        _ra().logger.debug(
  1743	            "Ignoring model.context_length=%s for startup runtime %s at %s "
  1744	            "(configured default is %s at %s)",
  1745	            _config_context_length,
  1746	            agent.model,
  1747	            _active_base_url or agent.provider,
  1748	            _configured_default_model,
  1749	            _configured_base_url or _model_cfg.get("provider"),
  1750	        )
  1751	        return None
  1752	    return _config_context_length
  1753	
  1754	
  1755	def set_config_context_length(agent, value: Optional[int]) -> None:
  1756	    """Store the durable ``model.context_length`` pin on EVERY cached copy of it.
  1757	
  1758	    The pin is read from config exactly once, at construction, then cached twice: on
  1759	    ``agent._config_context_length`` (switch/fallback resolution plus every display and ``/usage``
  1760	    surface) and on ``context_compressor._config_context_length`` (the compressor's own
  1761	    re-resolution). Live paths that updated only one copy left the other stale, so a session could
  1762	    report a pinned ceiling while compressing against a different window (#116467).
  1763	    """
  1764	    agent._config_context_length = value
  1765	    _compressor = getattr(agent, "context_compressor", None)
  1766	    if _compressor is not None:
  1767	        _compressor._config_context_length = value
  1768	
  1769	
  1770	def config_context_length_for_runtime(agent, config=None) -> Optional[int]:
  1771	    """Re-read the durable ``model.context_length`` pin for ``agent``'s CURRENT runtime, or ``None``.
  1772	
  1773	    Single re-derivation point for the cached pin: construction resolves it once, and every live path
  1774	    that re-resolves a runtime used to clear the cached copy without re-reading the config — so a
  1775	    model/provider switch or a Desktop config round-trip silently dropped a ceiling the user still had
  1776	    on disk, and resolution fell through to probing / catalog metadata / the 256K fallback (#116467).
  1777	
  1778	    Reuses construction's own scoping (``_scope_context_length_to_default_runtime``): the pin describes
  1779	    the configured default route, so an unrelated runtime never inherits it.
  1780	    """
  1781	    try:
  1782	        from hermes_cli.config import get_compatible_custom_providers, load_config
  1783	        _agent_cfg = config if isinstance(config, dict) else load_config()
  1784	        if not isinstance(_agent_cfg, dict):
  1785	            return None
  1786	        _model_section = _agent_cfg.get("model", {})
  1787	        if not isinstance(_model_section, dict):
  1788	            return None
  1789	        _pin = _model_section.get("context_length")
  1790	        if _pin is None or isinstance(_pin, bool):
  1791	            return None
  1792	        _pin = int(_pin)
  1793	        if _pin <= 0:
  1794	            return None
  1795	        return _scope_context_length_to_default_runtime(
  1796	            agent, _agent_cfg, _model_section, get_compatible_custom_providers(_agent_cfg),
  1797	            _pin, str(getattr(agent, "base_url", "") or ""),
  1798	        )
  1799	    except Exception:
  1800	        logger.debug("Could not re-read model.context_length for the current runtime", exc_info=True)
  1801	        return None
  1802	
  1803	
  1804	_CTX_LEN_REQUIREMENT = "must be a positive integer (e.g. 256000, not '256K')"
  1805	
  1806	
  1807	def _warn_invalid_custom_provider_context_length(agent, _custom_providers) -> None:
  1808	    """Surface a context_length the helper silently skipped (not a positive int)."""
  1809	    _target = normalize_route_base_url(agent.base_url)
  1810	    if not _target:
  1811	        return
  1812	    for _cp_entry in _custom_providers:
  1813	        if not isinstance(_cp_entry, dict):
  1814	            continue
  1815	        if normalize_route_base_url(_cp_entry.get("base_url")) != _target:
  1816	            continue
  1817	        _cp_models = _cp_entry.get("models", {})
  1818	        _cp_model_cfg = _cp_models.get(agent.model, {}) if isinstance(_cp_models, dict) else None
  1819	        _cp_ctx = _cp_model_cfg.get("context_length") if isinstance(_cp_model_cfg, dict) else None
  1820	        if _cp_ctx is not None and _positive_int(_cp_ctx) is None:
  1821	            _warn_invalid_config_int(
  1822	                f"context_length for model {agent.model!r} in custom_providers",
  1823	                _cp_ctx, _CTX_LEN_REQUIREMENT, "auto-detection", "auto-detected context window",
  1824	                agent=agent,
  1825	            )
  1826	        return
  1827	
  1828	
  1829	def _resolve_context_length(agent, _agent_cfg, base_url):
  1830	    # Aux compression model context_length hint (custom endpoints often can't report it).
  1831	    try:
  1832	        _aux_cfg = cfg_get(_agent_cfg, "auxiliary", "compression", default={})
  1833	    except Exception:
  1834	        _aux_cfg = {}
  1835	    _aux_ctx = _aux_cfg.get("context_length") if isinstance(_aux_cfg, dict) else None
  1836	    try:
  1837	        agent._aux_compression_context_length_config = int(_aux_ctx) if _aux_ctx is not None else None
  1838	    except (TypeError, ValueError):
  1839	        agent._aux_compression_context_length_config = None
  1840	
  1841	    _model_cfg = _agent_cfg.get("model", {})
  1842	    _model_section = _model_cfg if isinstance(_model_cfg, dict) else {}
  1843	
  1844	    _config_context_length = _model_section.get("context_length")
  1845	    if _config_context_length is not None:
  1846	        try:
  1847	            _config_context_length = int(_config_context_length)
  1848	        except (TypeError, ValueError):
  1849	            _warn_invalid_config_int(
  1850	                "model.context_length in config.yaml", _config_context_length,
  1851	                "must be a plain integer (e.g. 256000, not '256K')",
  1852	                "auto-detection", "auto-detected context window", agent=agent,
  1853	            )
  1854	            _config_context_length = None
  1855	
  1856	    # Resolve custom_providers before route-scoping: a named provider may keep its URL here.
  1857	    try:
  1858	        from hermes_cli.config import get_compatible_custom_providers
  1859	        _custom_providers = get_compatible_custom_providers(_agent_cfg)
  1860	    except Exception:
  1861	        _custom_providers = _agent_cfg.get("custom_providers")
  1862	        if not isinstance(_custom_providers, list):
  1863	            _custom_providers = []
  1864	
  1865	    # ``model.context_length`` describes the configured default model; drop it when the
  1866	    # startup runtime (model or route) differs from that default.
  1867	    if _config_context_length is not None:
  1868	        _config_context_length = _scope_context_length_to_default_runtime(
  1869	            agent, _agent_cfg, _model_section, _custom_providers, _config_context_length, base_url
  1870	        )
  1871	
  1872	    # Reused by _check_compression_model_feasibility (aux compression model detection).
  1873	    agent._custom_providers = _custom_providers
  1874	    _merge_custom_provider_extra_body(agent, _custom_providers)
  1875	
  1876	    if _config_context_length is None and _custom_providers:
  1877	        with suppress(Exception):
  1878	            from hermes_cli.config import get_custom_provider_context_length
  1879	            _cp_ctx_resolved = get_custom_provider_context_length(
  1880	                model=agent.model, base_url=agent.base_url, custom_providers=_custom_providers
  1881	            )
  1882	            if _cp_ctx_resolved:
  1883	                _config_context_length = int(_cp_ctx_resolved)
  1884	        if _config_context_length is None:
  1885	            _warn_invalid_custom_provider_context_length(agent, _custom_providers)
  1886	
  1887	    # Persisted for switch_model / fallback AFTER the custom_providers branch (per-model overrides).
  1888	    agent._config_context_length = _config_context_length
  1889	    if _config_context_length is not None:
  1890	        from agent.context_pin import warn_once_on_pin_disagreement
  1891	        warn_once_on_pin_disagreement(agent.model, agent.base_url or "", _config_context_length)
  1892	
  1893	    _lmstudio_runtime_context_length = agent._ensure_lmstudio_runtime_loaded(_config_context_length)
  1894	    if agent._lmstudio_load_was_unverified(_lmstudio_runtime_context_length):
  1895	        _ra().logger.warning(
  1896	            "LM Studio model activation was rejected or completed without a "
  1897	            "verifiable active context length; falling back to configured context"
  1898	        )
  1899	    _effective_context_length = agent._effective_lmstudio_context_length(
  1900	        _config_context_length, _lmstudio_runtime_context_length,
  1901	    )
  1902	    return _config_context_length, _custom_providers, _effective_context_length, _model_cfg
  1903	
  1904	
  1905	def _select_context_engine(_agent_cfg):
  1906	    """Config-driven context engine: ``context.engine`` → plugins/context_engine/<name>/ →
  1907	    general plugin system → None (built-in ContextCompressor)."""
  1908	    _engine_name = "compressor"
  1909	    with suppress(Exception):
  1910	        _ctx_cfg = _agent_cfg.get("context", {}) if isinstance(_agent_cfg, dict) else {}
  1911	        _engine_name = _ctx_cfg.get("engine", "compressor") or "compressor"
  1912	    if _engine_name == "compressor":
  1913	        return None  # built-in; don't auto-activate plugins
  1914	    _selected_engine = None
  1915	    _copy_failed = False
  1916	    try:
  1917	        from plugins.context_engine import load_context_engine
  1918	        _selected_engine = load_context_engine(_engine_name)
  1919	    except Exception as _ce_load_err:
  1920	        _ra().logger.debug("Context engine load from plugins/context_engine/: %s", _ce_load_err)
  1921	
  1922	    if _selected_engine is None:
  1923	        try:
  1924	            from hermes_cli.plugins import get_plugin_context_engine
  1925	            _candidate = get_plugin_context_engine()
  1926	        except Exception:
  1927	            _candidate = None
  1928	        if _candidate is not None and _candidate.name == _engine_name:
  1929	            # The plugin system holds ONE shared instance; each agent gets its own so a child's
  1930	            # update_model() can't mutate the parent's (#42449). clone_for_agent() defaults to
  1931	            # deepcopy; engines with uncopyable state (locks, DB conns) override it. A failure
  1932	            # falls back to the built-in compressor with an ACCURATE message, not "not found".
  1933	            try:
  1934	                _selected_engine = _candidate.clone_for_agent()
  1935	            except Exception as _copy_err:
  1936	                _copy_failed = True
  1937	                _ra().logger.warning(
  1938	                    "Context engine '%s' could not be safely copied for this "
  1939	                    "agent (%s) — falling back to built-in compressor. Plugin "
  1940	                    "engines that hold uncopyable state (locks, DB connections) "
  1941	                    "should override clone_for_agent() (or __deepcopy__) to copy "
  1942	                    "only mutable budget state.",
  1943	                    _engine_name, _copy_err,
  1944	                )
  1945	
  1946	    if _selected_engine is None and not _copy_failed:
  1947	        _ra().logger.warning(
  1948	            "Context engine '%s' not found — falling back to built-in compressor", _engine_name
  1949	        )
  1950	    return _selected_engine
  1951	
  1952	
  1953	def _compressor_max_tokens(agent):
  1954	    """``agent.max_tokens``, or the native-Gemini adapter default when unset: generateContent
  1955	    still sends maxOutputTokens=65,535 and the threshold is pct×(window − max_tokens), so
  1956	    reserving 0 let the provider 400 before compaction fired."""
  1957	    if agent.max_tokens is not None:
  1958	        return agent.max_tokens
  1959	    with suppress(Exception):
  1960	        from agent.gemini_native_adapter import (
  1961	            GEMINI_DEFAULT_MAX_OUTPUT_TOKENS, is_native_gemini_base_url
  1962	        )
  1963	        _gemini_provider = str(agent.provider or "").strip().lower() in {
  1964	            "gemini", "google", "google-gemini", "google-ai-studio",
  1965	        }
  1966	        if _gemini_provider or is_native_gemini_base_url(agent.base_url):
  1967	            return GEMINI_DEFAULT_MAX_OUTPUT_TOKENS
  1968	    return None
  1969	
  1970	
  1971	def _build_context_engine(agent, _agent_cfg, cs, _custom_providers, _effective_context_length, session_db):
  1972	    _selected_engine = _select_context_engine(_agent_cfg)
  1973	    if _selected_engine is not None:
  1974	        agent.context_compressor = _selected_engine
  1975	        # External engines own compaction policy — the host threshold (and its Codex
  1976	        # autoraise) never reaches the plugin, so drop the notice.
  1977	        agent._compression_threshold_autoraised = None
  1978	        # External engines own compaction policy: the host compression threshold (including the Codex
  1979	        # gpt-5.5 autoraise above) only configures the built-in ContextCompressor and never reaches the
  1980	        # plugin, so the autoraise notice would announce a change that does not apply. (#44439)
  1981	        from agent.model_metadata import get_model_context_length
  1982	        _plugin_ctx_len = get_model_context_length(
  1983	            agent.model, base_url=agent.base_url, api_key=getattr(agent, "api_key", ""),
  1984	            config_context_length=_effective_context_length, provider=agent.provider,
  1985	            custom_providers=_custom_providers,
  1986	        )
  1987	        # Per-model overrides BEFORE the initial update_model() so the first threshold
  1988	        # resolution already sees them.
  1989	        if cs.model_thresholds:
  1990	            agent.context_compressor.model_thresholds = cs.model_thresholds
  1991	        agent.context_compressor.update_model(
  1992	            model=agent.model, context_length=_plugin_ctx_len, base_url=agent.base_url,
  1993	            api_key=getattr(agent, "api_key", ""), provider=agent.provider, api_mode=agent.api_mode,
  1994	        )
  1995	        if not agent.quiet_mode:
  1996	            _ra().logger.info("Using context engine: %s", _selected_engine.name)
  1997	    else:
  1998	        agent.context_compressor = ContextCompressor(
  1999	            model=agent.model, threshold_percent=cs.threshold, protect_first_n=cs.protect_first,
  2000	            protect_last_n=cs.protect_last, summary_target_ratio=cs.target_ratio,
  2001	            summary_model_override=None, quiet_mode=agent.quiet_mode, base_url=agent.base_url,
  2002	            api_key=getattr(agent, "api_key", ""), config_context_length=_effective_context_length,
  2003	            provider=agent.provider, api_mode=agent.api_mode,
  2004	            abort_on_summary_failure=cs.abort_on_summary_failure,
  2005	            max_tokens=_compressor_max_tokens(agent), model_thresholds=cs.model_thresholds,
  2006	            threshold_tokens_cap=cs.threshold_tokens,
  2007	            proactive_prune_tokens=cs.proactive_prune_tokens,
  2008	            proactive_prune_min_result_chars=cs.proactive_prune_min_chars,
  2009	            proactive_prune_min_reclaim_tokens=cs.proactive_prune_min_reclaim,
  2010	            min_tail_user_messages=cs.min_tail_users, tail_mode=cs.tail_mode,
  2011	            custom_providers=_custom_providers,
  2012	        )
  2013	    _bind_session_state = getattr(agent.context_compressor, "bind_session_state", None)
  2014	    if callable(_bind_session_state):
  2015	        with suppress(Exception):
  2016	            _bind_session_state(session_db=session_db, session_id=agent.session_id)
  2017	    agent.compression_enabled = cs.enabled
  2018	    agent.compression_in_place = cs.in_place
  2019	    _cc = agent.context_compressor
  2020	    # Micro-compaction has no pre-compress checkpoint hook; suppress it while the gate is
  2021	    # armed (mirrors native_compaction.py).
  2022	    if cs.checkpoint_required and cs.micro_compact:
  2023	        logger.warning(
  2024	            "compression.checkpoint_required is enabled: post-turn "
  2025	            "micro-compaction is disabled for this agent so every lossy "
  2026	            "rewrite passes through the checkpoint-gated compressor."
  2027	        )
  2028	        cs.micro_compact = False
  2029	    for _attr, _value in (
  2030	        ("_micro_compact_enabled", cs.micro_compact),
  2031	        ("_micro_compact_every_n_turns", cs.micro_compact_every_n_turns),
  2032	        ("_micro_compact_defrag_threshold_tokens", cs.micro_compact_defrag_tokens),
  2033	    ):
  2034	        if hasattr(_cc, _attr):
  2035	            setattr(_cc, _attr, _value)
  2036	    agent.compression_checkpoint_required = cs.checkpoint_required
  2037	    from agent.conversation_compression import _warn_checkpoint_required_without_capable_provider
  2038	    _warn_checkpoint_required_without_capable_provider(agent)
  2039	    agent.codex_app_server_auto_compaction = cs.codex_app_server_auto
  2040	    agent.codex_responses_native_compaction = cs.codex_responses_native
  2041	    agent.codex_responses_compact_threshold = cs.codex_responses_compact_threshold
  2042	    from agent.native_compaction import resolve_native_compaction_capabilities
  2043	    agent.runtime_capabilities = resolve_native_compaction_capabilities(
  2044	        model=agent.model, base_url=agent.base_url, provider=agent.provider,
  2045	        is_codex_backend=(agent.provider or "").strip().lower() == "openai-codex",
  2046	    )
  2047	    agent.max_compression_attempts = cs.max_attempts
  2048	    agent.compression_idle_compact_after_seconds = cs.idle_compact_after_seconds
  2049	
  2050	
  2051	def _enforce_minimum_context(agent):
  2052	    # Reject windows below the 64K floor needed for reliable tool-calling; an explicit
  2053	    # positive model.context_length on LM Studio is allowed below the floor.
  2054	    _ctx = getattr(agent.context_compressor, "context_length", 0)
  2055	    # A local Ollama server serves num_ctx, not the GGUF's advertised window: a Modelfile or
  2056	    # model.ollama_num_ctx at 64K+ is a usable window even when the metadata says 40K (#100437).
  2057	    # Only a local endpoint can honour num_ctx, so a stale override never admits a hosted model.
  2058	    if agent._ollama_num_ctx and agent.base_url and is_local_endpoint(agent.base_url):
  2059	        _ctx = max(_ctx or 0, agent._ollama_num_ctx)
  2060	    _allow_lmstudio_explicit_below_floor = (
  2061	        str(agent.provider or "").strip().lower() == "lmstudio"
  2062	        and isinstance(agent._config_context_length, int)
  2063	        and not isinstance(agent._config_context_length, bool)
  2064	        and agent._config_context_length > 0
  2065	    )
  2066	    if _ctx and _ctx < MINIMUM_CONTEXT_LENGTH and not _allow_lmstudio_explicit_below_floor:
  2067	        floor_k = MINIMUM_CONTEXT_LENGTH // 1000
  2068	        if agent.base_url and is_local_endpoint(agent.base_url):
  2069	            # Any OpenAI-compatible local server (llama.cpp, vLLM, Ollama, ...) — the window is the
  2070	            # server's runtime setting, not the model's; never assume Ollama here (#87075).
  2071	            remedy = (
  2072	                f"Your local server is serving a {_ctx:,}-token window.  Start it with at least "
  2073	                f"{floor_k}K context (llama.cpp: -c {MINIMUM_CONTEXT_LENGTH}; vLLM: --max-model-len; "
  2074	                f"Ollama: OLLAMA_CONTEXT_LENGTH={MINIMUM_CONTEXT_LENGTH} or a Modelfile num_ctx), "
  2075	                f"or set model.ollama_num_ctx in config.yaml to the window it really serves "
  2076	                f"(at least {floor_k}K)."
  2077	            )
  2078	        else:
  2079	            remedy = (
  2080	                f"Choose a model with at least {floor_k}K context.  If your server "
  2081	                f"reports a window smaller than the model's true window, set "
  2082	                f"model.context_length in config.yaml to the real value "
  2083	                f"(this must be at least {floor_k}K)."
  2084	            )
  2085	        raise ValueError(
  2086	            f"Model {agent.model} has a context window of {_ctx:,} tokens, "
  2087	            f"which is below the minimum {MINIMUM_CONTEXT_LENGTH:,} required "
  2088	            f"by Hermes Agent.  {remedy}"
  2089	        )
  2090	
  2091	
  2092	def _warn_nonagentic_hermes_model(agent):
  2093	    # Nous Hermes 3/4 are chat models, not tool-call-tuned. cli.py show_banner() already
  2094	    # warns on the CLI, so skip platform=="cli"; non-quiet non-CLI surfaces still get it.
  2095	    if agent.quiet_mode or (agent.platform or "cli") == "cli":
  2096	        return
  2097	    with suppress(Exception):
  2098	        from hermes_cli.model_switch import _check_hermes_model_warning
  2099	        _hermes_warn = _check_hermes_model_warning(agent.model or "")
  2100	        if _hermes_warn:
  2101	            _user_msg = (
  2102	                "⚠ Nous Research Hermes 3 & 4 models are NOT agentic — they "
  2103	                "lack reliable tool-calling for agent workflows (delegation, "
  2104	                "cron, proactive tools). Consider an agentic model instead "
  2105	                "(Claude, GPT, Gemini, Qwen-Coder, etc.)."
  2106	            )
  2107	            agent._emit_warning(_user_msg)
  2108	            _ra().logger.warning(_hermes_warn)
  2109	
  2110	
  2111	def _inject_context_engine_tools(agent):
  2112	    # Context engine tool schemas (lcm_*), deduped against existing names (plugins may
  2113	    # register the same schemas; duplicates 400 provider-side) and gated on enabled_toolsets
  2114	    # so `platform_toolsets: telegram: []` can't leak them.
  2115	    # Skip names that are already present — the model_tools.get_tool_definitions() quiet_mode cache returned a
  2116	    # shared list pre-#17335, so a stray mutation here would poison subsequent agent inits in the same
  2117	    # Gateway process and trip provider-side 'duplicate tool name' errors. Even with the cache fix, dedup is
  2118	    # the right defense against plugin paths that may register the same schemas via ctx.register_tool().
  2119	    # Mirrors the memory tools dedup above. Respect the platform's enabled_toolsets configuration (#5544):
  2120	    # context engine tools follow the same gating pattern as memory provider tools — without the gate,
  2121	    # `platform_toolsets: telegram: []` would still leak lcm_* tools into the tool surface and incur the
  2122	    # same local-model latency penalty.
  2123	    agent._context_engine_tool_names: set = set()
  2124	    if (
  2125	        agent.context_compressor
  2126	        and agent.tools is not None
  2127	        and (agent.enabled_toolsets is None or "context_engine" in agent.enabled_toolsets)
  2128	    ):
  2129	        _existing_tool_names = {
  2130	            t.get("function", {}).get("name") for t in agent.tools if isinstance(t, dict)
  2131	        }
  2132	        from agent.memory_manager import normalize_tool_schema
  2133	        for _raw_schema in agent.context_compressor.get_tool_schemas():
  2134	            _schema = normalize_tool_schema(_raw_schema)
  2135	            if _schema is None:
  2136	                # A nameless tool makes strict providers 400 and disables the whole toolset.
  2137	                _ra().logger.warning(
  2138	                    # Skip it. See #47707.
  2139	                    "Context engine returned a tool schema with no resolvable "
  2140	                    "name; skipping to avoid poisoning the request (%r)",
  2141	                    _raw_schema,
  2142	                )
  2143	                continue
  2144	            _tname = _schema["name"]
  2145	            if _tname in _existing_tool_names:
  2146	                continue  # already registered via plugin/cache path
  2147	            agent.tools.append({"type": "function", "function": _schema})
  2148	            for _names in (agent.valid_tool_names, agent._context_engine_tool_names, _existing_tool_names):
  2149	                _names.add(_tname)
  2150	
  2151	    if agent.context_compressor:
  2152	        try:
  2153	            agent.context_compressor.on_session_start(
  2154	                agent.session_id, hermes_home=str(get_hermes_home()),
  2155	                platform=agent.platform or "cli", model=agent.model,
  2156	                context_length=getattr(agent.context_compressor, "context_length", 0),
  2157	                conversation_id=getattr(agent, "_gateway_session_key", None),
  2158	            )
  2159	        except Exception as _ce_err:
  2160	            _ra().logger.debug("Context engine on_session_start: %s", _ce_err)
  2161	
  2162	
  2163	def _configure_ollama_num_ctx(agent, _model_cfg, _config_context_length):
  2164	    # Ollama defaults num_ctx to 2048, so detect the max window and send num_ctx per request.
  2165	    # model.ollama_num_ctx overrides; model.context_length caps the detected value (VRAM).
  2166	    agent._ollama_num_ctx: int | None = None
  2167	    _override = _model_cfg.get("ollama_num_ctx") if isinstance(_model_cfg, dict) else None
  2168	    if _override is not None:
  2169	        try:
  2170	            agent._ollama_num_ctx = int(_override)
  2171	        except (TypeError, ValueError):
  2172	            _ra().logger.debug("Invalid ollama_num_ctx config value: %r", _override)
  2173	    if agent._ollama_num_ctx is None and agent.base_url and is_local_endpoint(agent.base_url):
  2174	        try:
  2175	            # api_key may be a callable (Entra token provider); detection needs a string.
  2176	            _key = agent.api_key if isinstance(agent.api_key, str) else ""
  2177	            _detected = query_ollama_num_ctx(agent.model, agent.base_url, api_key=_key or "")
  2178	            if _detected and _detected > 0:
  2179	                agent._ollama_num_ctx = _detected
  2180	        except Exception as exc:
  2181	            _ra().logger.debug("Local server num_ctx detection failed: %s", exc)
  2182	    # Cap auto-detected num_ctx to the explicit context_length (GGUF metadata can advertise
  2183	    # 256K+ and Ollama would allocate that much VRAM); never override an explicit num_ctx.
  2184	    if (
  2185	        agent._ollama_num_ctx
  2186	        and _config_context_length
  2187	        and _override is None
  2188	        and agent._ollama_num_ctx > _config_context_length
  2189	    ):
  2190	        _ra().logger.info(
  2191	            "Ollama num_ctx capped: %d -> %d (model.context_length override)",
  2192	            agent._ollama_num_ctx, _config_context_length,
  2193	        )
  2194	        agent._ollama_num_ctx = _config_context_length
  2195	    if agent._ollama_num_ctx and not agent.quiet_mode:
  2196	        # Name the real source: a config override is honoured on any local server, /api/show is Ollama-only.
  2197	        _ra().logger.info(
  2198	            "Local server num_ctx: will request %d tokens (%s)",
  2199	            agent._ollama_num_ctx,
  2200	            "model.ollama_num_ctx" if _override is not None else "model max from Ollama /api/show",
  2201	        )
  2202	
  2203	
  2204	def _clamp_compressor_to_ollama_num_ctx(agent):
  2205	    # Recalibrate the compressor to the served window: every request runs at num_ctx, so a
  2206	    # trigger derived from the probed model window could sit above it and never fire.
  2207	    # A config that sets only model.ollama_num_ctx (without model.context_length) previously left the
  2208	    # compressor targeting the probed window while the server truncated/rejected at num_ctx — the compaction
  2209	    # trigger could sit several times ABOVE the real served window and never fire. Clamp the compressor's
  2210	    # window to the effective num_ctx so threshold math operates on the context the server actually serves.
  2211	    # (Overlaps #60103's silent-clamp dead zone; this is the init-order half.)
  2212	    _cc_window = getattr(agent.context_compressor, "context_length", 0) or 0
  2213	    if agent._ollama_num_ctx and agent._ollama_num_ctx > 0 and _cc_window and agent._ollama_num_ctx < _cc_window:
  2214	        _ra().logger.info(
  2215	            "Compressor window clamped to Ollama num_ctx: %d -> %d",
  2216	            _cc_window, agent._ollama_num_ctx,
  2217	        )
  2218	        agent.context_compressor.update_model(
  2219	            model=agent.model, context_length=agent._ollama_num_ctx, base_url=agent.base_url,
  2220	            api_key=getattr(agent, "api_key", ""), provider=agent.provider, api_mode=agent.api_mode,
  2221	        )
  2222	
  2223	
  2224	def _emit_compression_summary(agent, cs):
  2225	    # Codex autoraise notice: once per profile/config state (persisted marker; the gateway
  2226	    # rebuilds the agent per message). The display gate hides the banner, not the autoraise.
  2227	    _autoraise = agent._compression_threshold_autoraised or {}
  2228	    _autoraise_notice = None
  2229	    if (
  2230	        # A change in the raised threshold (or the autoraised model) updates the marker state and
  2231	        # re-notifies once. The config display gate (compression.codex_gpt55_autoraise_notice) still
  2232	        # suppresses the banner entirely without disabling the threshold autoraise. See #54432.
  2233	        bool(_autoraise)
  2234	        and cs.enabled
  2235	        and cs.autoraise_notice_enabled
  2236	        and not _codex_gpt55_autoraise_notice_seen(_autoraise)
  2237	    ):
  2238	        _autoraise_notice = _build_codex_gpt5_autoraise_notice(
  2239	            _autoraise, context_length=getattr(agent.context_compressor, "context_length", None)
  2240	        )
  2241	
  2242	    if not agent.quiet_mode:
  2243	        _cc = agent.context_compressor
  2244	        if cs.enabled:
  2245	            # The active engine's own threshold — a plugin's differs from cs.threshold.
  2246	            _pct = getattr(_cc, "threshold_percent", cs.threshold)
  2247	            _cap = getattr(_cc, "threshold_tokens_cap", None)
  2248	            # Name the cap only when it is what set the trigger; on small windows the ratio already sits below it.
  2249	            _eff_cap = getattr(_cc, "_effective_threshold_cap", lambda _ctx: None)(_cc.context_length)
  2250	            _cap_binds = _eff_cap is not None and _cc.threshold_tokens == _eff_cap
  2251	            _cap_note = f" (capped at {_cap:,} tokens)" if _cap_binds else ""
  2252	            print(f"📊 Context limit: {_cc.context_length:,} tokens (compress at {int(_pct*100)}% = {_cc.threshold_tokens:,}{_cap_note})")
  2253	        else:
  2254	            print(f"📊 Context limit: {_cc.context_length:,} tokens (auto-compression disabled)")
  2255	        # Gateway users get the same text via _compression_warning on turn 1.
  2256	        if _autoraise_notice:
  2257	            agent._safe_print(_autoraise_notice, diagnostic=True)
  2258	
  2259	    # status_callback isn't wired yet: stash for replay on the first turn; mark shown so
  2260	    # repeated inits stay silent.
  2261	    agent._compression_warning = _autoraise_notice
  2262	    if _autoraise_notice:
  2263	        _record_codex_gpt55_autoraise_notice(_autoraise)
  2264	    # Feasibility check deferred to the first turn near threshold (eager costs ~400ms cold).
  2265	    agent._compression_feasibility_checked = False
  2266	
  2267	
  2268	def _snapshot_primary_runtime(agent):
  2269	    # Per-turn restoration snapshot: after a fallback, the next turn restores these so the
  2270	    # preferred model gets a fresh attempt.
  2271	    _cc = agent.context_compressor
  2272	    agent._primary_runtime = {
  2273	        "model": agent.model,
  2274	        "provider": agent.provider,
  2275	        "requested_provider": agent.requested_provider,
  2276	        "base_url": agent.base_url,
  2277	        "api_mode": agent.api_mode,
  2278	        "api_key": getattr(agent, "api_key", ""),
  2279	        "request_overrides": dict(getattr(agent, "request_overrides", {}) or {}),
  2280	        "client_kwargs": dict(agent._client_kwargs),
  2281	        "use_prompt_caching": agent._use_prompt_caching,
  2282	        "use_native_cache_layout": agent._use_native_cache_layout,
  2283	        "reasoning_echo_flag": getattr(agent, "_reasoning_echo_flag", False),
  2284	        # Engine state _try_activate_fallback() overwrites (getattr: plugin engines may lack them).
  2285	        "compressor_model": getattr(_cc, "model", agent.model),
  2286	        "compressor_base_url": getattr(_cc, "base_url", agent.base_url),
  2287	        "compressor_api_key": getattr(_cc, "api_key", ""),
  2288	        "compressor_provider": getattr(_cc, "provider", agent.provider),
  2289	        "compressor_context_length": _cc.context_length,
  2290	        "compressor_threshold_tokens": _cc.threshold_tokens,
  2291	    }
  2292	    if agent.api_mode == "anthropic_messages":
  2293	        agent._primary_runtime.update({
  2294	            "anthropic_api_key": agent._anthropic_api_key,
  2295	            "anthropic_base_url": agent._anthropic_base_url,
  2296	            "is_anthropic_oauth": agent._is_anthropic_oauth,
  2297	        })
  2298	
  2299	
  2300	def _init_usage_state(agent):
  2301	    from agent.runtime_cwd import scope_terminal_cwd
  2302	    agent._subdirectory_hints = SubdirectoryHintTracker(
  2303	        working_dir=scope_terminal_cwd() or None, enabled=not agent.skip_context_files)
  2304	    _set_defaults(agent, _USAGE_STATE)
  2305	
  2306	
  2307	# Per-session usage accounting.
  2308	_USAGE_STATE: Dict[str, Any] = {
  2309	    "_user_turn_count": 0,
  2310	    "_is_user_initiated_turn": False,  # Copilot x-initiator: first call of a user turn = "user"
  2311	    # Usage anchors (agent/usage_anchor.py): last response's exact usage + transcript
  2312	    # snapshot; invalidated on compaction/session switch so stale anchors never suppress compression.
  2313	    "_usage_anchor": None,
  2314	    "_turn_base_usage_anchor": None,
  2315	    "_request_pressure_anchored": False,  # whether the last pressure figure came from the anchor
  2316	    # Cumulative token usage for the session
  2317	    "session_prompt_tokens": 0,
  2318	    "session_completion_tokens": 0,
  2319	    "session_total_tokens": 0,
  2320	    "session_api_calls": 0,
  2321	    "session_input_tokens": 0,
  2322	    "session_output_tokens": 0,
  2323	    "session_cache_read_tokens": 0,
  2324	    "session_cache_write_tokens": 0,
  2325	    "session_reasoning_tokens": 0,
  2326	    "session_estimated_cost_usd": 0.0,
  2327	    "session_cost_status": "unknown",
  2328	    "session_cost_source": "none",
  2329	    # Status-bar latency/velocity history (last 10 calls), shared by loop + codex_runtime.
  2330	    "_api_latency_history": lambda: deque(maxlen=10),
  2331	    "_api_output_history": lambda: deque(maxlen=10),
  2332	}
  2333	
  2334	# Constructor params stored verbatim under the same name.
  2335	_PASSTHROUGH_PARAMS = (
  2336	    "model", "max_iterations", "save_trajectories", "verbose_logging", "quiet_mode",
  2337	    "tool_progress_mode", "ephemeral_system_prompt", "platform", "skip_context_files",
  2338	    "load_soul_identity", "pass_session_id", "log_prefix_chars",
  2339	    # OpenRouter provider preferences
  2340	    "providers_allowed", "providers_ignored", "providers_order", "provider_sort",
  2341	    "provider_require_parameters", "provider_data_collection", "openrouter_min_coding_score",
  2342	    # Toolset filtering
  2343	    "enabled_toolsets", "disabled_toolsets",
  2344	    # Model response configuration (None = provider/model default)
  2345	    "max_tokens", "reasoning_config", "service_tier",
  2346	    "side_agent",
  2347	)
  2348	# Gateway identity params stored as ``agent._<name>``. gateway_session_key is the stable
  2349	# per-chat key (e.g. agent:main:telegram:dm:123).
  2350	_GATEWAY_IDENTITY_PARAMS = (
  2351	    "user_id", "user_id_alt", "user_name", "chat_id", "chat_name", "chat_type", "thread_id",
  2352	    "gateway_session_key",
  2353	)
  2354	_CALLBACK_PARAMS = (
  2355	    "tool_progress_callback", "tool_start_callback", "tool_complete_callback",
  2356	    "tool_result_metadata_callback",
  2357	    "thinking_callback", "reasoning_callback", "clarify_callback",
  2358	    "read_terminal_callback", "read_preview_callback", "drive_preview_callback",
  2359	    "read_window_below_callback", "connection_callback", "tour_callback",
  2360	    "step_callback", "stream_delta_callback", "interim_assistant_callback",
  2361	    "status_callback", "notice_callback", "notice_clear_callback",
  2362	    "event_callback", "reaction_callback", "tool_gen_callback",
  2363	)
  2364	
  2365	
  2366	def init_agent(
  2367	    agent, base_url: str = None, api_key: str = None, provider: str = None, api_mode: str = None,
  2368	    acp_command: str = None, acp_args: list[str] | None = None, command: str = None,
  2369	    args: list[str] | None = None, model: str = "", max_iterations: int = sys.maxsize,
  2370	    enabled_toolsets: List[str] = None, disabled_toolsets: List[str] = None,
  2371	    save_trajectories: bool = False, verbose_logging: bool = False, quiet_mode: bool = False,
  2372	    tool_progress_mode: str = "all", ephemeral_system_prompt: str = None,
  2373	    log_prefix_chars: int = 100, log_prefix: str = "", providers_allowed: List[str] = None,
  2374	    providers_ignored: List[str] = None, providers_order: List[str] = None,
  2375	    provider_sort: str = None, provider_require_parameters: bool = False,
  2376	    provider_data_collection: str = None, openrouter_min_coding_score: Optional[float] = None,
  2377	    session_id: str = None, tool_progress_callback: callable = None,
  2378	    tool_start_callback: callable = None, tool_complete_callback: callable = None,
  2379	    thinking_callback: callable = None, reasoning_callback: callable = None,
  2380	    clarify_callback: callable = None, read_terminal_callback: callable = None,
  2381	    read_preview_callback: callable = None, drive_preview_callback: callable = None,
  2382	    read_window_below_callback: callable = None, connection_callback: callable = None,
  2383	    tour_callback: callable = None, step_callback: callable = None,
  2384	    stream_delta_callback: callable = None, interim_assistant_callback: callable = None,
  2385	    tool_gen_callback: callable = None, status_callback: callable = None,
  2386	    notice_callback: callable = None, notice_clear_callback: callable = None,
  2387	    event_callback: Optional[Callable[[str, dict], None]] = None,
  2388	    reaction_callback: Optional[Callable[[str], None]] = None, max_tokens: int = None,
  2389	    reasoning_config: Dict[str, Any] = None, service_tier: str = None,
  2390	    request_overrides: Dict[str, Any] = None, prefill_messages: List[Dict[str, Any]] = None,
  2391	    platform: str = None, user_id: str = None, user_id_alt: str = None, user_name: str = None,
  2392	    chat_id: str = None, chat_name: str = None, chat_type: str = None, thread_id: str = None,
  2393	    gateway_session_key: str = None, skip_context_files: bool = False,
  2394	    load_soul_identity: bool = False, skip_memory: bool = False,
  2395	    skip_background_review: bool = False, session_db=None, parent_session_id: str = None,
  2396	    iteration_budget: "IterationBudget" = None, run_budget_seconds: Optional[float] = None,
  2397	    fallback_model: Dict[str, Any] = None, credential_pool=None, checkpoints_enabled: bool = False,
  2398	    checkpoint_max_snapshots: int = 20, checkpoint_max_total_size_mb: int = 500,
  2399	    checkpoint_max_file_size_mb: int = 10, pass_session_id: bool = False,
  2400	    requested_provider: str = None, capabilities: Optional[Dict[str, bool]] = None, cwd: Optional[str] = None,
  2401	    side_agent: bool = False, memory_manager=None,
  2402	    tool_result_metadata_callback: Optional[Callable[..., dict]] = None,
  2403	):
  2404	    _install_safe_stdio()
  2405	
  2406	    _params = locals()
  2407	    for _name in _PASSTHROUGH_PARAMS:
  2408	        setattr(agent, _name, _params[_name])
  2409	    for _name in _GATEWAY_IDENTITY_PARAMS:
  2410	        setattr(agent, f"_{_name}", _params[_name])
  2411	    agent.session_cwd = cwd or None
  2412	    # Shared iteration budget: parent creates, children inherit.
  2413	    agent.iteration_budget = iteration_budget or IterationBudget(max_iterations)
  2414	    # CLI replaces this with _cprint so raw ANSI status lines go through prompt_toolkit's
  2415	    # renderer (StdoutProxy would mangle them). None = builtins.print.
  2416	    agent._print_fn = None
  2417	    agent.background_review_callback = None  # Optional sync callback for gateway delivery
  2418	    agent.memory_notifications = "on"  # Memory update notifications: "off", "on", "verbose"
  2419	    # Skips the end-of-turn review fork (~30K tokens/event); one switch for both review paths.
  2420	    agent.skip_background_review = bool(skip_background_review)
  2421	    agent.log_prefix = f"{log_prefix} " if log_prefix else ""
  2422	    # Effective base URL for feature detection (prompt caching, reasoning, etc.)
  2423	    from hermes_cli.providers import is_actual_route
  2424	    if is_actual_route(provider, base_url):
  2425	        from hermes_cli.auth import normalize_actual_base_url
  2426	        base_url = normalize_actual_base_url(base_url)
  2427	    agent.base_url = base_url or ""
  2428	    provider_name = provider.strip().lower() if isinstance(provider, str) and provider.strip() else None
  2429	    agent.provider = provider_name or ""
  2430	    agent.requested_provider = (
  2431	        requested_provider.strip().lower()
  2432	        if isinstance(requested_provider, str) and requested_provider.strip()
  2433	        else agent.provider
  2434	    )
  2435	    agent.capabilities = {
  2436	        key: value for key, value in (capabilities or {}).items()
  2437	        if isinstance(key, str) and isinstance(value, bool)
  2438	    }
  2439	    agent._credential_pool = credential_pool
  2440	    agent.acp_command = acp_command or command
  2441	    agent.acp_args = list(acp_args or args or [])
  2442	    _resolve_api_mode(agent, api_mode, provider_name, base_url)
  2443	    _finalize_routing(agent, api_mode, credential_pool)
  2444	
  2445	    # Platform callbacks are stored under their parameter names verbatim.
  2446	    for _cb in _CALLBACK_PARAMS:
  2447	        setattr(agent, _cb, _params[_cb])
  2448	    agent.suppress_status_output = False
  2449	
  2450	    _set_defaults(agent, _CONTROL_STATE)
  2451	
  2452	    # reasoning_content echo opt-in; switch_model / fallback / restore keep it in sync.
  2453	    agent._reasoning_echo_flag = agent._read_reasoning_echo_from_config()
  2454	    agent.request_overrides = dict(request_overrides or {})
  2455	    agent.prefill_messages = prefill_messages or []  # Prefilled conversation turns
  2456	    agent._force_ascii_payload = False
  2457	    # Every (provider, model) that rejected image content this session. build_api_request strips
  2458	    # images from requests to those models only, so history keeps them for any model that can see.
  2459	    agent._image_rejecting_models = set()
  2460	    # Models whose Anthropic organization answered a fast request with a fast-mode limit of 0;
  2461	    # agent.fast_mode stops sending ``speed`` to them for the rest of the session.
  2462	    agent._fast_mode_unavailable_models = set()
  2463	
  2464	    _init_prompt_cache_config(agent)
  2465	    _init_turn_state(agent, run_budget_seconds)
  2466	    _setup_logging(agent)
  2467	    _set_defaults(agent, _STREAM_STATE)
  2468	    _build_client(agent, api_key, base_url, fallback_model)
  2469	    _init_fallback_chain(agent, fallback_model)
  2470	    _load_tools(agent, enabled_toolsets, disabled_toolsets)
  2471	    _init_session_state(
  2472	        agent, session_id, session_db, parent_session_id, reasoning_config, max_tokens,
  2473	        checkpoints_enabled, checkpoint_max_snapshots, checkpoint_max_total_size_mb, checkpoint_max_file_size_mb,
  2474	    )
  2475	
  2476	    # Load config once for memory, skills, and compression sections
  2477	    try:
  2478	        from hermes_cli.config import load_config_readonly as _load_agent_config
  2479	        _agent_cfg = _load_agent_config()
  2480	    except Exception:
  2481	        _agent_cfg = {}
  2482	
  2483	    _apply_display_config(agent, _agent_cfg, platform)
  2484	    _init_memory(agent, _agent_cfg, skip_memory, platform, memory_manager=memory_manager)
  2485	    _apply_agent_section(agent, _agent_cfg)
  2486	    cs = _parse_compression_config(agent, _agent_cfg)
  2487	    _config_context_length, _custom_providers, _effective_context_length, _model_cfg = _resolve_context_length(
  2488	        agent, _agent_cfg, base_url
  2489	    )
  2490	    _build_context_engine(agent, _agent_cfg, cs, _custom_providers, _effective_context_length, session_db)
  2491	    _configure_ollama_num_ctx(agent, _model_cfg, _config_context_length)
  2492	    _enforce_minimum_context(agent)
  2493	    _warn_nonagentic_hermes_model(agent)
  2494	    _inject_context_engine_tools(agent)
  2495	    _init_usage_state(agent)
  2496	    _clamp_compressor_to_ollama_num_ctx(agent)
  2497	    _emit_compression_summary(agent, cs)
  2498	    _snapshot_primary_runtime(agent)
  2499	
  2500	
  2501	__all__ = ["init_agent"]
  2502	
  2503	
  2504	# ---- BEGIN PLUGIN-COMPAT (revert-scheduled; see COMPAT_MANIFEST.md) ----
  2505	# Names external plugins imported from this module before the Sep 2026 decomposition.
  2506	# Internal code MUST NOT use these (scripts/check_compat_pointers.py fails CI if it does).
  2507	# The whole block is removed by reverting the commit that added it.
  2508	
  2509	
  2510	_PLUGIN_COMPAT_LAZY = {
  2511	    'ToolGuardrailDecision': ('agent.tool_guardrails', 'ToolGuardrailDecision'),
  2512	}
  2513	
  2514	
  2515	def __getattr__(name):  # PEP 562 — lazy so no import cycles
  2516	    target = _PLUGIN_COMPAT_LAZY.get(name)
  2517	    if target is None:
  2518	        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
  2519	    import importlib
  2520	    from hermes_cli.plugin_compat import warn_once
  2521	    warn_once(__name__, name, *target)
  2522	    return getattr(importlib.import_module(target[0]), target[1])
  2523	# ---- END PLUGIN-COMPAT ----
