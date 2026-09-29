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
    settings = Path(os.environ.get("LIFEOS_HOOK_SETTINGS", str(Path.home() / ".claude/settings.json"))).expanduser()
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

    bridge = HookBridge(
        settings, settings.parent,
        model_tiers_provider=model_tiers,
    )
    try:
        from hermes_cli.plugins import VALID_HOOKS
    except ImportError:
        VALID_HOOKS = PATCHED_HOOKS
    patched_host = PATCHED_HOOKS <= VALID_HOOKS
    ctx.on_unload(bridge.close)
    ctx.register_hook("pre_tool_call", bridge.pre_tool_call)
    ctx.register_hook("post_tool_call", bridge.task_result)
    ctx.register_hook("pre_prompt_admission" if patched_host else "pre_llm_call", bridge.pre_llm_call)
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
