# ABOUTME: Resolves LifeOS tier aliases to configurable local model and effort pairs.
# ABOUTME: Supplies defaults for one local model and validates dashboard settings.

from __future__ import annotations

import json
import os
import sys
from collections.abc import Callable, Mapping
from typing import Any


DEFAULT_EFFORTS = {"haiku": "low", "sonnet": "medium", "opus": "xhigh", "fable": "xhigh"}
VALID_EFFORTS = frozenset({"minimal", "low", "medium", "high", "xhigh", "max", "ultra"})
VALID_PINS = frozenset({"none", *DEFAULT_EFFORTS})


def carrier_observation(model: str, effort: str, provider: str, mapping: Mapping[str, Any]) -> dict[str, Any]:
    """Describe the observed main route without changing its real model name."""
    rungs = ("fable", "opus", "sonnet", "haiku")
    name = model.lower()
    tier = next((rung for rung in rungs if name == rung or name.startswith(f"claude-{rung}-")), None)
    if tier is None and model and effort in VALID_EFFORTS:
        for require_model in (True, False):
            tier = next((rung for rung in rungs
                         if isinstance(mapping.get(rung), Mapping)
                         and mapping[rung].get("effort") == effort
                         and mapping[rung].get("model", "") == (model if require_model else "")
                         and (not mapping[rung].get("provider") or mapping[rung]["provider"] == provider)), None)
            if tier is not None:
                break
    pin = mapping.get("pin")
    return {"model": model or None, "provider": provider, "effort": effort,
            "tier": tier, "pin": pin if pin in rungs else None}


def configured_tiers(
    read_setting: Callable[[str, Any], Any], default_provider: str = "", default_model: str = "",
) -> dict[str, dict[str, str]]:
    tiers = {}
    for tier, default_effort in DEFAULT_EFFORTS.items():
        provider = read_setting(f"{tier}_provider", "")
        model = read_setting(f"{tier}_model", "")
        effort = read_setting(f"{tier}_effort", default_effort)
        inherit_child = read_setting(f"{tier}_inherit_child_default", False)
        if not isinstance(provider, str) or "\n" in provider or "\r" in provider:
            raise ValueError(f"{tier}_provider must be one provider name on one line")
        if not isinstance(model, str) or "\n" in model or "\r" in model:
            raise ValueError(f"{tier}_model must be one model name on one line")
        if not isinstance(effort, str) or effort not in VALID_EFFORTS:
            raise ValueError(f"{tier}_effort is not a supported Hermes effort")
        if not isinstance(inherit_child, bool):
            raise ValueError(f"{tier}_inherit_child_default must be true or false")
        if inherit_child:
            provider, model = "", ""
        elif provider.strip() and not model.strip():
            raise ValueError(f"{tier}_provider requires a configured model")
        elif not model.strip() and default_model:
            provider, model = default_provider, default_model
        tiers[tier] = {"provider": provider.strip(), "model": model.strip(), "effort": effort}
    return tiers


def configured_model_map(
    read_setting: Callable[[str, Any], Any], default_provider: str = "", default_model: str = "",
) -> dict[str, Any]:
    pin = read_setting("pinned_tier", "fable")
    if not isinstance(pin, str) or pin not in VALID_PINS:
        raise ValueError("pinned_tier is not a supported LifeOS tier")
    return {"pin": pin, **configured_tiers(read_setting, default_provider, default_model)}


def _tier_name(requested_model: str) -> str:
    name = requested_model.lower()
    for tier in DEFAULT_EFFORTS:
        if name == tier or name.startswith(f"claude-{tier}-"):
            return tier
    return "sonnet"


def route_delegate_args(args: Mapping[str, Any], mapping: Mapping[str, Any]) -> dict[str, Any]:
    """Replace LifeOS child aliases with the configured Hermes model and effort."""
    routed = dict(args)
    if routed.get("action"):
        return routed
    tasks = routed.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        if not isinstance(routed.get("goal"), str):
            return routed
        tasks = [{key: routed[key] for key in ("goal", "context", "model", "reasoning_effort") if key in routed}]
    mapped_tasks = []
    changed = False
    for task in tasks:
        if not isinstance(task, dict):
            mapped_tasks.append(task)
            continue
        requested = task.get("model")
        tier = _tier_name(requested) if isinstance(requested, str) else None
        if tier is None or not (requested.lower() == tier or requested.lower().startswith(f"claude-{tier}-")):
            mapped_tasks.append(task)
            continue
        route = mapping.get(tier)
        if not isinstance(route, Mapping):
            raise ValueError(f"{tier} route is not configured")
        model = route.get("model", "")
        provider = route.get("provider", "")
        effort = route.get("effort", DEFAULT_EFFORTS[tier])
        if not isinstance(model, str) or "\n" in model or "\r" in model:
            raise ValueError(f"{tier} model must be one model name on one line")
        if not isinstance(provider, str) or "\n" in provider or "\r" in provider:
            raise ValueError(f"{tier} provider must be one provider name on one line")
        if effort not in VALID_EFFORTS:
            raise ValueError(f"{tier} effort is not supported")
        child = dict(task)
        child["_lifeos_requested_model"] = requested
        if model.strip():
            child["model"] = model.strip()
        else:
            child.pop("model", None)
        if provider.strip():
            if not model.strip():
                raise ValueError(f"{tier} provider requires a configured model")
            child["provider"] = provider.strip()
        else:
            child.pop("provider", None)
        child["reasoning_effort"] = effort
        mapped_tasks.append(child)
        changed = True
    if changed:
        routed["tasks"] = mapped_tasks
        for key in ("goal", "context", "model", "reasoning_effort"):
            routed.pop(key, None)
    return routed


def resolve_route(requested_model: str, default_model: str, mapping: Mapping[str, Any]) -> tuple[str, str, str]:
    tier = _tier_name(requested_model)
    raw = mapping.get(tier, {})
    if not isinstance(raw, Mapping):
        raise ValueError(f"{tier} route must be an object")
    model = raw.get("model", "")
    provider = raw.get("provider", "")
    effort = raw.get("effort", DEFAULT_EFFORTS[tier])
    if not isinstance(provider, str) or "\n" in provider or "\r" in provider:
        raise ValueError(f"{tier} provider must be one provider name on one line")
    if not isinstance(model, str) or "\n" in model or "\r" in model:
        raise ValueError(f"{tier} model must be one model name on one line")
    if not isinstance(effort, str) or effort not in VALID_EFFORTS:
        raise ValueError(f"{tier} effort is not supported")
    selected_model = model.strip() or default_model
    if not selected_model:
        raise ValueError(f"{tier} has no configured model")
    if provider.strip() and not model.strip():
        raise ValueError(f"{tier} provider requires a configured model")
    return provider.strip(), selected_model, effort


def main() -> int:
    requested_model = sys.argv[1] if len(sys.argv) > 1 else ""
    mapping = json.loads(os.environ.get("LIFEOS_MODEL_TIER_MAP", "{}"))
    if not isinstance(mapping, dict):
        raise ValueError("LIFEOS_MODEL_TIER_MAP must be an object")
    provider, model, effort = resolve_route(requested_model, os.environ.get("ANTHROPIC_MODEL", ""), mapping)
    print(model)
    print(effort)
    print(provider)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, json.JSONDecodeError) as error:
        print(f"LifeOS model tier settings: {error}", file=sys.stderr)
        raise SystemExit(1)
