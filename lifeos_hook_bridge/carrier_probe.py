# ABOUTME: Verifies that Hermes delegates the configured LifeOS Fable route.
# ABOUTME: Stores expiring child execution evidence for LifeOS IntegrityCheck.

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

try:
    from .model_tiers import configured_model_map, resolve_route
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from model_tiers import configured_model_map, resolve_route


MAX_AGE = dt.timedelta(days=30)
STATE_NAME = "hermes-carrier-probe.json"


def route_fingerprint(provider: str, model: str, effort: str, base_url: str, api_mode: str) -> str:
    payload = json.dumps([provider, model, effort, base_url.rstrip("/"), api_mode], separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def check_state(state: dict[str, Any] | None, fingerprint: str, *, now: dt.datetime | None = None) -> tuple[bool, str]:
    if not isinstance(state, dict):
        return False, "NEVER RUN"
    if state.get("route_fingerprint") != fingerprint:
        return False, "ROUTE CHANGED"
    if state.get("verdict") != "HOLDS":
        return False, "INCONCLUSIVE"
    observed = state.get("observed")
    if not isinstance(observed, dict) or not isinstance(observed.get("api_calls"), int) or observed["api_calls"] < 1:
        return False, "INCONCLUSIVE"
    try:
        timestamp = dt.datetime.fromisoformat(state["ts"])
        if timestamp.tzinfo is None:
            raise ValueError("naive timestamp")
    except (KeyError, TypeError, ValueError):
        return False, "INCONCLUSIVE"
    current = now or dt.datetime.now(dt.timezone.utc)
    age = current - timestamp
    if age < dt.timedelta(0) or age > MAX_AGE:
        return False, "STALE"
    return True, "HOLDS"


def check_main_rung(main: tuple[str, str, str], top: tuple[str, str, str]) -> tuple[bool, str]:
    for actual, expected, name in zip(main, top, ("PROVIDER", "MODEL", "EFFORT")):
        if actual != expected:
            return False, f"MAIN {name} MISMATCH"
    return True, "HOLDS"


def _state_path() -> Path:
    return Path.home() / ".claude/LIFEOS/MEMORY/STATE" / STATE_NAME


def _mapping(config: dict[str, Any]) -> dict[str, Any]:
    raw = os.environ.get("LIFEOS_MODEL_TIER_MAP")
    if raw is not None:
        mapping = json.loads(raw)
        if not isinstance(mapping, dict):
            raise ValueError("LIFEOS_MODEL_TIER_MAP must be an object")
        return mapping
    plugins = config.get("plugins")
    entries = plugins.get("entries") if isinstance(plugins, dict) else None
    entry = entries.get("lifeos-hook-bridge") if isinstance(entries, dict) else None
    if not isinstance(entry, dict):
        entry = {}
    settings = entry.get("settings") or entry.get("config") or {}
    if not isinstance(settings, dict):
        raise ValueError("LifeOS plugin settings must be an object")
    return configured_model_map(lambda key, default: settings.get(key, default))


def _route(tier: str = "fable") -> tuple[str, str, str, dict[str, Any]]:
    from hermes_cli.config import load_config_readonly
    from hermes_cli.runtime_provider import resolve_runtime_provider

    config = load_config_readonly()
    model_config = config.get("model") or {}
    if not isinstance(model_config, dict):
        raise ValueError("Hermes model config must be a mapping")
    default_model = str(model_config.get("default") or model_config.get("name") or "")
    mapping = _mapping(config)
    provider, model, effort = resolve_route(tier, default_model, mapping)
    requested = provider or str(model_config.get("provider") or "").strip() or None
    runtime = resolve_runtime_provider(requested=requested, target_model=model)
    provider = provider or str(runtime.get("provider") or "").strip()
    if not provider or not runtime.get("base_url") or not runtime.get("api_key"):
        raise ValueError(f"{tier} route has no complete Hermes provider credentials")
    return provider, model, effort, runtime


def _check_main_rung(tier: str) -> tuple[bool, str]:
    from hermes_cli.config import load_config_readonly
    from hermes_cli.runtime_provider import resolve_runtime_provider
    from hermes_constants import resolve_reasoning_config

    config = load_config_readonly()
    model_config = config.get("model") or {}
    if not isinstance(model_config, dict):
        raise ValueError("Hermes model config must be a mapping")
    main_model = str(model_config.get("default") or model_config.get("name") or "")
    if not main_model:
        raise ValueError("Hermes main model is not configured")
    main_provider = str(model_config.get("provider") or "").strip()
    if not main_provider:
        main_provider = str(resolve_runtime_provider(requested=None, target_model=main_model).get("provider") or "")
    reasoning = resolve_reasoning_config(config, main_model)
    main_effort = str(reasoning.get("effort") or "") if isinstance(reasoning, dict) else ""
    top_provider, top_model, top_effort, _ = _route(tier)
    return check_main_rung((main_provider, main_model, main_effort), (top_provider, top_model, top_effort))


def _write_state(state: dict[str, Any]) -> None:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    handle = tempfile.NamedTemporaryFile("w", dir=path.parent, prefix=f".{path.name}.", delete=False)
    try:
        os.fchmod(handle.fileno(), 0o600)
        json.dump(state, handle, indent=2)
        handle.write("\n")
        handle.close()
        os.replace(handle.name, path)
    finally:
        if not handle.closed:
            handle.close()
        Path(handle.name).unlink(missing_ok=True)


def _run_child(provider: str, model: str, effort: str, runtime: dict[str, Any]) -> dict[str, Any]:
    from run_agent import AIAgent
    from tools.delegate_tool import _build_children

    parent = AIAgent(
        session_id="lifeos-hermes-carrier-parent", api_key=runtime["api_key"],
        base_url=runtime["base_url"], provider=provider,
        api_mode=runtime.get("api_mode") or "chat_completions", model=model,
        platform="cli", quiet_mode=True, skip_context_files=True, skip_memory=True,
        save_trajectories=False, enabled_toolsets=["file"],
    )
    credentials = {
        "model": model, "provider": provider, "base_url": runtime["base_url"],
        "api_key": runtime["api_key"], "api_mode": runtime.get("api_mode"),
        "request_overrides": runtime.get("request_overrides"),
        "command": runtime.get("command"), "args": runtime.get("args"),
    }
    try:
        children, error = _build_children(
            [{"goal": "Reply OK only.", "provider": provider, "model": model,
              "reasoning_effort": effort}], [None], credentials,
            top_role="leaf", max_iterations=1, parent_agent=parent, routing_cfg={},
            live_deleg_id=None, live_writers=[],
        )
        if error:
            raise RuntimeError(error)
        child = children[0][2]
        try:
            result = child.run_conversation(user_message="Reply OK only.", task_id="lifeos-hermes-carrier-child")
            reasoning = getattr(child, "reasoning_config", {}) or {}
            observed = {
                "provider": str(result.get("provider") or ""),
                "model": str(result.get("model") or ""),
                "effort": reasoning.get("effort") if isinstance(reasoning, dict) else None,
                "api_calls": result.get("api_calls"),
                "served_model": result.get("served_model"),
            }
            if not (result.get("completed") and not result.get("failed")
                    and observed["provider"] == provider and observed["model"] == model
                    and observed["effort"] == effort and isinstance(observed["api_calls"], int)
                    and observed["api_calls"] >= 1 and result.get("final_response")):
                raise RuntimeError("Hermes child did not complete on the configured Fable route")
            return observed
        finally:
            child.close()
    finally:
        parent.close()


def main(argv: list[str] | None = None) -> int:
    arguments = argv if argv is not None else sys.argv[1:]
    if arguments not in (["--check"], ["--run"]) and not (
        len(arguments) == 2 and arguments[0] == "--check-main-rung" and arguments[1] in {"haiku", "sonnet", "opus", "fable"}
    ):
        print("Usage: hermes --run-file carrier_probe.py --check|--run|--check-main-rung TIER", file=sys.stderr)
        return 2
    try:
        if arguments[0] == "--check-main-rung":
            valid, reason = _check_main_rung(arguments[1])
            print(f"HermesCarrierProbe: {reason}", file=sys.stdout if valid else sys.stderr)
            return 0 if valid else 1
        provider, model, effort, runtime = _route()
        fingerprint = route_fingerprint(
            provider, model, effort, str(runtime["base_url"]), str(runtime.get("api_mode") or ""),
        )
        if arguments == ["--check"]:
            try:
                state = json.loads(_state_path().read_text())
            except (OSError, ValueError):
                state = None
            valid, reason = check_state(state, fingerprint)
            print(f"HermesCarrierProbe: {reason}", file=sys.stdout if valid else sys.stderr)
            return 0 if valid else 1
        _write_state({
            "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
            "verdict": "INCONCLUSIVE", "route_fingerprint": fingerprint,
        })
        observed = _run_child(provider, model, effort, runtime)
        _write_state({
            "ts": dt.datetime.now(dt.timezone.utc).isoformat(), "verdict": "HOLDS",
            "route_fingerprint": fingerprint, "observed": observed,
        })
        print(f"HermesCarrierProbe: HOLDS ({provider} / {model}, {effort})")
        return 0
    except (ValueError, RuntimeError, OSError) as error:
        print(f"HermesCarrierProbe: INCONCLUSIVE: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
