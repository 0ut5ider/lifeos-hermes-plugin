# ABOUTME: Registers LifeOS hook callbacks with the Hermes plugin manager.
# ABOUTME: Loads the installed Claude hook settings from the LifeOS account.

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .bridge import HookBridge
from .model_tiers import configured_model_map


PATCHED_HOOKS = {"pre_prompt_admission", "pre_command_approval", "augment_tool_result", "pre_turn_stop", "on_turn_result"}


def register(ctx: Any) -> None:
    from .cli import register_commands

    register_commands(ctx)
    memory_runtime = None
    if hasattr(ctx, "register_memory_provider"):
        from .memory_provider import register_provider
        memory_runtime = register_provider(ctx)
    try:
        from hermes_constants import get_hermes_home
    except ImportError:
        profile = None
    else:
        profile = get_hermes_home()
    try:
        from hermes_cli.plugins import VALID_HOOKS
    except ImportError:
        VALID_HOOKS = PATCHED_HOOKS
    if profile is not None and 'pre_message_delivery' in VALID_HOOKS:
        from .discord_delivery import PrivateDiscordDelivery
        delivery = PrivateDiscordDelivery(profile / 'lifeos-memory.json')
        ctx.register_hook('pre_message_delivery', delivery.check)
    from .lifeos_installation import selection
    home = selection(profile).home if profile is not None else Path.home()
    settings = Path(os.environ.get("LIFEOS_HOOK_SETTINGS", str(home / ".claude/settings.json"))).expanduser()
    if not settings.is_file():
        return
    def model_tiers() -> dict[str, Any]:
        try:
            from hermes_cli.inventory import load_picker_context
        except ModuleNotFoundError as error:
            if error.name not in {"hermes_cli", "hermes_cli.inventory"}:
                raise
            return configured_model_map(ctx.get_config)
        current = load_picker_context()
        return configured_model_map(ctx.get_config, current.current_provider, current.current_model)

    patched_host = PATCHED_HOOKS <= VALID_HOOKS
    bridge = HookBridge(
        settings, settings.parent,
        model_tiers_provider=model_tiers,
        profile=profile, hold_turns=patched_host, lifeos_home=home,
    )
    if {"subagent_start", "subagent_stop"} <= VALID_HOOKS:
        bridge.child_lifecycle_enabled = True
        ctx.register_hook("subagent_start", bridge.child_start)
        ctx.register_hook("subagent_stop", bridge.child_stop)
    if hasattr(ctx, "on_unload"):
        ctx.on_unload(bridge.close)
    if "post_api_request" in VALID_HOOKS:
        ctx.register_hook("post_api_request", bridge.observe_api_response)
    ctx.register_hook("pre_tool_call", bridge.pre_tool_call)
    ctx.register_hook("post_tool_call", bridge.task_result)
    def prompt_admission(**kwargs):
        if memory_runtime is not None:
            from .memory_provider import current_metadata
            memory_runtime.admit(current_metadata(), **kwargs)
        return bridge.pre_llm_call(**kwargs)
    ctx.register_hook("pre_prompt_admission" if patched_host else "pre_llm_call", prompt_admission)
    if not patched_host:
        ctx.register_hook("post_tool_call", bridge.post_tool_call)
        ctx.register_hook("on_session_finalize", bridge.session_end)
        ctx.register_hook("api_request_error", bridge.api_request_error)
        return
    ctx.register_hook("pre_command_approval", bridge.command_approval)
    ctx.register_hook("augment_tool_result", bridge.augment_tool_result)
    def stop(final_response="", session_id="", attempt=0, **kwargs):
        result = bridge.stop(final_response, session_id, stop_hook_active=attempt > 0, **kwargs)
        if result and ctx.get_config("stop_cap_policy", "claude") == "fail_closed":
            return {**result, "on_limit": "fail"}
        return result

    ctx.register_hook("pre_turn_stop", stop)
    ctx.register_hook("on_session_finalize", bridge.session_end)
    ctx.register_hook("api_request_error", bridge.api_request_error)
    ctx.register_hook("on_turn_result", bridge.turn_end)
