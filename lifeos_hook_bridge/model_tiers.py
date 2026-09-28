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


def configured_tiers(read_setting: Callable[[str, Any], Any]) -> dict[str, dict[str, str]]:
    tiers = {}
    for tier, default_effort in DEFAULT_EFFORTS.items():
        model = read_setting(f"{tier}_model", "")
        effort = read_setting(f"{tier}_effort", default_effort)
        if not isinstance(model, str) or "\n" in model or "\r" in model:
            raise ValueError(f"{tier}_model must be one model name on one line")
        if not isinstance(effort, str) or effort not in VALID_EFFORTS:
            raise ValueError(f"{tier}_effort is not a supported Hermes effort")
        tiers[tier] = {"model": model.strip(), "effort": effort}
    return tiers


def configured_model_map(read_setting: Callable[[str, Any], Any]) -> dict[str, Any]:
    pin = read_setting("pinned_tier", "fable")
    if not isinstance(pin, str) or pin not in VALID_PINS:
        raise ValueError("pinned_tier is not a supported LifeOS tier")
    return {"pin": pin, **configured_tiers(read_setting)}


def _tier_name(requested_model: str) -> str:
    name = requested_model.lower()
    for tier in DEFAULT_EFFORTS:
        if name == tier or name.startswith(f"claude-{tier}-"):
            return tier
    return "sonnet"


def resolve_route(requested_model: str, default_model: str, mapping: Mapping[str, Any]) -> tuple[str, str]:
    tier = _tier_name(requested_model)
    raw = mapping.get(tier, {})
    if not isinstance(raw, Mapping):
        raise ValueError(f"{tier} route must be an object")
    model = raw.get("model", "")
    effort = raw.get("effort", DEFAULT_EFFORTS[tier])
    if not isinstance(model, str) or "\n" in model or "\r" in model:
        raise ValueError(f"{tier} model must be one model name on one line")
    if not isinstance(effort, str) or effort not in VALID_EFFORTS:
        raise ValueError(f"{tier} effort is not supported")
    selected_model = model.strip() or default_model
    if not selected_model:
        raise ValueError(f"{tier} has no configured model")
    return selected_model, effort


def main() -> int:
    requested_model = sys.argv[1] if len(sys.argv) > 1 else ""
    mapping = json.loads(os.environ.get("LIFEOS_MODEL_TIER_MAP", "{}"))
    if not isinstance(mapping, dict):
        raise ValueError("LIFEOS_MODEL_TIER_MAP must be an object")
    model, effort = resolve_route(requested_model, os.environ.get("ANTHROPIC_MODEL", ""), mapping)
    print(model)
    print(effort)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, json.JSONDecodeError) as error:
        print(f"LifeOS model tier settings: {error}", file=sys.stderr)
        raise SystemExit(1)
